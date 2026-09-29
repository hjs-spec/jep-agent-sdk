"""JEP-Agent SDK 2.1.

Agent tracing helpers aligned with JEP Core 0.7.
Chain/JAC behavior is companion semantics, not JEP Core.
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
from jep_agent.recorder import RecordingError, record, trace

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
    "RecordingError",
    "check_determinability",
    "conflict_edges",
    "evidence_cover",
    "DeterminabilityGuard",
    "build_jac_event",
    "verify_jac_core",
]

__version__ = "2.1.6"
