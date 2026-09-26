"""J/D/T/V convenience constructors for JEP Core 0.7."""

from typing import Any, Dict, Optional

from jep_agent.core.event import build_event


def judge(who: str, content: Any = None, what: Any = None, **kwargs) -> Dict[str, Any]:
    if what is None:
        what = content if isinstance(content, dict) and "claim" in content else {"claim": content}
    return build_event("J", who, what=what, **kwargs)


def delegate(
    who: str,
    delegatee: Optional[str] = None,
    scope: Any = None,
    *,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None:
        if delegatee is None or scope is None:
            raise ValueError("delegate requires delegatee and scope")
        what = {"delegatee": delegatee, "scope": scope}
    return build_event("D", who, what=what, **kwargs)


def terminate(
    who: str,
    ref: Any,
    termination_scope: Any = "future-reliance",
    *,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None:
        what = {"termination_scope": termination_scope}
    return build_event("T", who, what=what, ref=ref, **kwargs)


def verify(
    who: str,
    ref: Any,
    verification_scope: Any = "external_evidence",
    result: Any = None,
    *,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None:
        what = {"verification_scope": verification_scope, "result": result}
    return build_event("V", who, what=what, ref=ref, **kwargs)
