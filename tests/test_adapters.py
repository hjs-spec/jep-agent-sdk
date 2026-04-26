"""Test suite for JEP-Agent SDK."""

import pytest

from jep.adapters.mcp import JEPMCPServer


def test_mcp_server():
    server = JEPMCPServer("test-server")

    @server.register
    def add(a: int, b: int) -> int:
        return a + b

    result = add(2, 3)
    assert result == 5
    assert len(server.export_chain()) == 2  # J + V


def test_mcp_error_termination():
    server = JEPMCPServer("test-server")

    @server.register
    def fail():
        raise ValueError("oops")

    with pytest.raises(ValueError):
        fail()

    events = server.export_chain()
    assert events[-1]["verb"] == "T"
