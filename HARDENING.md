# Implementation hardening — September 2026

Do not report unverified or unfinished agent executions as valid.

## Changes

Signature verification binds the embedded signed payload to the current event. Chains verify every event, including the first, with a trusted public key. Exported events are copied. Missing keys return UNVERIFIED and unsigned chains do not pass integrity verification. Nonces are consumed after signature and policy checks. Async wrappers await completion and record errors/cancellation as termination. LangChain callback IDs no longer refer to a nonexistent field. The UI renders event fields as text. validate.py now exercises the actual signed API.

## Validation

```sh
python -m pytest -q
python validate.py
ruff check jep/ tests/
black --check jep/ tests/
```

## Compatibility and remaining limits

Legacy-04 embedded EdDSA signatures and legacy unsigned-event link hashes remain unchanged. This SDK is not the v0.6 wire SDK. verify_chain(public_key=...) is required for imported signed archives; unsigned traces remain available for recording. The jep import/console namespace still overlaps other packages; install in a separate environment. OpenAI monkey patching remains a legacy Completions integration; use the dedicated middleware for current Agents SDK integration.

## Follow-up hardening

The legacy synchronous Chat Completions patch is idempotent and retains events in the public trace manager instead of discarding each call chain. Quickstart now uses explicit @record instrumentation and a signing key. Documentation distinguishes this historical adapter from the current Agents SDK middleware and removes unsupported production/standardization claims.
