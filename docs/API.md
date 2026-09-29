# Core 0.7 API

- `build_event(verb, who, what, *, event_id=None, aud=None, ref=None, ext=None, ext_crit=None, when=None)` creates an unsigned event. J requires a claim; D requires `delegatee` and `scope`; T requires a reference and `termination_scope`; V requires a reference, `verification_scope` and `result`.
- `sign_event(event, private_key, *, kid=None)` returns a signed copy. The protected header uses Ed25519 and a key identifier.
- `canonicalize(event)` returns unsigned JCS bytes. `event_hash(event)` hashes the complete signed artifact.
- `event_identity_ref(event)` in `jep_agent.core.event` builds a typed `(who,id)` reference.
- `verify_event_signature(event, public_key)` checks the selected signature baseline. It does not establish actor identity or validate all Core semantics.
- `verify_payload_integrity(event, public_key)` returns `True` only when a trusted public key is supplied and both event shape and signature pass. Without a key it returns `False`; use `JEPVerifier.verify_result(...)` when an explicit `indeterminate` cryptographic result is needed.
- `JEPVerifier.verify_result(event, public_key, *, mode='archival', expected_aud=None, max_age_seconds=None)` checks Core structure, cryptography, critical extensions and requested profile checks. Acceptance mode uses a process-local identity store. `verify(...)` is an archival compatibility wrapper returning VALID / INVALID / UNVERIFIED.
- `AuditChain(issuer, private_key=None, storage_path=None)` appends local companion links. `verify_chain(public_key)` checks every signature and link. `export()` returns copies. Persistent writes use atomic replacement; an existing `storage_path` must be loaded before append. `save(..., overwrite=True)` is the explicit destructive replacement path.
- `@record(issuer=..., private_key=..., chain=..., capture_values=False)` records synchronous or asynchronous invocation and completion while omitting raw arguments/results by default. Generator and async-generator functions are rejected. `RecordingError.call_executed` distinguishes pre-invocation recording failure from post-execution recording failure. Cancellation and business exceptions remain the primary raised outcome if error recording also fails.
- `build_jac_event(...)` stores local task links in `ext['jep-agent.jac']`; `verify_jac_core(...)` requires external verification/lookup callbacks. Neither claims formal JAC conformance.

CLI: `jep-agent verify`, `jep-agent export`, and `jep-agent web`. Graphs are views of recorded relationships, not proof of causal or legal conclusions. See [migration](../MIGRATION-0.7.md) for historical archives and signature profiles.

The web viewer reads JSONL locally in the browser and rejects ambiguous or malformed JSON. Its separate local upload endpoint uses the SDK's strict JSON parser. HTML exported from the viewer embeds escaped event data so reopening the report restores its interactive view without a server. CLI HTML reports remain static tables. Both reports are unverified projections: exact artifact pins must match before a link is drawn, and conflicting artifacts with the same identity remain unresolved without a pin.

## Optional finite-model helpers

`check_determinability`, `conflict_edges`, `evidence_cover` and
`DeterminabilityGuard` are research compatibility APIs, separate from Core and
TSTO/Binding verification. See the [scope and guard modes](ARCHITECTURE.md#optional-research-helpers).
A result applies only to the supplied model. Empty knowledge bases do not block
execution; `warn` explicitly allows it. Invalid modes and `fallback` without a
callable raise `ValueError` at construction.
