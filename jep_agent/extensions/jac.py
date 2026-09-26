"""Local task-link companion helpers; not a claim of JAC protocol conformance.

The legacy function names remain for callers, but newly constructed events use
Core 0.7 and carry task relationships in ext['jep-agent.jac'].
"""

from copy import deepcopy
from typing import Any, Callable, Dict, Optional

from jep_agent.core.event import _validate_ref, _validate_shape, build_event

JAC_EXTENSION = "jep-agent.jac"


def build_jac_event(
    verb: str,
    who: str,
    content: Any = None,
    task_based_on: Any = None,
    extensions: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Build a Core event with explicitly separate local task-link metadata."""
    ext = deepcopy(extensions or {})
    if task_based_on is not None:
        _validate_ref(task_based_on)
        if JAC_EXTENSION in ext:
            raise ValueError("Pass task_based_on once; conflicting companion extension")
        ext[JAC_EXTENSION] = {"task_based_on": deepcopy(task_based_on)}
    what = kwargs.pop("what", content)
    return build_event(verb, who, what, ext=ext, **kwargs)


def verify_jac_core(
    event: Dict[str, Any],
    signature_verifier: Optional[Callable] = None,
    parent_exists_lookup: Optional[Callable] = None,
    task_parent_lookup: Optional[Callable] = None,
) -> str:
    """Check the local task-link companion, not authorization or causality.

    Required external lookups must be supplied before returning VALID.
    This compatibility name does not make these checks part of JEP Core.
    """
    try:
        _validate_shape(event)
    except (ValueError, TypeError) as exc:
        return f"INVALID: {exc}"
    if event.get("ext_crit"):
        return "INVALID: unsupported critical extension"
    if signature_verifier is None:
        return "UNVERIFIED: trusted signature verifier required"
    if not signature_verifier(event):
        return "INVALID: signature verification failed"
    ref = event.get("ref")
    if ref is not None:
        if parent_exists_lookup is None:
            return "UNVERIFIED: parent event lookup required"
        if not parent_exists_lookup(ref):
            return "INVALID: parent event not found"
    task_ref = event.get("ext", {}).get(JAC_EXTENSION, {}).get("task_based_on")
    if task_ref is not None:
        try:
            _validate_ref(task_ref)
        except ValueError as exc:
            return f"INVALID: {exc}"
        if task_parent_lookup is None:
            return "UNVERIFIED: parent task lookup required"
        if not task_parent_lookup(task_ref):
            fault = event.get("ext", {}).get("https://jac.org/fault", {})
            if fault.get("expected_parent") == task_ref:
                return "VALID_WITH_FAULT"
            return "INVALID: parent task not found"
    return "VALID"
