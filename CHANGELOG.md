# Changelog

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
