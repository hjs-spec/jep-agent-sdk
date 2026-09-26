# Changelog

## Unreleased

- Explicitly classify this package as a historical JEP-04/JAC-01 implementation.
- Do not use its nonce, embedded-payload JWS, bare-hash chain reference, or
  replay behavior as JEP Core 0.7 semantics.
- New JEP Core 0.7 integrations should use the 0.7 SDK/API path.
- Historical events remain unchanged and require explicit legacy handling.

# Changelog

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
