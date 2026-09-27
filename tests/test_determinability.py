"""Test determinability checker and guard."""

import pytest

from jep_agent.determinability import (
    DeterminabilityGuard,
    check_determinability,
)


def test_determinable():
    configs = [
        {"obs": "A", "target": 1},
        {"obs": "B", "target": 0},
    ]
    result = check_determinability(configs, lambda c: c["obs"], lambda c: c["target"])
    assert result[0] == "Determined"


def test_not_determinable():
    configs = [
        {"obs": "SAME", "target": 1},
        {"obs": "SAME", "target": 0},
    ]
    result = check_determinability(configs, lambda c: c["obs"], lambda c: c["target"])
    assert result[0] == "NotDetermined"


def test_guard_blocks():
    guard = DeterminabilityGuard(
        evidence_fn=lambda ctx: len(ctx.get("tools_used", [])),
        target_fn=lambda ctx: ctx.get("ok", "ok"),
        knowledge_base=[
            {"tools_used": ["a", "b"], "ok": "ok"},
            {"tools_used": ["a"], "ok": 0},
        ],
        on_insufficient="raise",
    )

    @guard.require_determinable
    def good(tools_used):
        return "ok"

    with pytest.raises(RuntimeError):
        good(["a"])

    assert good(["a", "b"]) == "ok"


@pytest.mark.parametrize("mode", ["raies", "", None])
def test_guard_rejects_unknown_mode_before_execution(mode):
    with pytest.raises(ValueError, match="on_insufficient"):
        DeterminabilityGuard(lambda c: 0, lambda c: c, on_insufficient=mode)


@pytest.mark.parametrize("fallback", [None, False, "handler"])
def test_guard_rejects_missing_or_noncallable_fallback(fallback):
    with pytest.raises(ValueError, match="callable fallback"):
        DeterminabilityGuard(
            lambda c: 0, lambda c: c, on_insufficient="fallback", fallback=fallback
        )


class FalseyFallback:
    def __bool__(self):
        return False

    def __call__(self, value):
        return ("review", value)


@pytest.mark.parametrize("fallback", [lambda value: ("review", value), FalseyFallback()])
def test_guard_fallback_handles_conflict_without_running_guarded_function(fallback):
    calls = []
    guard = DeterminabilityGuard(
        lambda c: 0,
        lambda c: c.get("outcome", "new"),
        knowledge_base=[{"outcome": "old"}],
        on_insufficient="fallback",
        fallback=fallback,
    )

    @guard.require_determinable
    def execute(value):
        calls.append(value)

    assert execute("request") == ("review", "request")
    assert calls == []


def test_guard_warn_remains_an_explicit_allow_mode(capsys):
    guard = DeterminabilityGuard(
        lambda c: 0,
        lambda c: c.get("outcome", "new"),
        knowledge_base=[{"outcome": "old"}],
        on_insufficient="warn",
    )
    calls = []

    @guard.require_determinable
    def execute():
        calls.append("executed")

    execute()
    assert calls == ["executed"]
    assert "WARNING" in capsys.readouterr().out
