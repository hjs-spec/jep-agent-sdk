# Release 2.1.1

Publish the repaired Core 0.7 package, including import fixes, independent conformance vectors, strict verification and safe HTML reports. Package metadata is checked before publication.

# Core 0.7 source repair (2.1 line)

Fix package import failures and complete the current Core 0.7 path: baseline signing, strict input handling, critical-extension rejection, exact-artifact hashes, typed references, companion chain/task separation, safe HTML export, examples and documentation.

CI verifies pinned Core J/D/T/V vectors, an independent validator, packaging coexistence and Python 3.10–3.13. Package-index publication is a separate action; merging this repair does not change an existing release or publish a new version. Historical 2.0.x archives require the corresponding legacy verifier.
