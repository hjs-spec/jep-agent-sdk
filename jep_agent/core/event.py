"""JEP Core 0.7 event construction, canonicalization, hashing, and signing."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

try:
    import jcs

    HAS_JCS = True
except ImportError:
    HAS_JCS = False

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

CORE_PROFILE = "jep-core-0.7"
WIRE_VERSION = "1"
VERBS = {"J", "D", "T", "V"}
TOP_LEVEL_FIELDS = {
    "jep",
    "id",
    "verb",
    "who",
    "when",
    "what",
    "aud",
    "ref",
    "ext",
    "ext_crit",
    "sig",
}


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _compute_what(content: bytes, algorithm: str = "sha256") -> str:
    if algorithm != "sha256":
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _event_identity_ref(event: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "type": "jep:event",
        "value": {"who": event["who"], "id": event["id"]},
    }


def _validate_shape(ev: Mapping[str, Any]) -> None:
    unknown = set(ev) - TOP_LEVEL_FIELDS
    if unknown:
        raise ValueError(f"Unknown Core field(s): {', '.join(sorted(unknown))}")

    for field in ("jep", "id", "verb", "who", "when", "what", "sig"):
        if field not in ev:
            raise ValueError(f"Missing required Core field: {field}")

    if ev["jep"] != WIRE_VERSION:
        raise ValueError("jep must be '1'")
    if not isinstance(ev["id"], str) or not ev["id"] or not ev["id"].isascii():
        raise ValueError("id must be a non-empty ASCII string")
    if ev["verb"] not in VERBS:
        raise ValueError("verb must be J, D, T, or V")
    if not isinstance(ev["who"], str) or not ev["who"]:
        raise ValueError("who must be a non-empty string")
    if type(ev["when"]) is not int:
        raise ValueError("when must be an integer")
    if not isinstance(ev["what"], (dict, str)):
        raise ValueError("what must be an object or algorithm-tagged digest")

    if ev.get("aud") is not None:
        if not isinstance(ev["aud"], str) or not ev["aud"]:
            raise ValueError("aud must be a non-empty string")

    if ev.get("ext") is not None and not isinstance(ev["ext"], dict):
        raise ValueError("ext must be an object")

    if ev.get("ext_crit") is not None:
        crit = ev["ext_crit"]
        valid = (
            isinstance(crit, list)
            and len(crit) == len(set(crit))
            and all(isinstance(item, str) and item for item in crit)
        )
        if not valid:
            raise ValueError("ext_crit must be a unique array of non-empty strings")

    what = ev["what"]
    if ev["verb"] == "D":
        valid_delegatee = isinstance(what, dict) and isinstance(
            what.get("delegatee"), str
        )
        if not valid_delegatee or not what.get("delegatee") or "scope" not in what:
            raise ValueError("D requires object-valued what with delegatee and scope")
    elif ev["verb"] == "T":
        valid_scope = isinstance(what, dict) and isinstance(
            what.get("termination_scope"), str
        )
        if "ref" not in ev or not valid_scope or not what.get("termination_scope"):
            raise ValueError("T requires ref and what.termination_scope")
    elif ev["verb"] == "V":
        if (
            "ref" not in ev
            or not isinstance(what, dict)
            or "verification_scope" not in what
            or "result" not in what
        ):
            raise ValueError(
                "V requires ref, what.verification_scope, and what.result"
            )


def build_event(
    verb: str,
    who: str,
    what: Any,
    *,
    event_id: Optional[str] = None,
    aud: Optional[str] = None,
    ref: Any = None,
    ext: Optional[Dict[str, Dict[str, Any]]] = None,
    ext_crit: Optional[list[str]] = None,
    when: Optional[int] = None,
) -> Dict[str, Any]:
    """Construct a new unsigned Core 0.7 event.

    Freshness nonces and challenges belong to profiles or extensions, not Core.
    """
    ev: Dict[str, Any] = {
        "jep": WIRE_VERSION,
        "id": event_id or f"urn:uuid:{uuid.uuid4()}",
        "verb": verb,
        "who": who,
        "when": int(time.time()) if when is None else when,
        "what": deepcopy(what),
        "sig": "",
    }
    if aud is not None:
        ev["aud"] = aud
    if ref is not None:
        ev["ref"] = deepcopy(ref)
    if ext:
        ev["ext"] = deepcopy(ext)
    if ext_crit:
        ev["ext_crit"] = list(ext_crit)
    _validate_shape(ev)
    return ev


def canonicalize(ev: Mapping[str, Any]) -> bytes:
    """Return the JEP Signing Payload: JCS(unsigned event)."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    unsigned = {key: deepcopy(value) for key, value in ev.items() if key != "sig"}
    return jcs.canonicalize(unsigned)


def event_hash(ev: Mapping[str, Any]) -> str:
    """Hash the exact full signed artifact, including sig."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    return "sha256:" + hashlib.sha256(jcs.canonicalize(dict(ev))).hexdigest()


def sign_event(ev: Dict[str, Any], private_key) -> Dict[str, Any]:
    """Apply the baseline detached compact JWS signature."""
    if not HAS_CRYPTO or not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Ed25519 private key required")

    _validate_shape(ev)
    header = json.dumps({"alg": "EdDSA"}, separators=(",", ":")).encode("utf-8")
    protected = _base64url_encode(header)
    payload = canonicalize(ev)
    signing_input = (protected + "." + _base64url_encode(payload)).encode("ascii")
    signature = _base64url_encode(private_key.sign(signing_input))

    signed = deepcopy(ev)
    signed["sig"] = protected + ".." + signature
    return signed


def verify_event_signature(ev: Mapping[str, Any], public_key) -> bool:
    if not HAS_CRYPTO or not isinstance(public_key, Ed25519PublicKey):
        return False

    sig = ev.get("sig")
    if not isinstance(sig, str):
        return False

    parts = sig.split(".")
    if len(parts) != 3 or parts[1] != "":
        return False

    try:
        header = json.loads(_base64url_decode(parts[0]))
        valid_header = (
            isinstance(header, dict)
            and header.get("alg") == "EdDSA"
            and "crit" not in header
            and header.get("b64", True) is True
        )
        if not valid_header:
            return False

        encoded_payload = _base64url_encode(canonicalize(ev))
        signing_input = (parts[0] + "." + encoded_payload).encode("ascii")
        public_key.verify(_base64url_decode(parts[2]), signing_input)
        return True
    except (InvalidSignature, ValueError, TypeError, json.JSONDecodeError):
        return False


def verify_payload_integrity(ev: Mapping[str, Any], public_key=None) -> bool:
    """Verify shape, and signature integrity when a trusted key is supplied."""
    try:
        _validate_shape(ev)
    except (TypeError, ValueError):
        return False

    if public_key is None:
        sig = ev.get("sig")
        return (
            isinstance(sig, str)
            and sig.count(".") == 2
            and sig.split(".")[1] == ""
        )
    return verify_event_signature(ev, public_key)


event_identity_ref = _event_identity_ref
