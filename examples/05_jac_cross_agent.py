"""
Example 5: JAC-01 cross-agent judgment chain.
"""

from jep.extensions.jac import build_jac_event
from jep.core.chain import AuditChain


def main():
    chain = AuditChain(issuer="did:example:agent-a")
    
    j1 = build_jac_event(
        verb="J",
        who="did:example:agent-a",
        content={"action": "diagnose_patient", "patient_id": "P001"},
        task_based_on=None,
    )
    chain.append(j1)
    parent_task = j1.get("what")
    
    chain2 = AuditChain(issuer="did:example:agent-b")
    j2 = build_jac_event(
        verb="J",
        who="did:example:agent-b",
        content={"action": "analyze_radiology"},
        task_based_on=parent_task,
        extensions={
            "https://jac.org/assign": {
                "assigner": "did:example:agent-a",
                "assignee": "did:example:agent-b",
                "capability_required": "diagnosis.radiology",
            }
        },
    )
    chain2.append(j2)
    
    print("Agent A head:", j1["nonce"][:8])
    print("Agent B continuation:", j2["nonce"][:8])
    print("task_based_on:", j2["task_based_on"][:40])
    
    chain.save("05_agent_a.jsonl")
    chain2.save("05_agent_b.jsonl")


if __name__ == "__main__":
    main()
