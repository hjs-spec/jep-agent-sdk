# Software 2.1.8

- Accept both Core 0.7 V `verification_scope` forms: a nonempty string or a nonempty unique string array. Preserve the signed representation and original Event Hash.
- Verify the published BYOI string-scope fixture and both producer forms against Core verifier 0.7.7; malformed scopes remain rejected.
- Use the released Core verifier consistently in CI and release validation, including the documented CLI roundtrip.
- Link contribution and private security-report routes from the SDK guide.

Core 0.7 semantics, frozen specification snapshots and existing signed fixtures are unchanged.

# Software 2.1.7

This release hardens the maintained JEP Core 0.7 SDK integration boundaries without changing the Core wire format or published protocol semantics.

- Require a trusted public key before the boolean payload-integrity helper can report success; callers that need an explicit missing-key state should use the structured verifier result.
- Minimize `@record` data capture by default. Raw arguments and return values are only retained with explicit `capture_values=True`.
- Reject generator and async-generator wrapping instead of reporting completion before iteration has actually finished.
- Add typed `RecordingError` stage metadata so pre-invocation recording failures and post-execution recording failures are distinguishable. Business exceptions and cancellation remain primary if outcome recording also fails.
- Make persistent `AuditChain` writes atomic, roll back failed in-memory appends, and refuse to overwrite an unknown existing archive until it is explicitly loaded or overwritten.
- Allow MCP server integrations to supply an explicit archive path and isolate adapter tests from persistent local files.
- Align README, API, integration and hardening documentation with these boundaries.

CI covers Python 3.10 through 3.13, package coexistence and the documented viewer container. Existing signed Core 0.7 artifacts remain unchanged.

# Software 2.1.6

The current baseline explicitly decodes JWS protected headers as UTF-8 instead of
allowing JSON encoding auto-detection. Explicit legacy profile behavior remains
unchanged. Tests cover six UTF-16/32 forms, retained valid noncanonical UTF-8
headers, and rejection before acceptance-state changes.

A local create/export/verify example now writes an event and public verification
material, reopens them in another process, rejects tampering and refuses to
overwrite an existing directory. No API or private-key export is required.

# Software 2.1.5

- Reject unknown `DeterminabilityGuard` conflict modes and missing/noncallable fallback handlers at construction. These invalid configurations previously allowed the guarded function to execute despite a modeled conflict. Explicit `warn` mode still allows execution.
- Replace the historical SDK architecture entry with the current component boundaries. Finite-model research helpers remain compatible optional APIs; they are not JEP Core checks, TSTO completion verification, or proof of real-world evidence sufficiency. The example now reads the actual call arguments and demonstrates a modeled conflict.
- Simplify the viewer container to the base SDK; remove unused framework extras, compiler installation, archive mount and unused storage environment variable. CI builds the documented Compose configuration and checks its HTTP entry.

Core wire/signature formats, existing signed archives and published protocol drafts are unchanged.

# Software 2.1.4

- Reject duplicate JSON members, non-finite/precision-losing numeric input and invalid Unicode before importing viewer archives. The local upload endpoint returns line-specific client errors for malformed records instead of silently replacing fields or returning a server error.
- Embed escaped event data in exported HTML and restore it when the report is reopened, including event details, links and Reset View. Reports remain local, unsigned projections; opening a report does not verify event signatures.
- Resolve report references against their exact artifact hash when pinned. Conflicting artifacts with one Event Identity remain unresolved without a matching pin. CLI and browser reports now share this boundary; CLI reports also resolve digest references.
- Label the viewer as a Core 0.7 event viewer and its edges as declared links.

Regression checks cover hostile JSON, exported-report reopening, preserved Event Hashes, conflicting identities and mismatched artifact pins. Core event/signature formats and previously published artifacts are unchanged.

# Software 2.1.3

Complete the JCS numeric roundtrip repair: accept the canonical shortest decimal spelling of a binary64 number as well as its exact integer value. For example, JavaScript emits `1000000000000000100` for the float whose exact integer value is `1000000000000000128`. Both serialize to the same JCS bytes. Noncanonical precision-losing integers and overflow remain rejected.

Regression coverage includes positive and negative shortest-form numbers, exact large integers, real signatures and unchanged Event Hashes. Published normative artifacts remain unchanged.

# Release 2.1.2

- Preserve JCS signatures when exactly representable large numbers arrive in integer-token form after JavaScript serialization (for example `1e20`). Reject precision-losing integers and keep `when` within its existing interoperable integer range.

- Return `event_identity: null` for missing, empty or mistyped event identities in invalid-event diagnostics. Error responses now remain consumable by Core 0.7 result readers.
- Reject malformed identities without consuming acceptance state.
- Point package documentation to the current API guide.

Core 0.7 behavior and valid event signatures are unchanged. The in-memory acceptance store remains a local reference implementation.
