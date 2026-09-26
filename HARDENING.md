# Core 0.7 implementation checks and limits

The current path rejects malformed JSON values, duplicate members at file ingress, unsupported top-level fields, malformed references, non-canonical base64url, duplicate JOSE headers, unsupported critical headers and critical event extensions. Missing keys are indeterminate. Invalid events do not consume acceptance state.

Events are signed with the detached Ed25519/JCS baseline. Event Hash includes the signature. In-memory acceptance compares unsigned content by `(who,id)`, so a valid new signature does not create a second acceptance effect. A lock serializes concurrent calls inside one process; this does not provide durable or multi-host acceptance.

Archive chain checks verify every signature, the predecessor identity and full-artifact pin. HTML export escapes visible text and embedded JSON; browser graphs display exact artifact hashes and typed event references separately. Viewers do not perform cryptographic validation.

Core does not enforce actor binding, external reference availability, causality, policy, legal consequences, or truth. A function execution error is not automatically a Termination statement. The `jep-agent.jac` and `jep-agent.chain` extensions are local companion behavior.

Historical releases and archives remain separate; see [migration](MIGRATION-0.7.md). The legacy OpenAI/LangChain monkey patches are experimental. Prefer explicit `@record` instrumentation when adapter compatibility is uncertain.

```sh
python -m compileall -q jep_agent tests
ruff check jep_agent tests
black --check jep_agent tests
python -m pytest -q
python validate.py
python -m build --wheel
python scripts/check_coexistence.py dist/*.whl
```
