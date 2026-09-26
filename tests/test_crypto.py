"""Test Core 0.7 detached signing and tamper detection."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.event import (
    build_event,
    sign_event,
    verify_event_signature,
    verify_payload_integrity,
)


def test_sign_and_verify_detached_jws():
    key = Ed25519PrivateKey.generate()
    signed = sign_event(build_event("J", "agent", {"claim": "x"}), key)
    assert signed["sig"].split(".")[1] == ""
    assert verify_event_signature(signed, key.public_key())


def test_tamper_detection():
    key = Ed25519PrivateKey.generate()
    signed = sign_event(build_event("J", "agent", {"claim": "x"}), key)
    signed["what"] = {"claim": "tampered"}
    assert not verify_payload_integrity(signed, key.public_key())


def test_integer_wire_spelling_preserves_large_jcs_number():
    import json

    import pytest

    from jep_agent.core.event import canonicalize, event_hash

    key = Ed25519PrivateKey.generate()
    signed = sign_event(
        build_event(
            "J",
            "actor",
            {"value": 1e20, "shortest": 1.0000000000000001e18, "negative": -1.0000000000000001e18},
        ),
        key,
    )
    wire = (
        json.dumps(signed)
        .replace("1e+20", "100000000000000000000")
        .replace("1.0000000000000001e+18", "1000000000000000100")
    )
    parsed = json.loads(wire)
    assert verify_event_signature(parsed, key.public_key())
    assert event_hash(parsed) == event_hash(signed)
    assert type(signed["what"]["value"]) is float
    for value in (2**53 + 1, 1000000000000000101, 10**400):
        with pytest.raises(ValueError):
            canonicalize({"value": value})
