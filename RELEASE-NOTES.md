# Software 2.1.3

Complete the JCS numeric roundtrip repair: accept the canonical shortest decimal spelling of a binary64 number as well as its exact integer value. For example, JavaScript emits `1000000000000000100` for the float whose exact integer value is `1000000000000000128`. Both serialize to the same JCS bytes. Noncanonical precision-losing integers and overflow remain rejected.

Regression coverage includes positive and negative shortest-form numbers, exact large integers, real signatures and unchanged Event Hashes. Published normative artifacts remain unchanged.

# Release 2.1.2

- Preserve JCS signatures when exactly representable large numbers arrive in integer-token form after JavaScript serialization (for example `1e20`). Reject precision-losing integers and keep `when` within its existing interoperable integer range.

- Return `event_identity: null` for missing, empty or mistyped event identities in invalid-event diagnostics. Error responses now remain consumable by Core 0.7 result readers.
- Reject malformed identities without consuming acceptance state.
- Point package documentation to the current API guide.

Core 0.7 behavior and valid event signatures are unchanged. The in-memory acceptance store remains a local reference implementation.
