# JEP-Agent SDK 2.1 — JEP Core 0.7

Record signed Core 0.7 events about agent calls, export them, and verify their integrity.

## Install

```sh
pip install jep-agent-sdk
```

The Python import is `jep_agent`; the command is `jep-agent`.

## Local create → export → independent verification

No API, account or hosted service is required after installing dependencies.
The runnable example is maintained in this repository:

```sh
git clone --branch v2.1.8 --depth 1 https://github.com/hjs-spec/jep-agent-sdk.git
cd jep-agent-sdk
python -m pip install jep-agent-sdk==2.1.8
python examples/local_roundtrip.py create ./local-evidence
python examples/local_roundtrip.py verify ./local-evidence
```

The `verify` command reopens the exported files in a separate process. The directory contains `event.json`,
`public-key.pem` and `keys.json`; the temporary private key is never exported.
Verification reports `status: valid`, `cryptographic: pass` and the original
Event Hash. Existing directories are never overwritten.

An independently implemented Core verifier can check the same files:

```sh
python -m pip install jep-core-conformance==0.7.7
jep-validate validate ./local-evidence/event.json --keys ./local-evidence/keys.json
```

The demonstration uses a temporary key. A public key shipped with a record proves
signature consistency; identifying a real actor requires an independently trusted
key/profile. Changing the signed claim causes verification to fail.

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

- `@record` retains function names and lifecycle status by default. Enable `capture_values=True` only for arguments and results that are safe to retain.
- `RecordingError.call_executed=True` means the business call already ran; do not automatically retry it.
- Load an existing archive before appending. Replacing it requires `save(..., overwrite=True)`.

See the [integration guide](docs/INTEGRATIONS.md#record-a-callable) for asynchronous calls, unsupported generators and failure handling.

## Inspect and verify

```sh
jep-agent verify events.jsonl --public-key public-key.pem
jep-agent export events.jsonl --output report.html
jep-agent web --port 8080
```

The CLI checks Core signatures and any local audit-chain links. It does not resolve arbitrary external references. The viewer and HTML export show recorded relationships and **Signed (unverified)** status; visual links do not establish causality or legal responsibility.

<a id="core-and-companion-boundaries"></a>

## Acceptance and local extensions

`JEPVerifier` acceptance state is process-local and is lost on restart. Repeated
delivery of the same identity and unsigned content returns `already_accepted`;
different content under the same identity is rejected. For shared durable state,
use the [reference API](https://github.com/hjs-spec/jep-api#state-and-multi-host-deployment).

The SDK stores audit links in `ext['jep-agent.chain']` and local task links in
`ext['jep-agent.jac']`. See the [API reference](docs/API.md) for supported checks
and [Core contract](https://github.com/hjs-spec/jep-core#current-contract) for event semantics.

## Optional framework adapters

The experimental OpenAI adapter targets synchronous Chat Completions; the
LangChain auto patch targets historical AgentExecutor APIs. Install their extra
dependencies only when using those adapters:

```sh
pip install 'jep-agent-sdk[langchain,openai]'
```

## Development

From a source checkout:

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
