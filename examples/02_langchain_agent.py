"""
Example 2: LangChain — TRUE zero-code integration.
Just import jep.adapters.langchain.auto and run your existing code.
"""

import jep.adapters.langchain.auto  # <-- ONE LINE. That's it.

# Your EXISTING LangChain code — zero changes needed
class FakeAgent:
    def run(self, query: str) -> str:
        return f"Answer for: {query}"

agent = FakeAgent()
result = agent.run("What is the weather?")
print(f"Result: {result}")

print("✓ LangChain auto-tracing active. All AgentExecutor runs emit JEP events.")
