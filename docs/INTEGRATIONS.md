# Maintained recording and reports

Use this SDK for local signed Core 0.7 recording. Use the
[API and HTTP clients](https://github.com/hjs-spec/.github/blob/main/PROJECTS.md#integrate)
when a service owns signing and shared acceptance state. Start with the
[packaged Core sample](https://github.com/hjs-spec/jep-core#verify-your-first-event)
to verify an event, then use the [local recorder example](../README.md#local-create--export--independent-verification)
or [HTTP Quickstart](https://github.com/hjs-spec/jep-quickstart) for your integration.

## Record a callable

The existing `record` wrapper supports synchronous and asynchronous functions.
Pass one `AuditChain` to related wrappers so their declared links share one owner.

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jep_agent.core.chain import AuditChain
from jep_agent.recorder import record

# Disposable demonstration key. Applications supply their configured key.
chain = AuditChain(issuer="did:example:app", private_key=Ed25519PrivateKey.generate())

@record(issuer=chain.issuer, chain=chain, auto_verify=False)
def summarize_public_status(status):
    return {"status": status}

assert summarize_public_status("ready") == {"status": "ready"}
assert chain.verify_chain()
events = chain.export()
```

`auto_verify=False` records invocation and result observations as J statements.
The default `True` records successful completion as a V statement scoped to
`execution_result`; it does not independently establish the result's truth.
Raw arguments and results are omitted by default. Set `capture_values=True` only
when retaining their `repr` is explicitly acceptable; otherwise construct explicit
events when redaction or digest-only evidence is required. Generator and
async-generator functions are rejected rather than being marked complete before
iteration finishes.

Recording can fail after an external side effect; it is not an atomic execution log.
A `RecordingError` with `call_executed=True` means the wrapped callable has already
run and its business effect must not be blindly retried. If the callable itself
raises or is cancelled and recording that outcome also fails, the original
exception/cancellation remains primary. A `RuntimeWarning` reports the secondary
recording failure; normal exception chaining is also retained where the Python
runtime preserves it. Existing `AuditChain.storage_path` archives must be loaded before append;
archive replacement is atomic and explicit overwrite requires
`save(..., overwrite=True)`.

Use `jep_agent.adapters.mcp.wrap_mcp_tool` for the existing simple MCP callable
wrapper. Neither wrapper installs a framework-wide hook or enforces authorization.
See the [API guide](API.md) for verification, export and the local web viewer.
Reports display recorded relationships; cryptographic checks need trusted keys,
and authority or business-policy checks need separately configured rules.

## Adding an integration

Add new signed recording, framework hooks and reports to this SDK when a concrete
consumer needs them. Define the Core event mapping, data minimization and failure
behavior first. Reuse the current event/signing implementation and compatibility
gate. Keep framework dependencies optional. A separately installable package is
justified only by a distinct consumer and release lifecycle.

<a id="existing-experimental-archives"></a>

For old archives, see [historical readers and migration limits](HISTORICAL-ARCHIVES.md).
