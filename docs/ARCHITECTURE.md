# Agent SDK architecture

The maintained path records and verifies JEP Core 0.7 events. Protocol definitions
and conformance assets belong to [Core](https://github.com/hjs-spec/jep-core).
Software versions are independent of the wire member `jep: "1"`.

| Component | Responsibility | Boundary |
|---|---|---|
| Event helpers and primitives | Build J/D/T/V statements, canonicalize, sign and hash | A statement does not enforce its claimed action |
| `JEPVerifier` | Independent Core checks and process-local acceptance | Requires trusted keys; no distributed state or application policy engine |
| `AuditChain` | Local signed recording and predecessor links | SDK companion extension, separate from Core reference semantics |
| Recorder and callable adapters | Observe invocation, result and failure | Recording is not atomic with external side effects |
| CLI and web viewer | Inspect archives and declared links | Verification needs supplied keys; HTML reports are unverified projections |

[API details](API.md) · [Supported integrations and gaps](INTEGRATIONS.md) ·
[Historical format migration](../MIGRATION-0.7.md).

## Optional research helpers

`jep_agent.determinability` contains finite-model research helpers and an optional
application decorator. Existing top-level imports remain available for compatibility.
The recorder, signing, Core verifier and TSTO binding do not call this module.

`Determined` means the supplied configurations contain no modeled observation/target
conflict. It does not prove sufficient real-world evidence, completeness, authority,
or TSTO completion. An empty guard knowledge base performs no comparison. A
nonempty guard compares that model plus the current context; the caller defines both
observation and target functions. Guard contexts contain `args`, `kwargs` and a
legacy `tools_used` convenience value drawn only from a first positional list;
use `args`/`kwargs` explicitly for other call signatures.

For a modeled conflict, `raise` blocks, `warn` intentionally allows execution, and
`fallback` invokes the configured alternative. Unknown modes and missing/noncallable
fallbacks are configuration errors. This helper is outside the protocol conformance
and acceptance path; new protocol requirements must not depend on it.

## Viewer deployment

The viewer container installs the base SDK without optional LangChain/OpenAI
framework packages or a compiler toolchain. `docker compose up --build` starts the
viewer on port 8080. Choose a JSONL file in the browser; the viewer reads it locally.
There is no server-side archive directory or `JEP_STORAGE_PATH` option.
