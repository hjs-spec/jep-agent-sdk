"""JEP Core 0.7 J/D/T/V primitive constructors."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from jep_agent.core.event import build_event


def judge(
    who: str,
    content: Any = None,
    what: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None:
        what = content if content is not None else {"claim": "judgment"}
    return build_event("J", who, what, **kwargs)


def delegate(
    who: str,
    *,
    delegatee: str,
    scope: Any,
    constraints: Optional[Iterable[Any]] = None,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    body = dict(what or {})
    body["delegatee"] = delegatee
    body["scope"] = scope
    if constraints is not None:
        body["constraints"] = list(constraints)
    return build_event("D", who, body, **kwargs)


def terminate(
    who: str,
    *,
    ref: Any,
    termination_scope: str = "future_reliance",
    reason: Optional[str] = None,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    body = dict(what or {})
    body["termination_scope"] = termination_scope
    if reason is not None:
        body["reason"] = reason
    return build_event("T", who, body, ref=ref, **kwargs)


def verify(
    who: str,
    *,
    ref: Any,
    verification_scope: Any,
    result: Any,
    what: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    body = dict(what or {})
    body["verification_scope"] = verification_scope
    body["result"] = result
    return build_event("V", who, body, ref=ref, **kwargs)
