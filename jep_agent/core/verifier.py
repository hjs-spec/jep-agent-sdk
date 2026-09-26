"""JEP Core 0.7 verification and idempotent acceptance helpers."""

from __future__ import annotations

import hashlib
import time
from threading import Lock
from typing import Any, Dict, Mapping, Optional

from jep_agent.core.event import _validate_shape, canonicalize, event_hash, verify_event_signature

CHECKS = (
    "syntax",
    "cryptographic",
    "actor_binding",
    "freshness",
    "audience",
    "event_identity",
    "reference_integrity",
    "extension_processing",
    "chain_integrity",
    "policy",
)


def _base_checks() -> Dict[str, str]:
    return {name: "not_checked" for name in CHECKS}


def _diag(code: str, message: str, check: str) -> Dict[str, Any]:
    return {"code": code, "message": message, "check": check}


class JEPVerifier:
    """Small in-memory Core 0.7 verifier.

    The acceptance store is reference-only. Production deployments need a
    durable shared store and atomic compare-and-set or unique insertion.
    """

    def __init__(self):
        self._accepted: Dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def verify_result(
        self,
        ev: Mapping[str, Any],
        public_key=None,
        *,
        mode: str = "archival",
        expected_aud: Optional[str] = None,
        max_age_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        checks = _base_checks()
        errors = []

        def fail(
            code: str,
            message: str,
            check: str,
            *,
            indeterminate: bool = False,
        ) -> Dict[str, Any]:
            checks[check] = "indeterminate" if indeterminate else "fail"
            errors.append(_diag(code, message, check))
            acceptance = None
            if mode == "acceptance":
                acceptance = {
                    "outcome": "indeterminate" if indeterminate else "rejected",
                    "effect_applied": False,
                }
            result = {
                "status": "indeterminate" if indeterminate else "invalid",
                "mode": mode,
                "profile": "jep-core-0.7",
                "event_identity": {
                    "who": ev.get("who") if isinstance(ev, dict) else None,
                    "id": ev.get("id") if isinstance(ev, dict) else None,
                },
                "event_hash": None,
                "checks": checks,
                "warnings": [],
                "errors": errors,
            }
            if acceptance is not None:
                result["acceptance"] = acceptance
            return result

        if mode not in {"archival", "acceptance"}:
            return fail(
                "ERR_DOMAIN_REQUIREMENT_UNSATISFIED",
                "reference verifier supports archival or acceptance mode",
                "policy",
            )

        if not isinstance(ev, dict):
            return fail("ERR_INVALID_FIELD_TYPE", "event must be an object", "syntax")
        for field in ("jep", "id", "verb", "who", "when", "what", "sig"):
            if field not in ev:
                return fail(
                    "ERR_MISSING_REQUIRED_FIELD", f"missing required field: {field}", "syntax"
                )
        if ev.get("jep") != "1":
            return fail("ERR_UNSUPPORTED_JEP_VERSION", "jep must be '1'", "syntax")
        if not isinstance(ev.get("verb"), str) or ev["verb"] not in {"J", "D", "T", "V"}:
            return fail("ERR_UNKNOWN_VERB", "verb must be J, D, T, or V", "syntax")
        try:
            _validate_shape(ev)
        except (TypeError, ValueError) as exc:
            return fail("ERR_INVALID_FIELD_TYPE", str(exc), "syntax")
        checks["syntax"] = "pass"

        if public_key is None:
            checks["cryptographic"] = "indeterminate"
            result = {
                "status": "indeterminate",
                "mode": mode,
                "profile": "jep-core-0.7",
                "event_identity": {"who": ev["who"], "id": ev["id"]},
                "event_hash": None,
                "checks": checks,
                "warnings": [],
                "errors": [
                    _diag(
                        "ERR_KEY_UNRESOLVED",
                        "trusted public key required",
                        "cryptographic",
                    )
                ],
            }
            if mode == "acceptance":
                result["acceptance"] = {
                    "outcome": "indeterminate",
                    "effect_applied": False,
                }
            return result

        if not verify_event_signature(ev, public_key):
            return fail(
                "ERR_SIGNATURE_INVALID",
                "signature verification failed",
                "cryptographic",
            )

        checks["cryptographic"] = "pass"
        checks["event_identity"] = "pass"
        if ev.get("ext_crit"):
            return fail(
                "ERR_UNKNOWN_CRITICAL_EXTENSION",
                "this verifier implements no critical extension handlers",
                "extension_processing",
            )
        checks["extension_processing"] = "pass"
        if "ref" not in ev:
            checks["reference_integrity"] = "not_applicable"

        if expected_aud is not None:
            if ev.get("aud") != expected_aud:
                return fail(
                    "ERR_DOMAIN_REQUIREMENT_UNSATISFIED",
                    "audience mismatch",
                    "audience",
                )
            checks["audience"] = "pass"

        if max_age_seconds is not None:
            now = int(time.time())
            if ev["when"] < now - max_age_seconds or ev["when"] > now + 300:
                return fail(
                    "ERR_TIMESTAMP_OUT_OF_WINDOW",
                    "declared event time is outside requested freshness window",
                    "freshness",
                )
            checks["freshness"] = "pass"

        result = {
            "status": "valid",
            "mode": mode,
            "profile": "jep-core-0.7",
            "event_identity": {"who": ev["who"], "id": ev["id"]},
            "event_hash": event_hash(ev),
            "checks": checks,
            "warnings": [],
            "errors": [],
        }
        if mode == "archival":
            return result

        identity = (ev["who"], ev["id"])
        payload_digest = hashlib.sha256(canonicalize(ev)).hexdigest()
        with self._lock:
            previous = self._accepted.get(identity)
            if previous is None:
                self._accepted[identity] = payload_digest
                outcome = "accepted"
                effect_applied = True
            elif previous == payload_digest:
                outcome = "already_accepted"
                effect_applied = False
            else:
                return fail(
                    "ERR_EVENT_ID_CONFLICT",
                    "Event Identity is already bound to different unsigned content",
                    "event_identity",
                )

        result["acceptance"] = {
            "outcome": outcome,
            "effect_applied": effect_applied,
        }
        return result

    def verify(
        self,
        ev: Mapping[str, Any],
        public_key=None,
        expected_aud: Optional[str] = None,
    ) -> str:
        """Compatibility wrapper over archival validation."""
        result = self.verify_result(
            ev,
            public_key,
            mode="archival",
            expected_aud=expected_aud,
        )
        if result["status"] == "valid":
            return "VALID"
        if result["status"] == "indeterminate":
            return "UNVERIFIED"
        return "INVALID"

    def reset_acceptance_state(self) -> None:
        with self._lock:
            self._accepted.clear()

    def reset_nonce_cache(self) -> None:
        """Deprecated compatibility alias. Core 0.7 has no nonce cache."""
        self.reset_acceptance_state()
