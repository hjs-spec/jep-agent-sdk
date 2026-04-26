"""
JEP Event Construction, Canonicalization, and JWS Signing.
Strictly compliant with draft-wang-jep-judgment-event-protocol-04.
"""

import uuid
import time
import json
import base64
import hashlib
from typing import Optional, Dict, Any

try:
    import jcs
    HAS_JCS = True
except ImportError:
    HAS_JCS = False

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


def _compute_what(content: bytes, algorithm: str = "sha256") -> str:
    if algorithm == "sha256":
        h = hashlib.sha256(content).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    return f"{algorithm}:{h}"


def build_event(
    verb: str,
    who: str,
    what: Optional[str] = None,
    aud: Optional[str] = None,
    ref: Optional[str] = None,
    task_based_on: Optional[str] = None,
    extensions: Optional[Dict[str, Any]] = None,
    nonce: Optional[str] = None,
    when: Optional[int] = None,
) -> Dict[str, Any]:
    if nonce is None:
        nonce = str(uuid.uuid4())
    if when is None:
        when = int(time.time())
    
    if verb not in ("J", "D", "T", "V"):
        raise ValueError(f"Invalid verb: {verb}. Must be J, D, T, or V.")
    
    ev = {
        "jep": "1",
        "verb": verb,
        "who": who,
        "when": when,
        "what": what,
        "nonce": nonce,
        "aud": aud,
        "ref": ref,
        "sig": "",
    }
    
    if task_based_on is not None:
        ev["task_based_on"] = task_based_on
    if extensions is not None:
        ev["extensions"] = extensions
    
    return ev


def canonicalize(ev: Dict[str, Any]) -> bytes:
    if not HAS_JCS:
        raise ImportError("jcs package required for RFC 8785. Install: pip install jcs")
    
    payload = {k: v for k, v in ev.items() if k != "sig"}
    return jcs.canonicalize(payload)


def event_hash(ev: Dict[str, Any]) -> str:
    return _compute_what(canonicalize(ev), "sha256")


def sign_event(ev: Dict[str, Any], private_key) -> Dict[str, Any]:
    if not HAS_CRYPTO:
        raise ImportError("cryptography package required.")
    
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Only Ed25519 private keys are supported.")
    
    payload_bytes = canonicalize(ev)
    
    protected_header = json.dumps({"alg": "EdDSA"}, separators=(',', ':'))
    protected_b64 = _base64url_encode(protected_header.encode('utf-8'))
    payload_b64 = _base64url_encode(payload_bytes)
    
    signing_input = (protected_b64 + "." + payload_b64).encode('utf-8')
    signature = private_key.sign(signing_input)
    sig_b64 = _base64url_encode(signature)
    
    jws_token = protected_b64 + "." + payload_b64 + "." + sig_b64
    ev["sig"] = jws_token
    return ev


def verify_event_signature(ev: Dict[str, Any], public_key) -> bool:
    if not HAS_CRYPTO or not ev.get("sig"):
        return False
    
    if not isinstance(public_key, Ed25519PublicKey):
        return False
    
    parts = ev["sig"].split(".")
    if len(parts) != 3:
        return False
    
    protected_b64, payload_b64, sig_b64 = parts
    signing_input = (protected_b64 + "." + payload_b64).encode('utf-8')
    
    try:
        sig_bytes = _base64url_decode(sig_b64)
        public_key.verify(sig_bytes, signing_input)
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


def verify_payload_integrity(ev: Dict[str, Any]) -> bool:
    if not ev.get("sig"):
        return False
    
    parts = ev["sig"].split(".")
    if len(parts) != 3:
        return False
    
    payload_b64 = parts[1]
    try:
        payload_bytes = _base64url_decode(payload_b64)
    except Exception:
        return False
    
    current_bytes = canonicalize(ev)
    return payload_bytes == current_bytes
