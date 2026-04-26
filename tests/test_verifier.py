"""Test JEP verification pipeline."""

from jep.core.event import build_event
from jep.core.verifier import JEPVerifier


def test_valid_event():
    v = JEPVerifier()
    ev = build_event("J", "agent", what="sha256:test")
    assert v.verify(ev) == "VALID"


def test_replay_detection():
    v = JEPVerifier()
    ev = build_event("J", "agent", what="sha256:test")
    assert v.verify(ev) == "VALID"
    assert "replay" in v.verify(ev).lower()


def test_bad_verb():
    v = JEPVerifier()
    ev = {
        "jep": "1",
        "verb": "X",
        "who": "agent",
        "when": 1000,
        "what": "sha256:test",
        "nonce": "test-nonce",
        "sig": "",
    }
    assert "bad verb" in v.verify(ev).lower()
