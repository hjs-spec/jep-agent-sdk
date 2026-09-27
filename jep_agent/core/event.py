"""JEP Core 0.7 event construction, canonicalization, hashing, and signing."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
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
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]*", value):
        raise ValueError("Expected unpadded base64url")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if _base64url_encode(raw) != value:
        raise ValueError("Non-canonical base64url")
    return raw


def _validate_json(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        _binary64_numbers(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite JSON number")
    elif isinstance(value, str):
        value.encode("utf-8", errors="strict")
    elif isinstance(value, list):
        for item in value:
            _validate_json(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON member names must be strings")
            _validate_json(key)
            _validate_json(item)
    else:
        raise ValueError("Unsupported JSON value")


def parse_json(text: str) -> Any:
    """Parse wire JSON without silently discarding duplicate members."""

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON member: {key}")
            result[key] = value
        return result

    value = json.loads(text, object_pairs_hook=pairs)
    _validate_json(value)
    return value


def _validate_digest(value: Any) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*:[0-9a-f]+", value):
        raise ValueError("Expected algorithm-tagged lowercase-hex digest")
    if value.startswith("sha256:") and len(value) != 71:
        raise ValueError("SHA-256 digest must contain 64 hex characters")


def _validate_ref(value: Any) -> None:
    if isinstance(value, str):
        _validate_digest(value)
        return
    if not isinstance(value, dict) or "type" not in value or "value" not in value:
        raise ValueError("ref requires a digest or typed reference")
    if not isinstance(value["type"], str) or not value["type"]:
        raise ValueError("Reference type must be non-empty")
    if value["type"] == "jep:event":
        identity = value["value"]
        if not isinstance(identity, dict) or set(identity) != {"who", "id"}:
            raise ValueError("Event reference must contain exactly who and id")
        if not all(isinstance(identity[k], str) and identity[k] for k in ("who", "id")):
            raise ValueError("Event reference identity must be non-empty strings")
    if "hash" in value:
        _validate_digest(value["hash"])


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
    if not isinstance(ev, dict):
        raise ValueError("Event must be an object")
    _validate_json(ev)
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
    if not isinstance(ev["verb"], str) or ev["verb"] not in VERBS:
        raise ValueError("verb must be J, D, T, or V")
    if not isinstance(ev["who"], str) or not ev["who"]:
        raise ValueError("who must be a non-empty string")
    if type(ev["when"]) is not int or abs(ev["when"]) > 2**53 - 1:
        raise ValueError("when must be an integer")
    if not isinstance(ev["what"], (dict, str)):
        raise ValueError("what must be an object or algorithm-tagged digest")
    if isinstance(ev["what"], str):
        _validate_digest(ev["what"])
    elif not ev["what"]:
        raise ValueError("what object must not be empty")
    if not isinstance(ev["sig"], str):
        raise ValueError("Baseline sig must be a string")
    if "ref" in ev:
        _validate_ref(ev["ref"])

    if "aud" in ev:
        if not isinstance(ev["aud"], str) or not ev["aud"]:
            raise ValueError("aud must be a non-empty string")

    if "ext" in ev:
        if not isinstance(ev["ext"], dict):
            raise ValueError("ext must be an object")
        if not all(k and isinstance(v, dict) for k, v in ev["ext"].items()):
            raise ValueError("Extensions require non-empty identifiers and object bodies")

    if "ext_crit" in ev:
        crit = ev["ext_crit"]
        valid = (
            isinstance(crit, list)
            and all(isinstance(item, str) and item for item in crit)
            and len(crit) == len(set(crit))
        )
        if not valid:
            raise ValueError("ext_crit must be a unique array of non-empty strings")

    what = ev["what"]
    if ev["verb"] == "D":
        valid_delegatee = isinstance(what, dict) and isinstance(what.get("delegatee"), str)
        if not valid_delegatee or not what.get("delegatee") or "scope" not in what:
            raise ValueError("D requires object-valued what with delegatee and scope")
    elif ev["verb"] == "T":
        valid_scope = isinstance(what, dict) and isinstance(what.get("termination_scope"), str)
        if "ref" not in ev or not valid_scope or not what.get("termination_scope"):
            raise ValueError("T requires ref and what.termination_scope")
    elif ev["verb"] == "V":
        if (
            "ref" not in ev
            or not isinstance(what, dict)
            or "verification_scope" not in what
            or "result" not in what
        ):
            raise ValueError("V requires ref, what.verification_scope, and what.result")
        scopes = what["verification_scope"]
        if not (
            isinstance(scopes, list)
            and scopes
            and all(isinstance(item, str) and item for item in scopes)
            and len(scopes) == len(set(scopes))
        ):
            raise ValueError("verification_scope must be a non-empty unique string array")


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
        "id": f"urn:uuid:{uuid.uuid4()}" if event_id is None else event_id,
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
    if ext is not None:
        ev["ext"] = deepcopy(ext)
    if ext_crit is not None:
        ev["ext_crit"] = deepcopy(ext_crit)
    _validate_shape(ev)
    return ev


def _binary64_numbers(value):
    """Adapt integer tokens to their preserved JCS binary64 value.

    JSON.stringify(1e20) emits an integer token. Parsing that token into a
    Python int must not invalidate that number. Accept an exact binary64
    integer or its canonical shortest decimal spelling, which can differ
    (1000000000000000100 represents the float 1000000000000000128).
    Other precision-losing integers remain rejected. Never edit the input.
    """
    if type(value) is int and abs(value) > 2**53 - 1:
        try:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Integer exceeds binary64 range")
            if int(number) != value and jcs.canonicalize(number) != str(value).encode("ascii"):
                raise ValueError("Integer is neither exact binary64 nor its canonical JCS spelling")
        except OverflowError as exc:
            raise ValueError("Integer exceeds binary64 range") from exc
        return number
    if isinstance(value, dict):
        return {key: _binary64_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_binary64_numbers(item) for item in value]
    return value


def canonicalize(ev: Mapping[str, Any]) -> bytes:
    """Return the JEP Signing Payload: JCS(unsigned event)."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    unsigned = {key: deepcopy(value) for key, value in ev.items() if key != "sig"}
    _validate_json(unsigned)
    return jcs.canonicalize(_binary64_numbers(unsigned))


