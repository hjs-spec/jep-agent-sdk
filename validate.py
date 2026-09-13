#!/usr/bin/env python3
"""Executable smoke check of the legacy-04 signed archive API."""
from pathlib import Path
from tempfile import TemporaryDirectory
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jep_agent.core.chain import AuditChain
from jep_agent.core.event import event_hash, verify_event_signature
from jep_agent.core.verifier import JEPVerifier
from jep_agent.primitives import judge, verify


def main():
    key = Ed25519PrivateKey.generate()
    with TemporaryDirectory() as directory:
        path = str(Path(directory) / "events.jsonl")
        chain = AuditChain(issuer="agent:A", private_key=key, storage_path=path)
        first = chain.append(judge("agent:A", content={"task": "example"}))
        last = chain.append(verify("agent:A", content={"result": "ok"}))
        assert last["ref"] == event_hash(first)
        loaded = AuditChain(issuer="agent:A", storage_path=path)
        loaded.load()
        assert loaded.verify_chain(public_key=key.public_key())
        verifier = JEPVerifier()
        for event in loaded.export():
            assert verifier.verify(event, key.public_key()) == "VALID"
        loaded.events[0]["what"] = "sha256:" + "0" * 64
        assert not loaded.verify_chain(public_key=key.public_key())
        assert not verify_event_signature(loaded.events[0], key.public_key())
    print("Legacy-04 signing, persistence, chain verification and tamper rejection passed.")


if __name__ == "__main__":
    main()
