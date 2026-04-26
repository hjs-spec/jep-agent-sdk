"""
LangChain integration — TRUE zero-code tracing.
Usage:
    import jep.adapters.langchain.auto   # <-- That's it.
"""

import sys
from typing import Any, Dict, List, Optional

from jep.core.chain import AuditChain
from jep.primitives import judge, terminate, verify


class _JEPCallbackHandler:
    """Minimal callback interface compatible with LangChain."""

    def __init__(
        self,
        issuer: str = "langchain:agent",
        private_key=None,
        storage_path: Optional[str] = None,
    ):
        self.chain = AuditChain(issuer=issuer, private_key=private_key, storage_path=storage_path)
        self._run_stack: List[str] = []

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        content = {"type": "chain_start", "inputs": inputs or {}}
        ev = judge(who=self.chain.issuer, content=content)
        self.chain.append(ev)
        self._run_stack.append(ev["event_id"])

    def on_chain_end(self, outputs: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        content = {"type": "chain_end", "outputs": outputs or {}}
        ev = verify(who=self.chain.issuer, content=content)
        self.chain.append(ev)
        if self._run_stack:
            self._run_stack.pop()

    def on_chain_error(self, error: Exception, **kwargs: Any) -> Any:
        content = {"type": "chain_error", "error": str(error)}
        ev = terminate(who=self.chain.issuer, content=content)
        self.chain.append(ev)

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]] = None,
        input_str: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        tool_name = serialized.get("name") if serialized else "unknown"
        content = {"type": "tool_start", "tool": tool_name, "input": input_str}
        ev = judge(who=self.chain.issuer, content=content)
        self.chain.append(ev)

    def on_tool_end(
        self,
        output: Optional[str] = None,
        observation: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        content = {
            "type": "tool_end",
            "output": str(output) if output else str(observation),
        }
        ev = verify(who=self.chain.issuer, content=content)
        self.chain.append(ev)

    def on_tool_error(self, error: Exception, **kwargs: Any) -> Any:
        content = {"type": "tool_error", "error": str(error)}
        ev = terminate(who=self.chain.issuer, content=content)
        self.chain.append(ev)

    def export(self) -> List[Dict[str, Any]]:
        return self.chain.events

    def save(self, path: Optional[str] = None):
        self.chain.save(path)


def _patch_langchain():
    """Monkey-patch LangChain AgentExecutor to auto-inject JEP callbacks."""
    try:
        from langchain.agents import AgentExecutor as _OrigAgentExecutor
    except ImportError:
        try:
            from langchain_core.agents import AgentExecutor as _OrigAgentExecutor
        except ImportError:
            return

    _orig_init = _OrigAgentExecutor.__init__
    _orig_run = (
        _OrigAgentExecutor.invoke
        if hasattr(_OrigAgentExecutor, "invoke")
        else _OrigAgentExecutor.run
    )

    def _jep_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        if not hasattr(self, "_jep_handler"):
            self._jep_handler = _JEPCallbackHandler()
        callbacks = list(kwargs.get("callbacks", []))
        if isinstance(callbacks, list) and self._jep_handler not in callbacks:
            callbacks.append(self._jep_handler)
            kwargs["callbacks"] = callbacks
            if hasattr(self, "callbacks"):
                if isinstance(self.callbacks, list):
                    if self._jep_handler not in self.callbacks:
                        self.callbacks.append(self._jep_handler)

    def _jep_run(self, *args, **kwargs):
        if not hasattr(self, "_jep_handler"):
            self._jep_handler = _JEPCallbackHandler()
        callbacks = kwargs.get("callbacks", [])
        if isinstance(callbacks, list):
            if self._jep_handler not in callbacks:
                callbacks = callbacks + [self._jep_handler]
                kwargs["callbacks"] = callbacks
        return _orig_run(self, *args, **kwargs)

    _OrigAgentExecutor.__init__ = _jep_init
    if hasattr(_OrigAgentExecutor, "invoke"):
        _OrigAgentExecutor.invoke = _jep_run
    else:
        _OrigAgentExecutor.run = _jep_run


def enable_tracing(
    issuer: str = "langchain:agent",
    private_key=None,
    storage_path: Optional[str] = None,
):
    """Explicit tracing with callback instance (for manual injection)."""
    return _JEPCallbackHandler(issuer=issuer, private_key=private_key, storage_path=storage_path)


class _AutoPatchModule:
    def __init__(self):
        _patch_langchain()


sys.modules[__name__ + ".auto"] = _AutoPatchModule()
