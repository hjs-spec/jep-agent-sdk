# Core 0.7 API

- `build_event(verb, who, what, *, event_id=None, aud=None, ref=None, ext=None, ext_crit=None, when=None)` creates an unsigned event. J requires a claim; D requires `delegatee` and `scope`; T requires a reference and `termination_scope`; V requires a reference, `verification_scope` and `result`.
- `sign_event(event, private_key, *, kid=None)` returns a signed copy. The protected header uses Ed25519 and a key identifier.
- `canonicalize(event)` returns unsigned JCS bytes. `event_hash(event)` hashes the complete signed artifact.
- `event_identity_ref(event)` in `jep_agent.core.event` builds a typed `(who,id)` reference.
- `verify_event_signature(event, public_key)` checks the selected signature baseline. It does not establish actor identity or validate all Core semantics.
- `JEPVerifier.verify_result(event, public_key, *, mode='archival', expected_aud=None, max_age_seconds=None)` checks Core structure, cryptography, critical extensions and requested profile checks. Acceptance mode uses a process-local identity store. `verify(...)` is an archival compatibility wrapper returning VALID / INVALID / UNVERIFIED.
- `AuditChain(issuer, private_key=None, storage_path=None)` appends local companion links. `verify_chain(public_key)` checks every signature and link. `export()` returns copies.
- `@record(issuer=..., private_key=..., chain=...)` records synchronous or asynchronous invocation and completion. Cancellation and errors do not imply termination of authority.
- `build_jac_event(...)` stores local task links in `ext['jep-agent.jac']`; `verify_jac_core(...)` requires external verification/lookup callbacks. Neither claims formal JAC conformance.

CLI: `jep-agent verify`, `jep-agent export`, and `jep-agent web`. Graphs are views of recorded relationships, not proof of causal or legal conclusions. See [migration](../MIGRATION-0.7.md) for historical archives and signature profiles.

The web viewer reads JSONL locally in the browser and rejects ambiguous or malformed JSON. Its separate local upload endpoint uses the SDK's strict JSON parser. HTML exported from the viewer embeds escaped event data so reopening the report restores its interactive view without a server. CLI HTML reports remain static tables. Both reports are unverified projections: exact artifact pins must match before a link is drawn, and conflicting artifacts with the same identity remain unresolved without a pin.
