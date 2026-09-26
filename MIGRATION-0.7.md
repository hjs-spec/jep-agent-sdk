# Migrating to the Core 0.7 source line

Version 2.1 produces Core 0.7 events. Versions 2.0.x retain the historical JEP-04/JAC-01 format. Keep historical archives and the matching legacy verifier unchanged. Never add fields to, re-sign, or reinterpret old records merely to pass current validation. There is no automatic format fallback.

| Earlier usage | Current usage |
|---|---|
| `nonce` as event handle | Stable `id`, scoped by `who` |
| `verify(who, content=...)` | `verify(who, ref=..., verification_scope=[...], result=...)` |
| `extensions` in a Core event | `ext` with object-valued extension bodies |
| Hash of unsigned event as identity | `(who,id)`; full signed Event Hash only pins an artifact |
| Chain parent in `ref` | Local `ext['jep-agent.chain']` |
| Top-level `task_based_on` | Local `ext['jep-agent.jac']['task_based_on']` |
| Error interpreted as T | J/V result statement; T specifically declares termination scope |

`build_event` requires an explicit `what`. `sign_event` returns a signed copy; use the returned value. Signing defaults to `alg: Ed25519` and `kid: <who>#key-1`. Supply `kid=` to identify a different key. Actor-key binding remains an external trust decision.

The short-lived pre-fix 2.1 source emitted detached `EdDSA` signatures. To verify those exact bytes, explicitly call `verify_event_signature(event, key, signature_profile='legacy-eddsa')`. This checks signature bytes only and does not promote a historical record to current conformance. Embedded JEP-04 signatures still require the historical release. Newly produced events always use the current baseline.

`build_jac_event` / `verify_jac_core` are compatibility names for a local task-link companion. They are not a claim that JAC-01 or another external JAC version has been migrated. Required lookup callbacks and trusted signature verification must be supplied before reporting the companion valid.

`JEPVerifier.verify_result(..., mode='acceptance')` uses process-local state. Re-signing unchanged unsigned content is a retry even when the artifact hash changes. A restart loses that state: production acceptance needs durable shared state and atomic effect handling. The SDK does not perform external business effects.
