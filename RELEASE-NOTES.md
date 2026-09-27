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
