"""Finite-model research guard; not JEP/TSTO verification or execution authority."""

from jep_agent.determinability import DeterminabilityGuard

# Use the actual argument context. These are synthetic observations/targets,
# not claims that a tool list establishes sufficient real-world evidence.
guard = DeterminabilityGuard(
    evidence_fn=lambda ctx: ctx["args"][0],
    target_fn=lambda ctx: ctx["args"][1],
    knowledge_base=[{"args": ("observation-A", 1)}],
    on_insufficient="raise",
)


@guard.require_determinable
def compare_modeled_outcome(observation, outcome):
    return outcome


if __name__ == "__main__":
    assert compare_modeled_outcome("observation-A", 1) == 1
    try:
        compare_modeled_outcome("observation-A", 0)
    except RuntimeError:
        print("Conflicting modeled outcome blocked; external truth remains unchecked.")
    else:
        raise AssertionError("Expected the modeled conflict to be blocked")
