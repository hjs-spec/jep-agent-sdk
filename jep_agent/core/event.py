"""JEP Core 0.7 event construction, JCS canonicalization, and detached JWS signing."""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
from copy import deepcopy
from typing import Any, Dict, Optional

try:
    import jcs
    HAS_JCS = True
except ImportError:
    HAS_JCS = False

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _compute_what(content: bytes, algorithm: str = "sha256") -> str:
    if algorithm != "sha256":
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _uuid_urn() -> str:
    return f"urn:uuid:{uuid.uuid4()}"


def _validate_verb_shape(verb: str, what: Any, ref: Any) -> None:
    if what is None:
        raise ValueError("what is required")
    if verb == "D":
        if not isinstance(what, dict) or "delegatee" not in what or "scope" not in what:
            raise ValueError("D requires what.delegatee and what.scope")
    elif verb == "T":
        if ref is None:
            raise ValueError("T requires ref")
        if not isinstance(what, dict) or "termination_scope" not in what:
            raise ValueError("T requires what.termination_scope")
    elif verb == "V":
        if ref is None:
            raise ValueError("V requires ref")
        if not isinstance(what, dict) or "verification_scope" not in what or "result" not in what:
            raise ValueError("V requires what.verification_scope and what.result")


def build_event(
    verb: str,
    who: str,
    what: Any,
    aud: Optional[str] = None,
    ref: Any = None,
    extensions: Optional[Dict[str, Any]] = None,
    ext_crit: Optional[list[str]] = None,
    when: Optional[int] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an unsigned JEP Core 0.7 event.

    Freshness nonces/challenges are profile mechanisms and belong in ext
    or a transport/profile layer, not as a mandatory Core member.
    """
    if verb not in ("J", "D", "T", "V"):
        raise ValueError(f"Invalid verb: {verb}. Must be J, D, T, or V.")
    _validate_verb_shape(verb, what, ref)
    ev: Dict[str, Any] = {
        "jep": "1",
        "id": event_id or _uuid_urn(),
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
    if extensions:
        ev["ext"] = deepcopy(extensions)
    if ext_crit:
        ev["ext_crit"] = list(ext_crit)
    return ev


def canonicalize(ev: Dict[str, Any]) -> bytes:
    """Return the JEP Signing Payload: JCS(unsigned event)."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    payload = {k: v for k, v in ev.items() if k != "sig"}
    return jcs.canonicalize(payload)


def event_hash(ev: Dict[str, Any]) -> str:
    """Hash the exact full signed event artifact, including sig."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    return "sha256:" + hashlib.sha256(jcs.canonicalize(ev)).hexdigest()


def sign_event(ev: Dict[str, Any], private_key) -> Dict[str, Any]:
    """Attach a detached compact JWS over the JCS unsigned payload."""
    if not HAS_CRYPTO:
        raise ImportError("cryptography package required.")
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Only Ed25519 private keys are supported by this baseline.")
    payload_bytes = canonicalize(ev)
    protected_header = json.dumps({"alg": "EdDSA", "typ": "jep-event+jws"}, separators=(",", ":"))
    protected_b64 = _base64url_encode(protected_header.encode("utf-8"))
    payload_b64 = _base64url_encode(payload_bytes)
    signing_input = (protected_b64 + "." + payload_b64).encode("ascii")
    signature = private_key.sign(signing_input)
    signed = deepcopy(ev)
    signed["sig"] = protected_b64 + ".." + _base64url_encode(signature)
    return signed


def verify_event_signature(ev: Dict[str, Any], public_key) -> bool:
    if not HAS_CRYPTO or not isinstance(public_key, Ed25519PublicKey):
        return False
    sig = ev.get("sig")
    if not isinstance(sig, str):
        return False
    parts = sig.split(".")
    if len(parts) != 3 or parts[1] != "":
        return False
    protected_b64, _, sig_b64 = parts
    try:
        header = json.loads(_base64url_decode(protected_b64))
        if not isinstance(header, dict) or header.get("alg") != "EdDSA" or "crit" in header or header.get("b64", True) is not True:
            return False
        payload_b64 = _base64url_encode(canonicalize(ev))
        signing_input = (protected_b64 + "." + payload_b64).encode("ascii")
        public_key.verify(_base64url_decode(sig_b64), signing_input)
        return True
    except Exception:
        return False


def verify_payload_integrity(ev: Dict[str, Any], public_key=None) -> bool:
    """Compatibility helper; detached JWS integrity requires the public key."""
    return bool(public_key is not None and verify_event_signature(ev, public_key))
