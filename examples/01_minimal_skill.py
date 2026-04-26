"""
Example 1: Minimal JEP skill with bare primitives.
"""

from jep import judge, verify, AuditChain


def main():
    chain = AuditChain(issuer="did:example:agent-demo")
    
    j = judge(who="did:example:agent-demo", content={"task": "check_door", "door_id": "A1"})
    chain.append(j)
    print(f"[J] Started: {j['nonce'][:8]}...")
    
    result = {"status": "closed", "confidence": 0.95}
    
    v = verify(who="did:example:agent-demo", content=result)
    chain.append(v)
    print(f"[V] Confirmed: {v['nonce'][:8]}...")
    
    assert chain.verify_chain(), "Chain broken!"
    print("✓ Chain integrity verified")
    
    chain.save("01_output.jsonl")
    print("Saved to 01_output.jsonl")


if __name__ == "__main__":
    main()
