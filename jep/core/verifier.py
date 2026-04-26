"""
JEP-04 and JAC-01 verification logic.
"""

import time
from typing import Optional, Dict, Any, Set, Callable
from jep.core.event import verify_event_signature, verify_payload_integrity


class JEPVerifier:
    def __init__(self, clock_skew_tolerance: int = 300):
        self.seen_nonces: Set[str] = set()
        self.clock_skew = clock_skew_tolerance
    
    def verify(
        self,
        ev: Dict[str, Any],
        public_key=None,
        expected_aud: Optional[str] = None,
        task_parent_lookup: Optional[Callable[[str], bool]] = None,
    ) -> str:
        required = ["jep", "verb", "who", "when", "nonce", "sig"]
        for f in required:
            if f not in ev:
                return f"INVALID: missing required field '{f}'"
        
        if ev["jep"] != "1":
            return "INVALID: bad jep version"
        
        if ev["verb"] not in ("J", "D", "T", "V"):
            return "INVALID: bad verb"
        
        if public_key is not None:
            if not verify_event_signature(ev, public_key):
                return "INVALID: signature verification failed (INVALID_SIGNATURE)"
        
        if ev.get("sig") and not verify_payload_integrity(ev):
            return "INVALID: payload tampered after signing"
        
        nonce = ev["nonce"]
        if nonce in self.seen_nonces:
            return "INVALID: replay detected (EXPIRED_RECEIPT)"
        self.seen_nonces.add(nonce)
        
        now = int(time.time())
        ts = ev["when"]
        if abs(now - ts) > self.clock_skew:
            return "INVALID: timestamp outside allowed window (EXPIRED_RECEIPT)"
        
        if expected_aud is not None:
            if ev.get("aud") != expected_aud:
                return "INVALID: aud mismatch"
        
        ref = ev.get("ref")
        if ref is not None and not isinstance(ref, str):
            return "INVALID: ref must be string or null"
        
        task_based_on = ev.get("task_based_on")
        if task_based_on is not None and task_parent_lookup is not None:
            if not task_parent_lookup(task_based_on):
                extensions = ev.get("extensions", {})
                if "https://jac.org/fault" in extensions:
                    fault = extensions["https://jac.org/fault"]
                    if fault.get("expected_parent") == task_based_on:
                        return "VALID_WITH_FAULT"
                return "INVALID: parent task not found (BROKEN_TASK_CHAIN)"
        
        return "VALID"
    
    def reset_nonce_cache(self):
        self.seen_nonces.clear()
