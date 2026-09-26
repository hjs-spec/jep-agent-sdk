"""
Example 5: Core 0.7 events with a local task-link companion.
"""

from jep_agent.extensions.jac import build_jac_event
from jep_agent.core.chain import AuditChain
from jep_agent.core.event import event_identity_ref


def main():
    chain = AuditChain(issuer="did:example:agent-a")

    j1 = build_jac_event(
        verb="J",
        who="did:example:agent-a",
        content={"action": "diagnose_patient", "patient_id": "P001"},
        task_based_on=None,
    )
    chain.append(j1)
    parent_task = event_identity_ref(j1)

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

    print("Agent A head:", j1["id"][:8])
    print("Agent B continuation:", j2["id"][:8])
    print("task_based_on:", j2["ext"]["jep-agent.jac"]["task_based_on"])

    chain.save("05_agent_a.jsonl")
    chain2.save("05_agent_b.jsonl")


if __name__ == "__main__":
    main()
