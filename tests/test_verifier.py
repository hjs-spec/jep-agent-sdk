"""Test JEP Core 0.7 verification and acceptance."""

import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.event import build_event, sign_event
from jep_agent.core.verifier import JEPVerifier


def signed_event(key, event_id="urn:test:event:1", what=None):
    return sign_event(
        build_event(
            "J", "agent", what or {"claim": "example"}, event_id=event_id, when=int(time.time())
        ),
        key,
    )


def test_valid_archival_event():
    key = Ed25519PrivateKey.generate()
    result = JEPVerifier().verify_result(signed_event(key), key.public_key(), mode="archival")
    assert result["status"] == "valid"
    assert result["checks"]["cryptographic"] == "pass"


def test_safe_retry_is_already_accepted_not_invalid():
    key = Ed25519PrivateKey.generate()
    verifier = JEPVerifier()
    event = signed_event(key)
    first = verifier.verify_result(event, key.public_key(), mode="acceptance")
    second = verifier.verify_result(event, key.public_key(), mode="acceptance")
    assert first["acceptance"] == {"outcome": "accepted", "effect_applied": True}
    assert second["status"] == "valid"
    assert second["acceptance"] == {"outcome": "already_accepted", "effect_applied": False}


def test_event_identity_conflict():
    key = Ed25519PrivateKey.generate()
    verifier = JEPVerifier()
    first = signed_event(key, what={"claim": "one"})
    second = signed_event(key, what={"claim": "two"})
    assert verifier.verify_result(first, key.public_key(), mode="acceptance")["status"] == "valid"
    result = verifier.verify_result(second, key.public_key(), mode="acceptance")
    assert result["status"] == "invalid"
    assert result["errors"][0]["code"] == "ERR_EVENT_ID_CONFLICT"


def test_bad_verb():
    key = Ed25519PrivateKey.generate()
    ev = build_event("J", "agent", {"claim": "x"})
    ev["verb"] = "X"
    ev = sign_event({**ev, "verb": "J"}, key)
    ev["verb"] = "X"
    result = JEPVerifier().verify_result(ev, key.public_key())
    assert result["errors"][0]["code"] == "ERR_UNKNOWN_VERB"
