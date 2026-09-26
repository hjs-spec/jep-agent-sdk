"""Test JEP Core 0.7 event construction and companion chain linkage."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.chain import CHAIN_EXTENSION, AuditChain
from jep_agent.core.event import build_event, canonicalize, event_hash


def test_build_event_structure():
    ev=build_event("J","did:example:agent",{"claim":"example"})
    assert ev["jep"]=="1"
    assert ev["verb"]=="J"
    assert ev["who"]=="did:example:agent"
    assert isinstance(ev["when"],int)
    assert isinstance(ev["id"],str)
    assert "nonce" not in ev
    assert ev["sig"]==""


def test_canonicalize_excludes_sig():
    ev=build_event("J","agent",{"claim":"example"})
    ev["sig"]="fakesig"
    assert b"fakesig" not in canonicalize(ev)


def test_event_hash_identifies_full_signed_artifact():
    ev=build_event("J","agent",{"claim":"example"},event_id="urn:test:event:1",when=1000)
    h1=event_hash(ev)
    ev2=dict(ev)
    ev2["sig"]="different"
    assert h1!=event_hash(ev2)


def test_chain_linkage_uses_companion_extension_not_core_ref():
    key=Ed25519PrivateKey.generate()
    chain=AuditChain(issuer="agent",private_key=key)
    chain.append(build_event("J","agent",{"claim":"first"}))
    e2=chain.append(build_event("J","agent",{"claim":"second"}))
    assert "ref" not in e2
    assert CHAIN_EXTENSION in e2["ext"]
    assert chain.verify_chain()
