"""Test JEP verification pipeline."""

import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep.core.event import sign_event
from jep.core.verifier import JEPVerifier


def test_valid_event():
    v = JEPVerifier()
    ev = {
        "jep": "1",
        "verb": "J",
        "who": "agent",
        "when": int(time.time()),
        "what": "sha256:test",
        "nonce": "test-nonce-1",
        "sig": "",
    }
    key = Ed25519PrivateKey.generate()
    sign_event(ev, key)
    assert v.verify(ev, key.public_key()) == "VALID"


def test_replay_detection():
    v = JEPVerifier()
    ev = {
        "jep": "1",
        "verb": "J",
        "who": "agent",
        "when": int(time.time()),
        "what": "sha256:test",
        "nonce": "test-nonce-2",
        "sig": "",
    }
    key = Ed25519PrivateKey.generate()
    sign_event(ev, key)
    assert v.verify(ev, key.public_key()) == "VALID"
    assert "replay" in v.verify(ev, key.public_key()).lower()


def test_bad_verb():
    v = JEPVerifier()
    ev = {
        "jep": "1",
        "verb": "X",
        "who": "agent",
        "when": int(time.time()),
        "what": "sha256:test",
        "nonce": "test-nonce-3",
        "sig": "",
    }
    assert "bad verb" in v.verify(ev).lower()
