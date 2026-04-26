"""Test JEP verification pipeline."""

import time

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
    assert v.verify(ev) == "VALID"


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
    assert v.verify(ev) == "VALID"
    assert "replay" in v.verify(ev).lower()


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
