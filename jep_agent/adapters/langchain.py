"""LangChain tracing adapter for JEP Core 0.7."""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

from jep_agent.core.chain import AuditChain
from jep_agent.core.event import event_identity_ref
from jep_agent.primitives import judge, verify


class _JEPCallbackHandler:
    """Minimal callback interface compatible with LangChain."""

    def __init__(
        self,
        issuer: str = "langchain:agent",
        private_key=None,
        storage_path: Optional[str] = None,
    ):
        self.chain = AuditChain(issuer=issuer, private_key=private_key, storage_path=storage_path)
        self._run_stack: List[Dict[str, Any]] = []
        self._tool_stack: List[Dict[str, Any]] = []

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        ev = self.chain.append(judge(
            who=self.chain.issuer,
            what={"claim": "chain_start", "inputs": inputs or {}},
        ))
        self._run_stack.append(event_identity_ref(ev))
        return ev

    def on_chain_end(self, outputs: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Any:
        ref = self._run_stack.pop() if self._run_stack else None
        if ref is None:
            return None
        return self.chain.append(verify(
            who=self.chain.issuer,
            ref=ref,
            verification_scope=["execution_result"],
            result={"status": "completed", "outputs": outputs or {}},
        ))

    def on_chain_error(self, error: Exception, **kwargs: Any) -> Any:
        ref = self._run_stack.pop() if self._run_stack else None
        if ref is None:
            return None
        return self.chain.append(verify(
            who=self.chain.issuer,
            ref=ref,
            verification_scope=["execution_result"],
            result={"status": "error", "error": str(error)},
        ))

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]] = None,
        input_str: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        tool_name = serialized.get("name") if serialized else "unknown"
        ev = self.chain.append(judge(
            who=self.chain.issuer,
            what={"claim": "tool_start", "tool": tool_name, "input": input_str},
        ))
        self._tool_stack.append(event_identity_ref(ev))
        return ev

    def on_tool_end(
        self,
        output: Optional[str] = None,
        observation: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        ref = self._tool_stack.pop() if self._tool_stack else None
        if ref is None:
            return None
        return self.chain.append(verify(
            who=self.chain.issuer,
            ref=ref,
            verification_scope=["execution_result"],
            result={"status": "completed", "output": str(output) if output else str(observation)},
        ))

    def on_tool_error(self, error: Exception, **kwargs: Any) -> Any:
        ref = self._tool_stack.pop() if self._tool_stack else None
        if ref is None:
            return None
        return self.chain.append(verify(
            who=self.chain.issuer,
            ref=ref,
            verification_scope=["execution_result"],
            result={"status": "error", "error": str(error)},
        ))

    def export(self) -> List[Dict[str, Any]]:
        return self.chain.export()

    def save(self, path: Optional[str] = None):
        self.chain.save(path)


def _patch_langchain():
    try:
        from langchain.agents import AgentExecutor as _OrigAgentExecutor
    except ImportError:
        try:
            from langchain_core.agents import AgentExecutor as _OrigAgentExecutor
        except ImportError:
            return

    _orig_init = _OrigAgentExecutor.__init__
    _orig_run = (\n        _OrigAgentExecutor.invoke\n        if hasattr(_OrigAgentExecutor, "invoke")\n        else _OrigAgentExecutor.run\n    )

    def _jep_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        if not hasattr(self, "_jep_handler"):
            self._jep_handler = _JEPCallbackHandler()
        if (\n            hasattr(self, "callbacks")\n            and isinstance(self.callbacks, list)\n            and self._jep_handler not in self.callbacks\n        ):
            self.callbacks.append(self._jep_handler)

    def _jep_run(self, *args, **kwargs):
        if not hasattr(self, "_jep_handler"):
            self._jep_handler = _JEPCallbackHandler()
        callbacks = list(kwargs.get("callbacks", []))
        if self._jep_handler not in callbacks:
            callbacks.append(self._jep_handler)
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
    return _JEPCallbackHandler(issuer=issuer, private_key=private_key, storage_path=storage_path)


class _AutoPatchModule:
    def __init__(self):
        _patch_langchain()


sys.modules[__name__ + ".auto"] = _AutoPatchModule()
