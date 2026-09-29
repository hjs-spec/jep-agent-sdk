"""@record decorator and trace manager for JEP Core 0.7."""

from __future__ import annotations

import functools
import inspect
from typing import Callable, Optional

from jep_agent.core.chain import AuditChain
from jep_agent.core.event import event_identity_ref
from jep_agent.primitives import judge, verify


class TraceManager:
    def __init__(self):
        self.chain: Optional[AuditChain] = None
        self.enabled = False

    def enable(
        self, issuer: str = "agent:default", private_key=None, storage_path: Optional[str] = None
    ):
        self.chain = AuditChain(issuer=issuer, private_key=private_key, storage_path=storage_path)
        self.enabled = True

    def disable(self):
        self.enabled = False

    def view(self):
        if not self.chain or not self.chain.events:
            print("No events recorded.")
            return
        for ev in self.chain.events:
            summary = (
                f"[{ev.get('verb', '?')}] {ev.get('who', '?')} @ "
                f"{ev.get('when', '?')} | what={str(ev.get('what', '?'))[:40]}..."
            )
            print(summary)

    def export(self) -> list:
        return self.chain.export() if self.chain else []

    def save(self, path: Optional[str] = None):
        if self.chain:
            self.chain.save(path)


trace = TraceManager()



class RecordingError(RuntimeError):
    """A JEP recording operation failed around a wrapped callable."""

    def __init__(
        self,
        message: str,
        *,
        stage: str,
        call_executed: bool,
        event_identity=None,
        recording_error_type: Optional[str] = None,
    ):
        super().__init__(message)
        self.stage = stage
        self.call_executed = call_executed
        self.event_identity = event_identity
        self.recording_error_type = recording_error_type


def _recording_error(
    exc: Exception,
    *,
    stage: str,
    call_executed: bool,
    start_event=None,
) -> RecordingError:
    identity = None
    if start_event is not None:
        try:
            identity = event_identity_ref(start_event)["value"]
        except (KeyError, TypeError):
            identity = None

    if stage == "before_execution":
        message = "JEP invocation recording failed before the wrapped callable executed"
    elif stage == "after_execution":
        message = (
            "The wrapped callable completed, but JEP completion recording failed; "
            "do not retry the business action solely because of this recording error"
        )
    else:
        message = (
            "The wrapped callable raised or was cancelled, and JEP error recording also failed"
        )

    return RecordingError(
        message,
        stage=stage,
        call_executed=call_executed,
        event_identity=identity,
        recording_error_type=type(exc).__name__,
    )


def record(
    func: Callable = None,
    *,
    issuer: str = "agent:default",
    private_key=None,
    chain: Optional[AuditChain] = None,
    auto_verify: bool = True,
    capture_values: bool = False,
):
    """Record invocation and completion for a synchronous or async callable.

    Arguments and return values are omitted by default. Set capture_values only
    when retaining those values is explicitly acceptable. Generator and
    async-generator functions are rejected because returning an iterator is not
    equivalent to completing its execution.
    """
    if chain is None:
        chain = AuditChain(issuer=issuer, private_key=private_key)

    def decorator(f: Callable) -> Callable:
        if inspect.isgeneratorfunction(f) or inspect.isasyncgenfunction(f):
            raise TypeError(
                "@record does not support generator or async-generator functions; "
                "record explicit lifecycle events instead"
            )

        def start(args, kwargs):
            what = {
                "claim": "function_invocation",
                "function": f.__name__,
            }
            if capture_values:
                what["args"] = repr(args)
                what["kwargs"] = repr(kwargs)
            return chain.append(judge(who=issuer, what=what))

        def finish(start_event, result=None, error=None):
            if error is not None:
                return chain.append(
                    judge(
                        who=issuer,
                        what={
                            "claim": "function_result",
                            "function": f.__name__,
                            "status": "error",
                            "error": f"error:{type(error).__name__}",
                        },
                        ref=event_identity_ref(start_event),
                    )
                )

            if auto_verify:
                verification_result = {"status": "completed"}
                if capture_values:
                    verification_result["result"] = repr(result)
                return chain.append(
                    verify(
                        who=issuer,
                        ref=event_identity_ref(start_event),
                        verification_scope=["execution_result"],
                        result=verification_result,
                    )
                )

            what = {
                "claim": "function_result",
                "function": f.__name__,
                "status": "completed",
            }
            if capture_values:
                what["result"] = repr(result)
            return chain.append(
                judge(
                    who=issuer,
                    what=what,
                    ref=event_identity_ref(start_event),
                )
            )

        def begin(args, kwargs):
            try:
                return start(args, kwargs)
            except Exception as exc:
                raise _recording_error(
                    exc,
                    stage="before_execution",
                    call_executed=False,
                ) from exc

        def finish_success(start_event, result):
            try:
                finish(start_event, result=result)
            except Exception as exc:
                raise _recording_error(
                    exc,
                    stage="after_execution",
                    call_executed=True,
                    start_event=start_event,
                ) from exc

        def finish_error(start_event, original_error):
            try:
                finish(start_event, error=original_error)
            except Exception as exc:
                recording_error = _recording_error(
                    exc,
                    stage="after_error",
                    call_executed=True,
                    start_event=start_event,
                )
                raise original_error from recording_error

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start_event = begin(args, kwargs)
            try:
                result = f(*args, **kwargs)
            except BaseException as exc:
                finish_error(start_event, exc)
                raise
            finish_success(start_event, result)
            return result

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start_event = begin(args, kwargs)
            try:
                result = await f(*args, **kwargs)
            except BaseException as exc:
                finish_error(start_event, exc)
                raise
            finish_success(start_event, result)
            return result

        wrapper = async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper
        wrapper._jep_chain = chain
        return wrapper

    return decorator(func) if func is not None else decorator
