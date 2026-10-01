"""Cross-repository vectors and regression cases for the 0.7 boundary."""

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from jep_agent.core.event import (
    _base64url_encode,
    build_event,
    canonicalize,
    event_hash,
    parse_json,
    sign_event,
    verify_event_signature,
)
from jep_agent.core.verifier import JEPVerifier

FIXTURES = Path(__file__).parent / "fixtures/core-0.7"


@pytest.mark.parametrize("verb", ["J", "D", "T", "V"])
def test_official_core_vectors(verb):
    event = json.loads((FIXTURES / f"{verb}-basic.json").read_text())
    keys = json.loads((FIXTURES / "keys.json").read_text())
    header = json.loads(base64.urlsafe_b64decode(event["sig"].split(".")[0] + "=="))
    jwk = keys[header["kid"]]
    key = Ed25519PublicKey.from_public_bytes(base64.urlsafe_b64decode(jwk["x"] + "=="))
    assert JEPVerifier().verify_result(event, key)["status"] == "valid"


def test_producer_accepted_by_independent_core_validator():
    core = pytest.importorskip("jep_conformance.jep_validate_07")
    key = Ed25519PrivateKey.generate()
    who = "agent:interop"
    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _base64url_encode(key.public_key().public_bytes_raw()),
    }
    ref = {"type": "jep:event", "value": {"who": who, "id": "root"}}
    for verb, body, options in [
        ("J", {"claim": "x"}, {}),
        ("D", {"delegatee": "agent:b", "scope": {}}, {}),
        ("T", {"termination_scope": "future_reliance"}, {"ref": ref}),
        ("V", {"verification_scope": ["syntax"], "result": {"status": "pass"}}, {"ref": ref}),
        ("V", {"verification_scope": "cryptographic", "result": "pass"}, {"ref": ref}),
    ]:
        event = sign_event(build_event(verb, who, body, **options), key)
        result = core.validate_event(event, keys={f"{who}#key-1": jwk})
        assert result["status"] == "valid", result
        assert core.event_hash(event) == event_hash(event)


def test_published_string_scope_vector_keeps_signature_and_event_hash():
    fixtures = Path(__file__).parent / "fixtures/core-v07"
    raw = (fixtures / "V-string-scope.json").read_text()
    event = parse_json(raw)
    keys = json.loads((fixtures / "keys.json").read_text())
    key = Ed25519PublicKey.from_public_bytes(
        base64.urlsafe_b64decode(keys["byoi-key-1"]["x"] + "==")
    )
    result = JEPVerifier().verify_result(event, key)
    assert result["status"] == "valid", result
    assert event == json.loads(raw)
    assert event_hash(event) == (
        "sha256:95d6d17f3fb530c282251eb8c0b9d3885dbc25f6ae01a782390bc7ad98e30765"
    )
    event["what"]["verification_scope"] = ["cryptographic"]
    assert not verify_event_signature(event, key)


@pytest.mark.parametrize("scope", ["", [], [""], ["syntax", "syntax"], [1], {}, None])
def test_invalid_v_scopes_still_rejected(scope):
    with pytest.raises(ValueError, match="verification_scope"):
        build_event(
            "V",
            "actor",
            {"verification_scope": scope, "result": "pass"},
            ref={"type": "jep:event", "value": {"who": "actor", "id": "target"}},
        )


@pytest.mark.parametrize(
    "patch",
    [
        {"ext_crit": [{}]},
        {"ext_crit": None},
        {"ext": {"x": []}},
        {"aud": None},
        {"what": {}},
        {"what": "sha256:abc"},
        {"when": 2**53},
        {"verb": []},
        {"ref": {"type": "jep:event", "value": {"id": "x"}}},
        {"what": {"bad": float("nan")}},
        {"what": {"bad": "\ud800"}},
        {"unexpected": True},
    ],
)
def test_malformed_event_returns_diagnostic(patch):
    event = {**build_event("J", "actor", {"claim": "x"}), **patch}
    result = JEPVerifier().verify_result(event, mode="acceptance")
    assert result["status"] == "invalid"
    assert result["acceptance"] == {"outcome": "rejected", "effect_applied": False}


@pytest.mark.parametrize("value", [None, [], "event", 42])
def test_non_object_returns_diagnostic(value):
    assert JEPVerifier().verify_result(value)["status"] == "invalid"


