# JEP-Agent SDK 2.1 — JEP Core 0.7

Record signed statements about agent calls and inspect their evidence. The current source implements JEP Core 0.7; historical 2.0.x releases implement the earlier JEP-04/JAC-01 format. See [migration](MIGRATION-0.7.md) before upgrading.

JEP is an individual IETF Internet-Draft, not an IETF-endorsed standard. Valid signatures do not establish factual truth, authorization, legality, successful external execution, or payment readiness.

## Install

```sh
pip install jep-agent-sdk
# Optional framework dependencies:
pip install 'jep-agent-sdk[langchain,openai]'
```

For source development, clone this repository and use `pip install -e '.[dev]'`. Imports use `jep_agent`; the command is `jep-agent`, independent of `jep-sdk-py` and `jep-cli`.

## Local create → export → independent verification

No API, account or hosted service is required after installing dependencies.
The runnable example is maintained in this repository:

```sh
git clone --branch v2.1.6 --depth 1 https://github.com/hjs-spec/jep-agent-sdk.git
cd jep-agent-sdk
python -m pip install jep-agent-sdk==2.1.6
python examples/local_roundtrip.py create ./local-evidence
python examples/local_roundtrip.py verify ./local-evidence
```

The second command starts a separate process. The directory contains `event.json`,
`public-key.pem` and `keys.json`; the temporary private key is never exported.
Verification reports `status: valid`, `cryptographic: pass` and the original
Event Hash. Existing directories are never overwritten.

An independently implemented Core verifier can check the same files:

```sh
python -m pip install jep-core-conformance==0.7.5
jep-validate validate ./local-evidence/event.json --keys ./local-evidence/keys.json
```

These are synthetic demonstration keys. A public key shipped with a record proves
signature consistency, not who supplied the record; real actor binding requires
an independently trusted key/profile. No freshness, policy, completion or payment
claim is implied. Changing the signed claim causes verification to fail.

## Signed trace

```python
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jep_agent import AuditChain, record

key = Ed25519PrivateKey.generate()
chain = AuditChain("agent:example", private_key=key)

@record(issuer=chain.issuer, chain=chain)
def task(value):
    return value * 2

assert task(21) == 42
assert chain.verify_chain(key.public_key())
chain.save("events.jsonl")
Path("public-key.pem").write_bytes(key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
))
```

Recording without a key is allowed for local traces, but produces unsigned, unverified records. Use a securely persisted key in a real deployment; this example generates a temporary key.

`@record` records the function name and lifecycle status by default, not raw arguments or return values. Set `capture_values=True` only when those values are intentionally safe to retain. Generator and async-generator functions are rejected because returning an iterator is not the same as completing execution.

If recording fails before invocation, `RecordingError.call_executed` is `False`. If the callable has already completed and completion recording fails, it is `True`; do not blindly retry the business action from that error alone. When the callable itself raises or is cancelled and recording that outcome also fails, the original exception or cancellation remains primary.

Audit archives are written through a same-directory temporary file and atomic replacement. An existing `storage_path` must be loaded before appending, or `save(..., overwrite=True)` must be used explicitly; an unknown existing archive is never silently replaced.

## Core and companion boundaries

| Concern | Behavior |
|---|---|
| Event Identity | Stable `(who, id)` |
| Signing payload | RFC 8785 canonical unsigned event |
| Baseline signature | Detached JWS, `alg: Ed25519`, protected `kid` |
| Event Hash | SHA-256 of the complete signed artifact, including `sig` |
| Validation | Independent syntax, cryptographic, extension and requested profile checks |
| Retry | Same identity and unsigned content returns `already_accepted` |
| Conflict | Same identity with different unsigned content is rejected |
| Freshness / audience | Checked only when requested |
| Unknown critical extension | Rejected before acceptance |
| Audit-chain linkage | `ext['jep-agent.chain']`; separate from Core `ref` |
| Research helpers | Optional finite-model determinability; outside Core/TSTO validation |
| Task linkage | Local `ext['jep-agent.jac']`; no formal JAC conformance claim |

The in-memory `JEPVerifier` acceptance store is for a single process. It is not a durable distributed acceptance service. An independently trusted public key must be supplied; `kid` alone does not prove actor identity. Reference resolution, actor binding, domain policy and external effects remain unchecked unless provided by a separate profile or application.

A function failure/cancellation produces a result statement, not a Core Termination event. Async tracing records completion only after the call finishes. A secondary recording failure never replaces the original business exception or cancellation.

## Inspect and verify

```sh
jep-agent verify events.jsonl --public-key public-key.pem
jep-agent export events.jsonl --output report.html
jep-agent web --port 8080
```

The CLI checks Core signatures and any local audit-chain links. It does not resolve arbitrary external references. The viewer and HTML export show recorded relationships and **Signed (unverified)** status; visual links do not establish causality or legal responsibility.

Framework adapters are experimental: the OpenAI adapter targets synchronous Chat Completions, and the LangChain auto patch targets historical AgentExecutor APIs. New signed integrations use the [callable recording path](docs/INTEGRATIONS.md). The separate Agents SDK middleware is a retired unsigned observation experiment; it is not the maintained Core integration path.

## Development

```sh
pip install '.[dev,langchain,openai]' build
make lint
python -m pytest -q
python validate.py
python -m build --wheel
python scripts/check_coexistence.py dist/*.whl
```

CI uses fixed Core 0.7 J/D/T/V vectors and a commit-pinned independent Core validator. It also installs the built wheel beside the Python SDK and CLI in both orders and checks independent uninstalls.

- [Architecture and research-helper boundaries](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Migration and historical compatibility](MIGRATION-0.7.md)
- [Implementation limits](HARDENING.md)
- [Canonical JEP Core repository](https://github.com/hjs-spec/jep-core)

BSD-3-Clause. Author: Yuqiang Wang, HJS Foundation, signal@humanjudgment.org.
