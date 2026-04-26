"""
Example 6: DeterminabilityGuard — runtime evidence gate.
"""

from jep.determinability import DeterminabilityGuard


def my_risky_agent(query: str, tools_used: list) -> str:
    return f"Decision for {query}"


guard = DeterminabilityGuard(
    evidence_fn=lambda ctx: len(ctx.get("tools_used", [])),
    target_fn=lambda ctx: ctx.get("outcome"),
    knowledge_base=[
        {"tools_used": ["search", "calc"], "outcome": 1},
        {"tools_used": ["search"], "outcome": 0},
        {"tools_used": ["search", "calc", "verify"], "outcome": 1},
    ],
    on_insufficient="raise",
)


@guard.require_determinable
def safe_agent(query: str, tools_used: list):
    return my_risky_agent(query, tools_used)


if __name__ == "__main__":
    try:
        result = safe_agent("complex query", tools_used=["search", "calc"])
        print(f"✓ Allowed: {result}")
    except RuntimeError as e:
        print(f"✗ Blocked: {e}")
    
    try:
        result = safe_agent("complex query", tools_used=["search"])
        print(f"✓ Allowed: {result}")
    except RuntimeError as e:
        print(f"✗ Blocked (expected): {e}")
