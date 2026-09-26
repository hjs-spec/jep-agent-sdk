# Release 2.1.2

- Preserve JCS signatures when exactly representable large numbers arrive in integer-token form after JavaScript serialization (for example `1e20`). Reject precision-losing integers and keep `when` within its existing interoperable integer range.

- Return `event_identity: null` for missing, empty or mistyped event identities in invalid-event diagnostics. Error responses now remain consumable by Core 0.7 result readers.
- Reject malformed identities without consuming acceptance state.
- Point package documentation to the current API guide.

Core 0.7 behavior and valid event signatures are unchanged. The in-memory acceptance store remains a local reference implementation.
