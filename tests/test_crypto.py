import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jep.core.event import sign_event, verify_event_signature, verify_payload_integrity, build_event


def generate_test_key():
    return Ed25519PrivateKey.generate()


def test_sign_and_verify():
    key = generate_test_key()
    ev = build_event("J", "agent", what="sha256:test")
    signed = sign_event(ev, key)
    assert signed["sig"] != ""
    assert verify_event_signature(signed, key.public_key())


def test_tamper_detection():
    key = generate_test_key()
    ev = build_event("J", "agent", what="sha256:test")
    signed = sign_event(ev, key)
    
    signed["what"] = "sha256:TAMPERED"
    assert not verify_payload_integrity(signed)
