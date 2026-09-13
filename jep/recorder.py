"""
@record decorator and global trace manager.
"""

import functools
import inspect
from typing import Callable, Optional

from jep.core.chain import AuditChain
from jep.primitives import judge, terminate, verify


class TraceManager:
    def __init__(self):
        self.chain: Optional[AuditChain] = None
        self.enabled = False

    def enable(
        self,
        issuer: str = "agent:default",
        private_key=None,
        storage_path: Optional[str] = None,
    ):
        self.chain = AuditChain(
            issuer=issuer,
            private_key=private_key,
            storage_path=storage_path,
        )
        self.enabled = True

    def disable(self):
        self.enabled = False

    def view(self):
        if not self.chain or not self.chain.events:
            print("No events recorded.")
            return

        for ev in self.chain.events:
            verb = ev.get("verb", "?")
            who = ev.get("who", "?")
            when = ev.get("when", "?")
            what = str(ev.get("what", "?"))[:40]
            print(f"[{verb}] {who} @ {when} | what={what}...")

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
            chain.append(
                judge(
                    who=issuer,
                    content={
                        "function": f.__name__,
                        "args": repr(args),
                        "kwargs": repr(kwargs),
                    },
                )
            )

        def finish(result=None, error=None):
            content = (
                {"error": f"error:{type(error).__name__}"}
                if error is not None
                else {"result": repr(result)}
            )
            primitive = verify if error is None and auto_verify else terminate
            chain.append(primitive(who=issuer, content=content))

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start(args, kwargs)
            try:
                result = f(*args, **kwargs)
            except BaseException as exc:
                finish(error=exc)
                raise
            finish(result=result)
            return result

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start(args, kwargs)
            try:
                result = await f(*args, **kwargs)
            except BaseException as exc:
                finish(error=exc)
                raise
            finish(result=result)
            return result

        wrapper = async_wrapper if inspect.iscoroutinefunction(f) else sync_wrapper
        wrapper._jep_chain = chain
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
