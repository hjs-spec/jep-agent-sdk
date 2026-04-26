import pytest
from jep.core.verifier import JEPVerifier
from jep.core.event import build_event


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
    ev = build_event("X", "agent")
    assert "bad verb" in v.verify(ev).lower()
