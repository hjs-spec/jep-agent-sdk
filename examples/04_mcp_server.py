"""
Example 4: MCP server with JEP recording.
"""

from jep.adapters.mcp import JEPMCPServer


def read_file(path: str) -> str:
    return f"Contents of {path}"


def calculate(expression: str) -> float:
    return eval(expression)


def main():
    server = JEPMCPServer("my-mcp-server", issuer="did:example:mcp-server")
    
    server.register(read_file)
    server.register(calculate)
    
    read_file("data.txt")
    calculate("2 + 2")
    
    print(f"Events: {len(server.export_chain())}")
    for ev in server.export_chain():
        print(f"  {ev['verb']}: {ev.get('what', 'N/A')[:40]}...")


if __name__ == "__main__":
    main()
