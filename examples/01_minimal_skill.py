"""
Example 1: Minimal JEP skill with bare primitives.
"""

from jep_agent import judge, verify, AuditChain
from jep_agent.core.event import event_identity_ref
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main():
    chain = AuditChain(issuer="did:example:agent-demo", private_key=Ed25519PrivateKey.generate())

    j = judge(who="did:example:agent-demo", content={"task": "check_door", "door_id": "A1"})
    j = chain.append(j)
    print(f"[J] Started: {j['id'][:8]}...")

    result = {"status": "closed", "confidence": 0.95}

    v = verify(
        who="did:example:agent-demo",
        ref=event_identity_ref(j),
        verification_scope=["execution_result"],
        result=result,
    )
    chain.append(v)
    print(f"[V] Confirmed: {v['id'][:8]}...")

    assert chain.verify_chain(), "Chain broken!"
    print("✓ Chain integrity verified")

    chain.save("01_output.jsonl")
    print("Saved to 01_output.jsonl")


if __name__ == "__main__":
    main()
