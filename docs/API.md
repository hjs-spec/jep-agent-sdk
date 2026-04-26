# API Reference

## Core Functions

### `build_event(verb, who, **kwargs)`
Build a JEP-04 compliant event dict.

### `sign_event(event, private_key)`
Sign event with Ed25519 JWS (RFC 7515).

### `verify_event_signature(event, public_key)` / `verify_payload_integrity(event)`
Cryptographic verification.

### `JEPVerifier.verify(event, **kwargs)`
Full verification pipeline (signature, replay, timestamp, chain).

## Decorators

### `@record(issuer=..., private_key=...)`
Auto-instrument any function with JEP events.

## Adapters

### `import jep.adapters.langchain.auto`
Global monkey-patch. All LangChain AgentExecutor runs auto-record.

### `import jep.adapters.openai_agents.auto`
Global monkey-patch. All OpenAI chat completions auto-record.

### `JEPMCPServer(name)` — MCP
Server wrapper that auto-records all registered tools.

## Determinability

### `DeterminabilityGuard(evidence_fn, target_fn, knowledge_base, on_insufficient="raise")`
Runtime gate. Decorated functions are blocked if evidence is insufficient.

## CLI

### `jep web [--port 8080]`
Launch causal topology viewer.

### `jep verify &lt;file.jsonl&gt; [--public-key key.pem]`
Verify event signatures and chain integrity.

### `jep export &lt;file.jsonl&gt; --output report.html`
Export full audit report with embedded causal graph.
