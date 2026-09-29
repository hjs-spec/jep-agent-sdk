# Changelog

## 2.1.7

- Require a trusted key for boolean payload-integrity success.
- Omit raw callable arguments and return values from `@record` by default; add explicit capture opt-in.
- Reject generator and async-generator wrappers that cannot be represented as completed calls.
- Preserve business exceptions and cancellation when secondary recording fails; add recording-stage metadata.
- Make local audit archive updates atomic and prevent accidental overwrite of unknown existing archives.
- Add explicit MCP archive-path configuration and safety-boundary regression coverage.

## 2.1.0

- Migrate the default event model to JEP Core 0.7.
- Add stable Event Identity `(who,id)`; remove mandatory Core nonce generation.
- Use detached compact JWS over the JCS-canonicalized unsigned event.
- Hash the full signed artifact for Event Hash.
- Replace nonce replay rejection with explicit idempotent acceptance semantics in `JEPVerifier.verify_result()`.
- Enforce Core 0.7 verb minima for D/T/V.
- Move SDK audit-chain linkage to the `jep-agent.chain` companion extension instead of overloading Core `ref`.
- Update LangChain/OpenAI/MCP tracing so execution failure is not misrepresented as a Termination event.
- Preserve historical signed artifacts externally; no automatic legacy fallback or re-signing is introduced.

## 2.0.0

- Move the legacy Python namespace to `jep_agent` and CLI to `jep-agent`; see MIGRATION-2.md.
- Retain historical event/signature compatibility.

## 1.0.0 (2026-04-26)

- Initial release
- Full JEP-04 compliance (RFC 8785 JCS, JWS EdDSA, anti-replay)
- JAC-01 extension support (`task_based_on`, fault recording)
- TRUE zero-code adapters: LangChain (`import .auto`), OpenAI (`import .auto`), MCP
- DeterminabilityGuard runtime gate for causal sufficiency checks
- Causal topology web viewer (SVG force-directed graph)
- Compliance export (`jep export`) with embedded causal graph
- CLI tools: `jep web`, `jep verify`, `jep export`
- Docker & docker-compose support
