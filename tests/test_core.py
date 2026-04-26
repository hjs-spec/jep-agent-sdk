"""Test core event construction and hashing."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep.core.chain import AuditChain
from jep.core.event import build_event, canonicalize, event_hash


def test_build_event_structure():
    ev = build_event("J", "did:example:agent", what="sha256:abc123")
    assert ev["jep"] == "1"
    assert ev["verb"] == "J"
    assert ev["who"] == "did:example:agent"
    assert isinstance(ev["when"], int)
    assert isinstance(ev["nonce"], str)
    assert ev["sig"] == ""


def test_canonicalize_excludes_sig():
    ev = build_event("J", "agent", what="sha256:test")
    ev["sig"] = "fakesig"
    canon = canonicalize(ev)
    assert b"fakesig" not in canon


def test_event_hash_consistency():
    ev = build_event("J", "agent", what="sha256:test", nonce="fixed-nonce", when=1000)
    h1 = event_hash(ev)
    h2 = event_hash(ev)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_chain_linkage():
    key = Ed25519PrivateKey.generate()
    chain = AuditChain(issuer="agent", private_key=key)
    chain.append(build_event("J", "agent"))
    e2 = chain.append(build_event("V", "agent"))
    assert e2["ref"] is not None
    assert e2["ref"].startswith("sha256:")
    assert chain.verify_chain()
