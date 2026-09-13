import sys
from types import SimpleNamespace

from jep.recorder import trace


def test_legacy_auto_retains_events_and_does_not_double_wrap(monkeypatch):
    class Completions:
        def create(self, **kwargs):
            return "answer"

    mock = SimpleNamespace(
        resources=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(Completions=Completions))
        )
    )
    monkeypatch.setitem(sys.modules, "openai", mock)
    from jep.adapters.openai_agents import auto_patch

    trace.enable(issuer="legacy:test")
    try:
        auto_patch()
        first = Completions.create
        auto_patch()
        assert Completions.create is first
        assert Completions().create(model="test") == "answer"
        assert len(trace.chain.events) == 2
    finally:
        trace.disable()
