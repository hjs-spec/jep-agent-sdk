# Release 2.0.0

Fix the Python namespace and CLI command collisions with the current JEP clients. Import the legacy SDK as `jep_agent` and run `jep-agent`; see MIGRATION-2.md for existing shared installations. Historical JEP-04/JAC-01 signed events remain unchanged. Internal imports, adapters, examples, Docker and CI use the new namespace.
