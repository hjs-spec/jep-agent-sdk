# Historical integration archives

Eight companion experiments have left active development. Their source,
releases and readers are preserved in their original repositories. Keep the
original format/version when inspecting an existing archive.

| Historical capability | Preserved reader | Maintained path / remaining gap |
|---|---|---|
| Browser replay and flexible input aliases | `jep-replay-visualizer` | SDK reports for SDK events; no equivalent alias decoder |
| Local delegation lineage and scope rules | `jep-lineage-explorer` | SDK declared links; no replacement for its local policy model |
| Local envelope and mock profile execution | `jep-runtime` | SDK/API signed Core events; no automatic envelope conversion |
| Scope attenuation and revocation model | `jep-authority-runtime` | Application authorization policy; no Core policy-engine replacement |
| LangGraph observation hooks | `jep-langgraph-adapter` | Explicit callable recording; no full graph-hook replacement |
| OpenAI Agents SDK RunHooks | `jep-openai-agents-middleware` | Explicit callable recording; maintained RunHooks integration is not implemented |
| MCP lifecycle and nested replay | `jep-mcp-wrapper` | Simple signed callable/MCP recording; no equivalent lifecycle replay |
| Claude transcript import and `.jcrpack` | `jep-claude-replay` | No maintained transcript/pack importer |

Find these repositories and their maintenance status in the
[directory](https://github.com/hjs-spec/.github/blob/main/ARCHIVES.md#retired-experiments).
Do not reinterpret old records as Core 0.7, rewrite old signatures, or fall back
to another decoder after validation fails. An explicit migration must preserve
the source evidence and define/test each field and semantic mapping.

For current recording, return to the [integration guide](INTEGRATIONS.md).
