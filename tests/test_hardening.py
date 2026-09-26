import asyncio

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.chain import AuditChain
from jep_agent.core.event import build_event, sign_event, verify_event_signature
from jep_agent.core.verifier import JEPVerifier
from jep_agent.recorder import record


def test_first_event_tamper_and_unsigned_chain_are_rejected():
    key = Ed25519PrivateKey.generate()
    chain = AuditChain("agent", private_key=key)
    original = chain.append(build_event("J", "agent", {"claim": "x"}))
    assert chain.verify_chain()
    chain.events[0]["what"] = {"claim": "tampered"}
    assert not verify_event_signature(chain.events[0], key.public_key())
    assert not chain.verify_chain()
    unsigned = AuditChain("agent")
    unsigned.append(build_event("J", "agent", {"claim": "x"}))
    assert not unsigned.verify_chain()
    assert JEPVerifier().verify(original) == "UNVERIFIED"


def test_failed_audience_check_does_not_consume_acceptance_state():
    key = Ed25519PrivateKey.generate()
    event = sign_event(build_event("J", "agent", {"claim": "x"}, aud="one"), key)
    verifier = JEPVerifier()
    failed = verifier.verify_result(event, key.public_key(), mode="acceptance", expected_aud="two")
    assert failed["status"] == "invalid"
    accepted = verifier.verify_result(
        event, key.public_key(), mode="acceptance", expected_aud="one"
    )
    assert accepted["acceptance"]["outcome"] == "accepted"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_async_lifecycle_waits_for_actual_completion(outcome):
    entered = asyncio.Event()
    release = asyncio.Event()

    @record
    async def task():
        entered.set()
        await release.wait()
        if outcome == "error":
            raise ValueError("failure")
        return 42

    pending = asyncio.create_task(task())
    await entered.wait()
    assert [e["verb"] for e in task._jep_chain.export()] == ["J"]
    if outcome == "cancel":
        pending.cancel()
    else:
        release.set()
    if outcome == "success":
        assert await pending == 42
    else:
        with pytest.raises(asyncio.CancelledError if outcome == "cancel" else ValueError):
            await pending
    assert [e["verb"] for e in task._jep_chain.export()] == [
        "J",
        "V" if outcome == "success" else "J",
    ]


def test_langchain_callback_error_is_result_not_termination():
    from jep_agent.adapters.langchain import _JEPCallbackHandler

    handler = _JEPCallbackHandler()
    handler.on_chain_start(inputs={"question": "test"})
    handler.on_chain_error(ValueError("failed"))
    assert handler._run_stack == []
    assert [e["verb"] for e in handler.chain.export()] == ["J", "V"]
