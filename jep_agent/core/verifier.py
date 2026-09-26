"""JEP Core 0.7 verification and idempotent acceptance helpers."""

from __future__ import annotations

import hashlib
import time
from threading import Lock
from typing import Any, Dict, Optional

from jep_agent.core.event import canonicalize, verify_event_signature


class JEPVerifier:
    def __init__(self):
        self._identity_payloads: Dict[tuple[str, str], str] = {}
        self._accepted: set[tuple[str, str]] = set()
        self._lock = Lock()

    @staticmethod
    def _checks() -> Dict[str, str]:
        return {
            "syntax": "not_checked",
            "cryptographic": "not_checked",
            "actor_binding": "not_checked",
            "freshness": "not_checked",
            "audience": "not_checked",
            "event_identity": "not_checked",
            "reference_integrity": "not_checked",
            "extension_processing": "not_checked",
            "chain_integrity": "not_checked",
            "policy": "not_checked",
        }

    def validate(
        self,
        ev: Dict[str, Any],
        public_key=None,
        *,
        mode: str = "archival",
        expected_aud: Optional[str] = None,
        max_age_seconds: Optional[int] = None,
        acceptance_domain: str = "default",
    ) -> Dict[str, Any]:
        checks = self._checks()
        errors = []
        required = ["jep", "id", "verb", "who", "when", "what", "sig"]
        for name in required:
            if name not in ev:
                checks["syntax"] = "fail"
                return self._result("invalid", mode, ev, checks, [{"code":"ERR_MISSING_REQUIRED_FIELD","message":name}])
        if ev["jep"] != "1" or ev["verb"] not in ("J", "D", "T", "V"):
            checks["syntax"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_INVALID_FIELD_TYPE","message":"invalid jep or verb"}])
        if not isinstance(ev["id"], str) or not ev["id"] or not isinstance(ev["who"], str) or type(ev["when"]) is not int:
            checks["syntax"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_INVALID_FIELD_TYPE","message":"invalid id/who/when"}])
        what, ref = ev["what"], ev.get("ref")
        if ev["verb"] == "D" and (not isinstance(what, dict) or "delegatee" not in what or "scope" not in what):
            checks["syntax"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_MISSING_REQUIRED_FIELD","message":"D requires delegatee/scope"}])
        if ev["verb"] == "T" and (ref is None or not isinstance(what, dict) or "termination_scope" not in what):
            checks["syntax"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_MISSING_REQUIRED_FIELD","message":"T requires ref/termination_scope"}])
        if ev["verb"] == "V" and (ref is None or not isinstance(what, dict) or "verification_scope" not in what or "result" not in what):
            checks["syntax"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_MISSING_REQUIRED_FIELD","message":"V requires ref/verification_scope/result"}])
        checks["syntax"] = "pass"

        if public_key is None:
            checks["cryptographic"] = "indeterminate"
            return self._result("indeterminate", mode, ev, checks, [{"code":"ERR_KEY_UNRESOLVED","message":"trusted public key required"}])
        if not verify_event_signature(ev, public_key):
            checks["cryptographic"] = "fail"
            return self._result("invalid", mode, ev, checks, [{"code":"ERR_SIGNATURE_INVALID","message":"signature verification failed"}])
        checks["cryptographic"] = "pass"

        identity = (ev["who"], ev["id"])
        payload_digest = hashlib.sha256(canonicalize(ev)).hexdigest()
        with self._lock:
            prior = self._identity_payloads.get(identity)
            if prior is not None and prior != payload_digest:
                checks["event_identity"] = "fail"
                return self._result("invalid", mode, ev, checks, [{"code":"ERR_EVENT_ID_CONFLICT","message":"same Event Identity with different unsigned content"}])
        checks["event_identity"] = "pass"

        if expected_aud is not None:
            if ev.get("aud") != expected_aud:
                checks["audience"] = "fail"
                return self._result("invalid", mode, ev, checks, [{"code":"ERR_DOMAIN_REQUIREMENT_UNSATISFIED","message":"aud mismatch"}])
            checks["audience"] = "pass"

        if max_age_seconds is not None:
            if ev["when"] < int(time.time()) - max_age_seconds:
                checks["freshness"] = "fail"
                return self._result("invalid", mode, ev, checks, [{"code":"ERR_EVENT_EXPIRED","message":"event outside freshness window"}])
            checks["freshness"] = "pass"

        checks["reference_integrity"] = "not_applicable" if ref is None else "not_checked"
        checks["extension_processing"] = "pass"

        acceptance = None
        with self._lock:
            self._identity_payloads.setdefault(identity, payload_digest)
            if mode == "acceptance":
                acceptance_key = (acceptance_domain, ev["who"], ev["id"])
                if acceptance_key in self._accepted:
                    acceptance = {"outcome":"already_accepted","effect_applied":False}
                else:
                    self._accepted.add(acceptance_key)
                    acceptance = {"outcome":"accepted","effect_applied":True}
        return self._result("valid", mode, ev, checks, errors, acceptance)

    def verify(self, ev: Dict[str, Any], public_key=None, **kwargs) -> str:
        """Compatibility convenience wrapper over the structured 0.7 result."""
        result = self.validate(ev, public_key, **kwargs)
        if result["status"] == "valid":
            acceptance = result.get("acceptance")
            if acceptance and acceptance["outcome"] == "already_accepted":
                return "ALREADY_ACCEPTED"
            return "VALID"
        if result["status"] == "indeterminate":
            return "INDETERMINATE"
        code = result.get("errors", [{}])[0].get("code", "INVALID")
        return f"INVALID: {code}"

    def reset_acceptance_state(self):
        with self._lock:
            self._accepted.clear()

    @staticmethod
    def _result(status, mode, ev, checks, errors, acceptance=None):
        result = {
            "status": status,
            "mode": mode,
            "profile": "jep-core-0.7",
            "event_identity": ({"who":ev.get("who"),"id":ev.get("id")} if isinstance(ev, dict) else None),
            "checks": checks,
            "warnings": [],
            "errors": errors,
        }
        if acceptance is not None:
            result["acceptance"] = acceptance
        return result
