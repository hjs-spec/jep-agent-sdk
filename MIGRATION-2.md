# Migrating to Agent SDK 2.0

The distribution remains `jep-agent-sdk`. Python imports move from `jep` to `jep_agent`; the executable moves from `jep` to `jep-agent`. This is an intentional major release so the legacy SDK can coexist with `jep-sdk-py` (`from jep import JEPClient`) and `jep-cli` (`jep`). No colliding compatibility shim is installed.

```python
from jep_agent import AuditChain, judge, trace
from jep_agent.core.verifier import JEPVerifier
from jep import JEPClient  # current JEP-Core-0.6 HTTP client
```

```sh
python -m pip install --upgrade 'jep-agent-sdk>=2,<3'
jep-agent verify events.jsonl --public-key key.pem
```

If Agent SDK 1.x and the current Python SDK/CLI were installed together, removing the old distribution can remove files owned by the other packages. Restore those files after upgrading:

```sh
python -m pip install --upgrade 'jep-agent-sdk>=2,<3'
python -m pip install --force-reinstall 'jep-sdk-py>=0.6.2' 'jep-cli>=0.6.1'
```

Update imports in application code, adapters and launch scripts, including `jep.web.server:app` to `jep_agent.web.server:app`. Existing JSONL archives, hashes, signing keys and signatures are unchanged and continue to use the legacy verifier. Package version 2.0 is not a new wire protocol. For current 0.6 events use the three main SDKs and JEP API.
