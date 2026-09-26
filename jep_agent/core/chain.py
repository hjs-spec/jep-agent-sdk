"""Audit-chain composition above JEP Core 0.7.

Chain ordering is carried in an extension; Core ref remains available for
verb semantics such as T/V targets and is not overloaded as an implicit
previous-event hash pointer.
"""

import json
import os
from copy import deepcopy
from typing import Any, Dict, List, Optional

from jep_agent.core.event import event_hash, sign_event, verify_event_signature

CHAIN_EXT = "org.hjs.audit-chain"


def event_reference(event: Dict[str, Any], *, pin_artifact: bool = True) -> Dict[str, Any]:
    ref = {"type": "jep:event", "value": {"who": event["who"], "id": event["id"]}}
    if pin_artifact and event.get("sig"):
        ref["hash"] = event_hash(event)
    return ref


class AuditChain:
    def __init__(self, issuer: str, private_key=None, storage_path: Optional[str] = None):
        self.issuer = issuer
        self.private_key = private_key
        self.events: List[Dict[str, Any]] = []
        self.storage_path = storage_path

    def append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        event = deepcopy(event)
        event["who"] = self.issuer
        if self.events:
            ext = deepcopy(event.get("ext") or {})
            ext[CHAIN_EXT] = {"previous": event_reference(self.events[-1], pin_artifact=True)}
            event["ext"] = ext
        if self.private_key is not None:
            event = sign_event(event, self.private_key)
        self.events.append(event)
        if self.storage_path:
            self._flush()
        return deepcopy(event)

    def verify_chain(self, public_key=None) -> bool:
        if public_key is None and self.private_key is not None:
            public_key = self.private_key.public_key()
        if not self.events or public_key is None:
            return False
        if not all(verify_event_signature(ev, public_key) for ev in self.events):
            return False
        for i in range(1, len(self.events)):
            previous = self.events[i - 1]
            link = (self.events[i].get("ext") or {}).get(CHAIN_EXT, {}).get("previous")
            if link != event_reference(previous, pin_artifact=True):
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
