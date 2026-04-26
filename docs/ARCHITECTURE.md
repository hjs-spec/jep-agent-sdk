# JEP-Agent SDK Architecture

## Layers

```
┌─────────────────────────────────────────┐
│  Adapters (LangChain, OpenAI, MCP)      │
│  — TRUE zero-code via monkey-patch      │
├─────────────────────────────────────────┤
│  DeterminabilityGuard (runtime gate)      │
├─────────────────────────────────────────┤
│  Recorder / Trace Manager                 │
├─────────────────────────────────────────┤
│  Primitives (J/D/T/V)                   │
├─────────────────────────────────────────┤
│  Core (Event, JWS, Verifier, Chain)     │
│  — RFC 8785 JCS, RFC 7515 JWS, Ed25519  │
├─────────────────────────────────────────┤
│  Extensions (JAC-01, Privacy, TTL)        │
└─────────────────────────────────────────┘
```

## Design Principles

1. **Narrow Waist**: Core is minimal (~800 lines). Everything else is adapter/extension.
2. **RFC Compliance**: Strict JEP-04 (RFC 8785 JCS, JWS EdDSA).
3. **True Zero-Code**: `import jep.adapters.xxx.auto` — no business code changes.
4. **Privacy by Default**: Supports digest-only, TTL, identity rotation.
5. **Causal Observability**: DeterminabilityGuard prevents execution on insufficient evidence.
```
