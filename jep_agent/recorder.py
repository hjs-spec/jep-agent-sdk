"""@record decorator and global trace manager for JEP Core 0.7."""

import functools
import inspect
from typing import Callable, Optional

from jep_agent.core.chain import AuditChain, event_reference
from jep_agent.primitives import judge, terminate, verify


class TraceManager:
    def __init__(self):
        self.chain: Optional[AuditChain] = None
        self.enabled = False

    def enable(self, issuer: str = "agent:default", private_key=None, storage_path: Optional[str] = None):
        self.chain = AuditChain(issuer=issuer, private_key=private_key, storage_path=storage_path)
        self.enabled = True

    def disable(self):
        self.enabled = False

    def view(self):
        if not self.chain or not self.chain.events:
            print("No events recorded.")
            return
        for ev in self.chain.events:
            print(f"[{ev.get('verb', '?')}] {ev.get('who', '?')} @ {ev.get('when', '?')} | what={str(ev.get('what', '?'))[:40]}...")

    def export(self) -> list:
        return self.chain.export() if self.chain else []

    def save(self, path: Optional[str] = None):
        if self.chain:
            self.chain.save(path)


trace = TraceManager()


def record(func: Callable = None, *, issuer: str = "agent:default", private_key=None, chain: Optional[AuditChain] = None, auto_verify: bool = True):
    if chain is None:
        chain = AuditChain(issuer=issuer, private_key=private_key)

    def decorator(f: Callable) -> Callable:
        def start(args, kwargs):
            return chain.append(judge(who=issuer, content={
                "claim": "function-call",
                "function": f.__name__,
                "args": repr(args),
                "kwargs": repr(kwargs),
            }))

        def finish(target, result=None, error=None):
            ref = event_reference(target, pin_artifact=bool(target.get("sig")))
            if error is not None:
                return chain.append(terminate(
                    who=issuer, ref=ref, termination_scope="function-execution",
                    what={"termination_scope":"function-execution","reason":f"error:{type(error).__name__}"},
                ))
            if auto_verify:
                return chain.append(verify(
                    who=issuer, ref=ref, verification_scope="function_execution",
                    result={"status":"completed","value":repr(result)},
                ))
            return chain.append(judge(who=issuer, content={"claim":"function-result","result":repr(result)}))

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            target = start(args, kwargs)
            try:
                result = f(*args, **kwargs)
            except BaseException as exc:
                finish(target, error=exc)
                raise
            finish(target, result=result)
            return result

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            target = start(args, kwargs)
            try:
                result = await f(*args, **kwargs)
            except BaseException as exc:
                finish(target, error=exc)
                raise
            finish(target, result=result)
            return result

        wrapper = async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper
        wrapper._jep_chain = chain
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
