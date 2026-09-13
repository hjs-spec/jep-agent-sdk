"""
Audit chain maintenance with hash-linking.
"""

import hashlib
import json
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

from jep.core.event import canonicalize, sign_event, verify_event_signature


class AuditChain:
    def __init__(
        self,
        issuer: str,
        private_key=None,
        storage_path: Optional[str] = None,
    ):
        self.issuer = issuer
        self.private_key = private_key
        self.events: List[Dict[str, Any]] = []
        self.storage_path = storage_path

    def append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event = deepcopy(event)
        event["who"] = self.issuer

        if self.events:
            prev = self.events[-1]
            prev_hash = "sha256:" + hashlib.sha256(canonicalize(prev)).hexdigest()
            if event.get("ref") is None:
                event["ref"] = prev_hash

        if self.private_key is not None:
            event = sign_event(event, self.private_key)

        self.events.append(event)

        if self.storage_path:
            self._flush()

        return deepcopy(event)

    def verify_chain(self, public_key=None) -> bool:
        """Verify signatures and legacy-04 links, including the first event.

        Imported archives need the trusted public key. Unsigned traces cannot
        establish integrity and never return True from this method.
        """
        if public_key is None and self.private_key is not None:
            public_key = self.private_key.public_key()
        if not self.events or public_key is None:
            return False
        if not all(verify_event_signature(ev, public_key) for ev in self.events):
            return False
        for i in range(1, len(self.events)):
            prev = self.events[i - 1]
            curr = self.events[i]

            expected_ref = "sha256:" + hashlib.sha256(canonicalize(prev)).hexdigest()
            if curr.get("ref") != expected_ref:
                return False

        return True

    def export(self) -> List[Dict[str, Any]]:
        return deepcopy(self.events)

    def save(self, path: Optional[str] = None):
        target = path or self.storage_path
        if target:
            with open(target, "w", encoding="utf-8") as f:
                for ev in self.events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def load(self, path: Optional[str] = None):
        target = path or self.storage_path
        if target and os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                self.events = [json.loads(line) for line in f if line.strip()]

    def _flush(self):
        self.save()
