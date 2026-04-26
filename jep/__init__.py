"""
JEP-Agent SDK 1.0
Reference implementation of draft-wang-jep-judgment-event-protocol-04
with JAC-01 extension support.
"""

from jep.core.event import (
    build_event,
    sign_event,
    verify_event_signature,
    verify_payload_integrity,
    canonicalize,
    event_hash,
)
from jep.core.verifier import JEPVerifier
from jep.core.chain import AuditChain
from jep.primitives import judge, delegate, terminate, verify
from jep.recorder import record, trace
from jep.determinability import check_determinability, conflict_edges, evidence_cover, DeterminabilityGuard
from jep.extensions.jac import build_jac_event, verify_jac_core

__all__ = [
    "build_event",
    "sign_event",
    "verify_event_signature",
    "verify_payload_integrity",
    "canonicalize",
    "event_hash",
    "JEPVerifier",
    "AuditChain",
    "judge",
    "delegate",
    "terminate",
    "verify",
    "record",
    "trace",
    "check_determinability",
    "conflict_edges",
    "evidence_cover",
    "DeterminabilityGuard",
    "build_jac_event",
    "verify_jac_core",
]

__version__ = "1.0.0"
