"""
JAC-01 extension support.
"""

from typing import Any, Callable, Dict, Optional

from jep.core.event import build_event


def build_jac_event(
    verb: str,
    who: str,
    content: Any = None,
    task_based_on: Optional[str] = None,
    extensions: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Build JAC-01 compliant event with task_based_on."""
    from jep.primitives import _content_to_what

    what = _content_to_what(content)
    return build_event(
        verb,
        who,
        what=what,
        task_based_on=task_based_on,
        extensions=extensions,
        **kwargs,
    )


def verify_jac_core(
    event: Dict[str, Any],
    signature_verifier: Optional[Callable] = None,
    parent_exists_lookup: Optional[Callable[[str], bool]] = None,
    task_parent_lookup: Optional[Callable[[str], bool]] = None,
) -> str:
    """
    JAC-01 core verification logic (Section 1.4).
    Returns: VALID, VALID_WITH_FAULT, or INVALID: reason
    """
    if signature_verifier and not signature_verifier(event):
        return "INVALID: signature verification failed"

    ref = event.get("ref")
    if ref and parent_exists_lookup and not parent_exists_lookup(ref):
        return "INVALID: parent event not found"

    if event.get("verb") == "J" and ref is not None:
        return "INVALID: J event with non-null ref"

    task_based_on = event.get("task_based_on")
    if task_based_on and task_parent_lookup:
        if not task_parent_lookup(task_based_on):
            extensions = event.get("extensions", {})
            if "https://jac.org/fault" in extensions:
                fault = extensions["https://jac.org/fault"]
                if fault.get("expected_parent") == task_based_on:
                    return "VALID_WITH_FAULT"
            return "INVALID: parent task not found"

    return "VALID"