def event_hash(ev: Mapping[str, Any]) -> str:
    """Hash the exact full signed artifact, including sig."""
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    _validate_json(ev)
    return "sha256:" + hashlib.sha256(jcs.canonicalize(_binary64_numbers(dict(ev)))).hexdigest()


def sign_event(ev: Dict[str, Any], private_key, *, kid: Optional[str] = None) -> Dict[str, Any]:
    """Apply the baseline detached compact JWS signature."""
    if not HAS_CRYPTO or not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Ed25519 private key required")

    _validate_shape(ev)
    kid = f"{ev['who']}#key-1" if kid is None else kid
    if not isinstance(kid, str) or not kid:
        raise ValueError("kid must be a non-empty key identifier")
    header = json.dumps({"alg": "Ed25519", "kid": kid}, separators=(",", ":")).encode("utf-8")
    protected = _base64url_encode(header)
    payload = canonicalize(ev)
    signing_input = (protected + "." + _base64url_encode(payload)).encode("ascii")
    signature = _base64url_encode(private_key.sign(signing_input))

    signed = deepcopy(ev)
    signed["sig"] = protected + ".." + signature
    return signed


def verify_event_signature(
    ev: Mapping[str, Any], public_key, *, signature_profile: str = "baseline-0.7"
) -> bool:
    if not HAS_CRYPTO or not isinstance(public_key, Ed25519PublicKey):
        return False

    if not isinstance(ev, dict):
        return False
    sig = ev.get("sig")
    if not isinstance(sig, str):
        return False

    parts = sig.split(".")
    if len(parts) != 3 or parts[1] != "":
        return False

    try:
        header_bytes = _base64url_decode(parts[0])
        # JWS current-baseline headers are UTF-8; do not auto-detect UTF-16/32.
        # Historical decoding stays behind its explicit profile selection.
        header = parse_json(
            header_bytes.decode("utf-8") if signature_profile == "baseline-0.7" else header_bytes
        )
        algorithm = {"baseline-0.7": "Ed25519", "legacy-eddsa": "EdDSA"}.get(signature_profile)
        valid_header = (
            isinstance(header, dict)
            and algorithm is not None
            and header.get("alg") == algorithm
            and "crit" not in header
            and header.get("b64", True) is True
        )
        if signature_profile == "baseline-0.7":
            valid_header = (
                valid_header and isinstance(header.get("kid"), str) and bool(header["kid"])
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
        return isinstance(sig, str) and sig.count(".") == 2 and sig.split(".")[1] == ""
    return verify_event_signature(ev, public_key)


event_identity_ref = _event_identity_ref
