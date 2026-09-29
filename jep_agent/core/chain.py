"""Companion audit-chain profile for JEP Core 0.7.

Chain linkage is carried in an SDK extension and is not a JEP Core ref semantic.
"""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from typing import Any, Dict, List, Optional

from jep_agent.core.event import (
    event_hash,
    event_identity_ref,
    parse_json,
    sign_event,
    verify_payload_integrity,
)

CHAIN_EXTENSION = "jep-agent.chain"


class AuditChain:
    def __init__(self, issuer: str, private_key=None, storage_path: Optional[str] = None):
        self.issuer = issuer
        self.private_key = private_key
        self.events: List[Dict[str, Any]] = []
        self.storage_path = storage_path
        self._storage_loaded = False
        self._storage_created = False

    def append(self, event: Dict[str, Any]) -> Dict[str, Any]:
        ev = deepcopy(event)
        ev["who"] = self.issuer
        if self.events:
            prev = self.events[-1]
            ext = deepcopy(ev.get("ext") or {})
            ext[CHAIN_EXTENSION] = {
                "previous": event_identity_ref(prev)["value"],
                "artifact_hash": event_hash(prev),
            }
            ev["ext"] = ext
        if self.private_key is not None:
            ev = sign_event(ev, self.private_key)

        self.events.append(ev)
        try:
            if self.storage_path:
                self._flush()
        except Exception:
            self.events.pop()
            raise
        return deepcopy(ev)

    def verify_chain(self, public_key=None) -> bool:
        if public_key is None and self.private_key is not None:
            public_key = self.private_key.public_key()
        if not self.events or public_key is None:
            return False
        if not all(verify_payload_integrity(ev, public_key) for ev in self.events):
            return False
        for i in range(1, len(self.events)):
            prev = self.events[i - 1]
            curr = self.events[i]
            link = (curr.get("ext") or {}).get(CHAIN_EXTENSION)
            if not isinstance(link, dict):
                return False
            if link.get("previous") != {"who": prev.get("who"), "id": prev.get("id")}:
                return False
            if link.get("artifact_hash") != event_hash(prev):
                return False
        return True

    def export(self) -> List[Dict[str, Any]]:
        return deepcopy(self.events)

    def _is_storage_target(self, target: str) -> bool:
        if self.storage_path is None:
            return False
        return os.path.abspath(os.fspath(target)) == os.path.abspath(os.fspath(self.storage_path))

    def _atomic_save(self, target: str) -> None:
        payload = "".join(json.dumps(ev, ensure_ascii=False) + "\n" for ev in self.events)
        directory = os.path.dirname(os.path.abspath(target))
        prefix = f".{os.path.basename(target)}."
        fd, temporary = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        except BaseException:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise

    def save(self, path: Optional[str] = None, *, overwrite: bool = False):
        target = path or self.storage_path
        if not target:
            return

        target = os.fspath(target)
        managed = self._is_storage_target(target)
        if os.path.exists(target):
            allowed = overwrite or (managed and (self._storage_loaded or self._storage_created))
            if not allowed:
                raise FileExistsError(
                    f"Refusing to overwrite existing audit archive: {target}. "
                    "Load it before continuing or pass overwrite=True explicitly."
                )

        self._atomic_save(target)
        if managed:
            self._storage_created = True

    def load(self, path: Optional[str] = None):
        target = path or self.storage_path
        if not target:
            return

        target = os.fspath(target)
        managed = self._is_storage_target(target)
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as handle:
                loaded = [parse_json(line) for line in handle if line.strip()]
            self.events = loaded
        if managed:
            self._storage_loaded = True

    def _flush(self):
        self.save()
