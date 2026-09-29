"""Regression tests for SDK safety boundaries."""

import asyncio
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent import RecordingError
from jep_agent.core.chain import AuditChain
from jep_agent.core.event import build_event, sign_event, verify_payload_integrity
from jep_agent.primitives import judge
from jep_agent.recorder import record


class CollectingChain:
    def __init__(self, issuer="agent"):
        self.issuer = issuer
        self.events = []

    def append(self, event):
        self.events.append(event)
        return event


class FailOnSecondAppend:
    def __init__(self, issuer="agent"):
        self.issuer = issuer
        self.calls = 0

    def append(self, event):
        self.calls += 1
        if self.calls == 2:
            raise OSError("simulated recording failure")
        return event


def test_verify_payload_integrity_requires_trusted_key():
    key = Ed25519PrivateKey.generate()
    event = sign_event(build_event("J", "agent", {"claim": "original"}), key)

    assert verify_payload_integrity(event, key.public_key())
    assert not verify_payload_integrity(event)

    tampered = dict(event)
    tampered["what"] = {"claim": "tampered"}
    assert not verify_payload_integrity(tampered, key.public_key())


def test_record_omits_values_by_default_and_allows_explicit_capture():
    secret = "synthetic-secret-token"

    safe_chain = CollectingChain()

    @record(issuer=safe_chain.issuer, chain=safe_chain, auto_verify=False)
    def safe_echo(value):
        return value

    assert safe_echo(secret) == secret
    assert secret not in json.dumps(safe_chain.events)

    capture_chain = CollectingChain()

    @record(
        issuer=capture_chain.issuer,
        chain=capture_chain,
        auto_verify=False,
        capture_values=True,
    )
    def captured_echo(value):
        return value

    assert captured_echo(secret) == secret
    assert secret in json.dumps(capture_chain.events)


def test_record_rejects_generator_and_async_generator_functions():
    def stream():
        yield 1

    async def async_stream():
        yield 1

    with pytest.raises(TypeError, match="generator"):
        record(stream)
    with pytest.raises(TypeError, match="generator"):
        record(async_stream)


def test_post_execution_recording_failure_is_typed():
    chain = FailOnSecondAppend()
    effects = []

    @record(issuer=chain.issuer, chain=chain)
    def task():
        effects.append("executed")
        return 7

    with pytest.raises(RecordingError) as excinfo:
        task()

    assert effects == ["executed"]
    assert excinfo.value.stage == "after_execution"
    assert excinfo.value.call_executed is True
    assert isinstance(excinfo.value.__cause__, OSError)


def test_business_exception_remains_primary_when_error_recording_fails():
    chain = FailOnSecondAppend()

    @record(issuer=chain.issuer, chain=chain)
    def task():
        raise ValueError("business failure")

    with pytest.raises(ValueError) as excinfo:
        task()

    assert str(excinfo.value) == "business failure"
    assert isinstance(excinfo.value.__cause__, RecordingError)
    assert excinfo.value.__cause__.stage == "after_error"
    assert excinfo.value.__cause__.call_executed is True


@pytest.mark.asyncio
async def test_cancellation_remains_primary_when_error_recording_fails():
    chain = FailOnSecondAppend()
    entered = asyncio.Event()

    @record(issuer=chain.issuer, chain=chain)
    async def task():
        entered.set()
        await asyncio.Event().wait()

    pending = asyncio.create_task(task())
    await entered.wait()
    pending.cancel()

    with pytest.raises(asyncio.CancelledError) as excinfo:
        await pending

    assert isinstance(excinfo.value.__cause__, RecordingError)
    assert excinfo.value.__cause__.stage == "after_error"
    assert excinfo.value.__cause__.call_executed is True


def test_existing_storage_requires_load_before_append(tmp_path):
    path = tmp_path / "chain.jsonl"
    original = json.dumps(judge("agent", content={"claim": "existing"})) + "\n"
    path.write_text(original, encoding="utf-8")

    chain = AuditChain("agent", storage_path=str(path))
    with pytest.raises(FileExistsError, match="Load it before continuing"):
        chain.append(judge("agent", content={"claim": "new"}))

    assert chain.events == []
    assert path.read_text(encoding="utf-8") == original


def test_loaded_storage_can_continue_without_discarding_history(tmp_path):
    path = tmp_path / "chain.jsonl"
    original = json.dumps(judge("agent", content={"claim": "existing"})) + "\n"
    path.write_text(original, encoding="utf-8")

    chain = AuditChain("agent", storage_path=str(path))
    chain.load()
    chain.append(judge("agent", content={"claim": "new"}))

    reloaded = AuditChain("agent", storage_path=str(path))
    reloaded.load()
    assert len(reloaded.events) == 2
    assert reloaded.events[0]["what"] == {"claim": "existing"}
    assert reloaded.events[1]["what"] == {"claim": "new"}


def test_atomic_persistence_failure_keeps_disk_and_memory_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "chain.jsonl"
    original = json.dumps(judge("agent", content={"claim": "existing"})) + "\n"
    path.write_text(original, encoding="utf-8")

    chain = AuditChain("agent", storage_path=str(path))
    chain.load()

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("jep_agent.core.chain.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        chain.append(judge("agent", content={"claim": "new"}))

    assert len(chain.events) == 1
    assert path.read_text(encoding="utf-8") == original
    assert sorted(item.name for item in tmp_path.iterdir()) == ["chain.jsonl"]


def test_save_requires_explicit_overwrite_for_unmanaged_existing_file(tmp_path):
    path = tmp_path / "export.jsonl"
    path.write_text("sentinel\n", encoding="utf-8")

    chain = AuditChain("agent")
    chain.events = [judge("agent", content={"claim": "replacement"})]

    with pytest.raises(FileExistsError):
        chain.save(str(path))
    assert path.read_text(encoding="utf-8") == "sentinel\n"

    chain.save(str(path), overwrite=True)
    assert "replacement" in path.read_text(encoding="utf-8")
