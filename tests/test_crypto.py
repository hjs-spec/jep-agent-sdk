"""Test Core 0.7 detached signing and tamper detection."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.event import (\n    build_event,\n    sign_event,\n    verify_event_signature,\n    verify_payload_integrity,\n)


def test_sign_and_verify_detached_jws():
    key=Ed25519PrivateKey.generate()
    signed=sign_event(build_event("J","agent",{"claim":"x"}),key)
    assert signed["sig"].split(".")[1]==""
    assert verify_event_signature(signed,key.public_key())


def test_tamper_detection():
    key=Ed25519PrivateKey.generate()
    signed=sign_event(build_event("J","agent",{"claim":"x"}),key)
    signed["what"]={"claim":"tampered"}
    assert not verify_payload_integrity(signed,key.public_key())
