"""
J/D/T/V primitives — thin wrappers around build_event.
"""

import json
from typing import Any, Dict, Optional

from jep.core.event import _compute_what, build_event


def _content_to_what(content: Any) -> Optional[str]:
    if content is None:
        return None
    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = json.dumps(
            content, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    return _compute_what(data, "sha256")


def judge(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("J", who, what=what, **kwargs)


def delegate(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("D", who, what=what, **kwargs)


def terminate(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("T", who, what=what, **kwargs)


def verify(
    who: str,
    ref: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("V", who, what=what, ref=ref, **kwargs)"""
J/D/T/V primitives — thin wrappers around build_event.
"""

import json
from typing import Any, Dict, Optional

from jep.core.event import _compute_what, build_event


def _content_to_what(content: Any) -> Optional[str]:
    if content is None:
        return None
    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = json.dumps(
            content, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    return _compute_what(data, "sha256")


def judge(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("J", who, what=what, **kwargs)


def delegate(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("D", who, what=what, **kwargs)


def terminate(
    who: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("T", who, what=what, **kwargs)


def verify(
    who: str,
    ref: str,
    content: Any = None,
    what: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    if what is None and content is not None:
        what = _content_to_what(content)
    return build_event("V", who, what=what, ref=ref, **kwargs)
