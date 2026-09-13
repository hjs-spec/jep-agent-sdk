"""
JEP-Agent SDK 2.0
Reference implementation of draft-wang-jep-judgment-event-protocol-04
with JAC-01 extension support.
"""

from jep_agent.core.chain import AuditChain
from jep_agent.core.event import (
    build_event,
    canonicalize,
    event_hash,
    sign_event,
    verify_event_signature,
    verify_payload_integrity,
)
from jep_agent.core.verifier import JEPVerifier
from jep_agent.determinability import (
    DeterminabilityGuard,
    check_determinability,
    conflict_edges,
    evidence_cover,
)
from jep_agent.extensions.jac import build_jac_event, verify_jac_core
from jep_agent.primitives import delegate, judge, terminate, verify
from jep_agent.recorder import record, trace

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

__version__ = "2.0.0"
