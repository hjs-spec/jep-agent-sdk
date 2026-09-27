"""Current JWS headers use UTF-8, without rewriting historical profiles."""

import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.event import (
    _base64url_encode,
    build_event,
    canonicalize,
    event_hash,
    sign_event,
    verify_event_signature,
)
from jep_agent.core.verifier import JEPVerifier


def signed_header(event, key, raw):
    protected = _base64url_encode(raw)
    payload = _base64url_encode(canonicalize(event))
    signature = key.sign((protected + "." + payload).encode("ascii"))
    return {**event, "sig": protected + ".." + _base64url_encode(signature)}


@pytest.mark.parametrize(
    "encoding", ["utf-16", "utf-16-le", "utf-16-be", "utf-32", "utf-32-le", "utf-32-be"]
)
def test_non_utf8_header_does_not_consume_identity(encoding):
    key = Ed25519PrivateKey.generate()
    original = sign_event(build_event("J", "did:example:test", {"claim": "test"}), key)
    raw = json.dumps({"alg": "Ed25519", "kid": "test-key"}).encode(encoding)
    bad = signed_header(original, key, raw)
    verifier = JEPVerifier()
    for mode in ("archival", "acceptance"):
        result = verifier.verify_result(bad, key.public_key(), mode=mode)
        assert result["status"] == "invalid"
        assert result["checks"]["cryptographic"] == "fail"
        if mode == "acceptance":
            assert result["acceptance"] == {"outcome": "rejected", "effect_applied": False}
    first = verifier.verify_result(original, key.public_key(), mode="acceptance")
    retry = verifier.verify_result(original, key.public_key(), mode="acceptance")
    assert first["acceptance"] == {"outcome": "accepted", "effect_applied": True}
    assert retry["acceptance"] == {"outcome": "already_accepted", "effect_applied": False}


def test_valid_utf8_header_need_not_be_canonical_json():
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "did:example:test", {"claim": "test"})
    raw = json.dumps(
        {"note": {"text": "合法", "number": 1e20}, "kid": "test-key", "alg": "Ed25519"},
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
    signed = signed_header(event, key, raw)
    result = JEPVerifier().verify_result(signed, key.public_key())
    assert result["status"] == "valid"
    assert result["event_hash"] == event_hash(signed)


def test_explicit_legacy_profile_retains_original_decoder():
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "did:example:test", {"claim": "legacy fixture"})
    raw = json.dumps({"alg": "EdDSA"}).encode("utf-16")
    signed = signed_header(event, key, raw)
    assert verify_event_signature(signed, key.public_key(), signature_profile="legacy-eddsa")
    assert not verify_event_signature(signed, key.public_key())
