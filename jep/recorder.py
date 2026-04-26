"""
@record decorator and global trace manager.
"""

import functools
from typing import Any, Callable, Optional

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
    auto_verify: bool = True,
):
    chain = AuditChain(issuer=issuer, private_key=private_key)

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            content = {
                "function": f.__name__,
                "args": repr(args),
                "kwargs": repr(kwargs),
            }
            j_event = judge(who=issuer, content=content)
            chain.append(j_event)

            try:
                result = f(*args, **kwargs)
                status = "success"
                result_content = {"result": repr(result)}
            except Exception as e:
                result = None
                status = f"error:{type(e).__name__}"
                result_content = {"error": status}
                raise
            finally:
                if auto_verify and status == "success":
                    v_event = verify(who=issuer, content=result_content)
                    chain.append(v_event)
                else:
                    t_event = terminate(
                        who=issuer, content=result_content
                    )
                    chain.append(t_event)

            return result

        wrapper._jep_chain = chain
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
