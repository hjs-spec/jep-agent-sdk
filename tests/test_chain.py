"""Test chain linkage and persistence."""

from jep.core.chain import AuditChain
from jep.core.event import build_event


def test_audit_chain_save_load(tmp_path):
    path = tmp_path / "chain.jsonl"
    chain = AuditChain(issuer="agent", storage_path=str(path))

    chain.append(build_event("J", "agent", content={"task": "t1"}))
    chain.append(build_event("V", "agent", content={"result": "ok"}))

    chain2 = AuditChain(issuer="agent", storage_path=str(path))
    chain2.load()
    assert len(chain2.events) == 2
    assert chain2.verify_chain()


def test_cross_chain_ref():
    chain1 = AuditChain(issuer="a")
    e1 = chain1.append(build_event("J", "a", content={"x": 1}))

    chain2 = AuditChain(issuer="b")
    e2 = build_event("J", "b", content={"x": 2}, ref=e1.get("what"))
    chain2.append(e2)

    assert e2["ref"] == e1.get("what") or e2["ref"].startswith("sha256:")
