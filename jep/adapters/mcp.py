"""
MCP (Model Context Protocol) adapter for JEP-04.
"""

from typing import Callable

from jep.core.chain import AuditChain
from jep.recorder import record


def wrap_mcp_tool(
    tool_func: Callable, issuer: str = "mcp:agent", private_key=None
) -> Callable:
    """Wrap an MCP tool function with JEP-04 recording."""
    return record(
        tool_func, issuer=issuer, private_key=private_key, auto_verify=True
    )


class JEPMCPServer:
    """
    MCP server with full JEP integration.
    """

    def __init__(
        self, server_name: str, issuer: str = "mcp:server", private_key=None
    ):
        self.server_name = server_name
        self.chain = AuditChain(
            issuer=issuer,
            private_key=private_key,
            storage_path=f"{server_name}_jep_chain.jsonl",
        )

    def register(self, tool_func: Callable) -> Callable:
        """Register an MCP tool with JEP tracing."""
        wrapped = record(
            tool_func,
            issuer=self.chain.issuer,
            private_key=self.chain.private_key,
            chain=self.chain,
            auto_verify=True,
        )
        return wrapped

    def export_chain(self) -> list:
        """Return full audit chain."""
        return self.chain.events
