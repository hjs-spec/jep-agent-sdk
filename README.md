> Historical repository.
>
> This repository reflects an earlier design line and is no longer the current implementation track.
>
> Current versions:
>
> - JEP v0.6: https://github.com/hjs-spec/jep-v06
> - JEP API v0.6: https://github.com/hjs-spec/jep-api
> - HJS v0.5: https://github.com/hjs-spec/hjs-05
> - JAC v0.5: https://github.com/hjs-spec/jac-agent-02

# JEP-Agent SDK 1.0

[![IETF Draft](https://img.shields.io/badge/IETF-JEP--04-blue)](https://datatracker.ietf.org/doc/draft-wang-jep-judgment-event-protocol-04/)
[![IETF Draft](https://img.shields.io/badge/IETF-JAC--01-purple)](https://datatracker.ietf.org/doc/draft-wang-jac-01/)
[![PyPI](https://img.shields.io/badge/pip-jep--agent--sdk-blue)](https://pypi.org/project/jep-agent-sdk/)
[![License](https://img.shields.io/badge/license-BSD--3--Clause-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**Historical tracing SDK with explicit instrumentation and local verification.**

JEP-Agent SDK is an experimental implementation of the [Judgment Event Protocol (JEP-04)](https://datatracker.ietf.org/doc/draft-wang-jep-judgment-event-protocol-04/) and [JAC-01](https://datatracker.ietf.org/doc/draft-wang-jac-01/). It records instrumented calls using the historical event format. A configured signing key and independently trusted verification key are required for signature assurance.

---

## Install

```bash
pip install jep-agent-sdk
```

With framework adapters:
```bash
pip install jep-agent-sdk[langchain,openai]
```

> For current MCP and OpenAI Agents integrations, use `jep-mcp-wrapper` and `jep-openai-agents-middleware`. This repository retains legacy adapters.

---

## 30-Second Quickstart

```python
from jep import trace
from jep.recorder import record
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

trace.enable(issuer="did:example:agent-001", private_key=Ed25519PrivateKey.generate())

@record(issuer="did:example:agent-001", chain=trace.chain)
def my_agent(query: str) -> str:
    return f"Result for {query}"

my_agent("hello")
trace.view()   # See the J/D/T/V event chain in your terminal
```

---

## Legacy framework adapters

| Framework | Integration | Your Code Changes |
|-----------|-------------|-------------------|
| **LangChain** | `import jep.adapters.langchain.auto` | Experimental patch |
| **OpenAI Chat Completions (legacy)** | `import jep.adapters.openai_agents.auto` | Experimental patch |
| **MCP** | `from jep.adapters.mcp import JEPMCPServer` | **One line** |

---

## Causal Web Viewer

```bash
jep web --port 8080
```

Drag-and-drop your `events.jsonl`. Get an interactive force-directed causal graph. Click any node to inspect the full JEP event. Pan, zoom, export.

---

## Determinability Guard — Stop Agents from Guessing

```python
from jep.determinability import DeterminabilityGuard

guard = DeterminabilityGuard(
    evidence_fn=lambda ctx: len(ctx.get("tools_used", [])),
    target_fn=lambda ctx: ctx.get("outcome"),
    knowledge_base=[{"tools_used": ["search", "calc"], "outcome": 1},
                    {"tools_used": ["search"], "outcome": 0}],
    on_insufficient="raise",
)

@guard.require_determinable
def my_agent(query: str, tools_used: list) -> str:
    ...
```

**What it does:** If your agent hasn't gathered enough evidence to make a deterministic decision, the guard blocks execution and tells you exactly what's missing. This is an application-defined gate; it does not guarantee factual accuracy.

---

## CLI Tools

```bash
# Verify signatures, chains, and anti-replay
jep verify events.jsonl --public-key key.pem

# Export a full compliance report (HTML with embedded causal graph)
jep export events.jsonl --output report.html
```

---

## What is JEP?

JEP (Judgment Event Protocol) is a minimal log format proposed in an individual IETF Internet-Draft for AI agent decisions. It defines four immutable verbs:

| Verb | Meaning | RFC 2119 |
|------|---------|----------|
| **J** | Judge — Initiate a decision | MUST |
| **D** | Delegate — Transfer authority | MUST |
| **T** | Terminate — Close lifecycle | MUST |
| **V** | Verify — Validate an event | MUST |

Signing is optional at recording time. Unsigned events are unverified. This historical format uses its own embedded JWS payload and hash links; use `jep-v06` for the current detached JWS/JCS conformance baseline.

---

## Project Structure

```
jep/
├── core/           # JEP-04 protocol engine (event, crypto, verifier, chain)
├── primitives.py   # J/D/T/V convenience wrappers
├── recorder.py     # @record decorator + global trace manager
├── determinability.py  # Causal sufficiency gate (DeterminabilityGuard)
├── extensions/
│   └── jac.py      # JAC-01 cross-agent accountability
├── adapters/
│   ├── langchain.py      # TRUE zero-code auto-patch
│   ├── openai_agents.py  # TRUE zero-code auto-patch
│   └── mcp.py            # MCP server wrapper
├── cli/
│   └── main.py     # jep web | jep verify | jep export
└── web/
    └── static/
        └── index.html   # Drag-and-drop causal topology viewer
```

---

## Documentation

- [Architecture & Design Principles](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [JEP-04 Internet-Draft](https://datatracker.ietf.org/doc/draft-wang-jep-judgment-event-protocol-04/)
- [JAC-01 Internet-Draft](https://datatracker.ietf.org/doc/draft-wang-jac-01/)

---

## Contributing

```bash
git clone https://github.com/hjs-spec/jep-agent-sdk.git
cd jep-agent-sdk
make install
make test
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Author

**Yuqiang Wang**  
HJS Foundation Ltd.  
Email: signal@humanjudgment.org  
GitHub: [@hjs-spec](https://github.com/hjs-spec)

---

*JEP-Agent SDK is released under BSD-3-Clause. The protocol draft is an individual IETF Internet-Draft and does not represent IETF endorsement.*