def test_unknown_critical_extension_cannot_consume_acceptance():
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "actor", {"claim": "x"})
    critical = sign_event(
        {**event, "ext": {"example:required": {}}, "ext_crit": ["example:required"]}, key
    )
    verifier = JEPVerifier()
    result = verifier.verify_result(critical, key.public_key(), mode="acceptance")
    assert result["errors"][0]["code"] == "ERR_UNKNOWN_CRITICAL_EXTENSION"
    assert not result["acceptance"]["effect_applied"]
    assert (
        verifier.verify_result(sign_event(event, key), key.public_key(), mode="acceptance")[
            "acceptance"
        ]["outcome"]
        == "accepted"
    )


def test_resigning_is_retry_but_unsigned_change_is_conflict():
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "actor", {"claim": "x"})
    first = sign_event(event, key, kid="key-1")
    second = sign_event(event, key, kid="key-2")
    verifier = JEPVerifier()
    assert event_hash(first) != event_hash(second)
    assert verifier.verify_result(first, key.public_key(), mode="acceptance")["acceptance"][
        "effect_applied"
    ]
    assert (
        verifier.verify_result(second, key.public_key(), mode="acceptance")["acceptance"]["outcome"]
        == "already_accepted"
    )
    conflict = sign_event({**event, "what": {"claim": "other"}}, key)
    assert (
        verifier.verify_result(conflict, key.public_key(), mode="acceptance")["errors"][0]["code"]
        == "ERR_EVENT_ID_CONFLICT"
    )


def test_concurrent_acceptance_applies_once():
    key = Ed25519PrivateKey.generate()
    event = sign_event(build_event("J", "actor", {"claim": "x"}), key)
    verifier = JEPVerifier()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _: verifier.verify_result(event, key.public_key(), mode="acceptance"),
                range(32),
            )
        )
    assert sum(r["acceptance"]["effect_applied"] for r in results) == 1
    assert all(r["status"] == "valid" for r in results)


def test_legacy_algorithm_requires_explicit_profile():
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "actor", {"claim": "x"})
    protected = _base64url_encode(b'{"alg":"EdDSA"}')
    signature = key.sign((protected + "." + _base64url_encode(canonicalize(event))).encode())
    event["sig"] = protected + ".." + _base64url_encode(signature)
    assert not verify_event_signature(event, key.public_key())
    assert verify_event_signature(event, key.public_key(), signature_profile="legacy-eddsa")


@pytest.mark.parametrize(
    "header",
    [
        b'{"alg":"Ed25519","kid":"key","b64":false}',
        b'{"alg":"Ed25519","alg":"Ed25519","kid":"key"}',
        b'{"alg":"Ed25519","kid":"key","crit":["unknown"]}',
    ],
)
def test_unsupported_signed_jose_headers_rejected(header):
    key = Ed25519PrivateKey.generate()
    event = build_event("J", "actor", {"claim": "x"})
    protected = _base64url_encode(header)
    event["sig"] = (
        protected
        + ".."
        + _base64url_encode(
            key.sign((protected + "." + _base64url_encode(canonicalize(event))).encode())
        )
    )
    assert not verify_event_signature(event, key.public_key())


def test_padded_signature_and_duplicate_json_rejected():
    key = Ed25519PrivateKey.generate()
    event = sign_event(build_event("J", "actor", {"claim": "x"}), key)
    padded = deepcopy(event)
    padded["sig"] += "=="
    assert not verify_event_signature(padded, key.public_key())
    with pytest.raises(ValueError, match="Duplicate"):
        parse_json('{"what":{"x":1,"x":2}}')


def test_task_link_companion_is_separate_and_requires_evidence():
    from jep_agent.extensions.jac import JAC_EXTENSION, build_jac_event, verify_jac_core

    ref = {"type": "jep:event", "value": {"who": "agent:a", "id": "task"}}
    event = build_jac_event("J", "agent:b", {"claim": "continue"}, task_based_on=ref)
    assert "task_based_on" not in event
    assert event["ext"][JAC_EXTENSION]["task_based_on"] == ref
    key = Ed25519PrivateKey.generate()
    event = sign_event(event, key)
    assert verify_jac_core(event).startswith("UNVERIFIED")

    def signature(ev):
        return verify_event_signature(ev, key.public_key())

    assert verify_jac_core(event, signature).startswith("UNVERIFIED")
    assert (
        verify_jac_core(event, signature, task_parent_lookup=lambda value: value == ref) == "VALID"
    )
