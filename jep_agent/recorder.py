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


def record(
    func: Callable = None,
    *,
    issuer: str = "agent:default",
    private_key=None,
    chain: Optional[AuditChain] = None,
    auto_verify: bool = True,
):
    if chain is None:
        chain = AuditChain(issuer=issuer, private_key=private_key)

    def decorator(f: Callable) -> Callable:
        def start(args, kwargs):
            return chain.append(
                judge(
                    who=issuer,
                    what={
                        "claim": "function_invocation",
                        "function": f.__name__,
                        "args": repr(args),
                        "kwargs": repr(kwargs),
                    },
                )
            )

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
                return chain.append(
                    verify(
                        who=issuer,
                        ref=event_identity_ref(start_event),
                        verification_scope=["execution_result"],
                        result={"status": "completed", "result": repr(result)},
                    )
                )
            return chain.append(
                judge(
                    who=issuer,
                    what={
                        "claim": "function_result",
                        "function": f.__name__,
                        "status": "completed",
                        "result": repr(result),
                    },
                    ref=event_identity_ref(start_event),
                )
            )

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start_event = start(args, kwargs)
            try:
                result = f(*args, **kwargs)
            except BaseException as exc:
                finish(start_event, error=exc)
                raise
            finish(start_event, result=result)
            return result

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start_event = start(args, kwargs)
            try:
                result = await f(*args, **kwargs)
            except BaseException as exc:
                finish(start_event, error=exc)
                raise
            finish(start_event, result=result)
            return result

        wrapper = async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper
        wrapper._jep_chain = chain
        return wrapper

    return decorator(func) if func is not None else decorator
