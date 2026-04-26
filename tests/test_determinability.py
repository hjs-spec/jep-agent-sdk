"""Test determinability checker and guard."""

import pytest

from jep.determinability import (
    DeterminabilityGuard,
    check_determinability,
)


def test_determinable():
    configs = [
        {"obs": "A", "target": 1},
        {"obs": "B", "target": 0},
    ]
    result = check_determinability(
        configs, lambda c: c["obs"], lambda c: c["target"]
    )
    assert result[0] == "Determined"


def test_not_determinable():
    configs = [
        {"obs": "SAME", "target": 1},
        {"obs": "SAME", "target": 0},
    ]
    result = check_determinability(
        configs, lambda c: c["obs"], lambda c: c["target"]
    )
    assert result[0] == "NotDetermined"


def test_guard_blocks():
    guard = DeterminabilityGuard(
        evidence_fn=lambda ctx: len(ctx.get("tools_used", [])),
        target_fn=lambda ctx: ctx.get("ok"),
        knowledge_base=[
            {"tools_used": ["a", "b"], "ok": 1},
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
