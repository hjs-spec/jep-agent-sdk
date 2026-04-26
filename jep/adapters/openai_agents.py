"""
OpenAI Agents SDK integration — TRUE zero-code.
Usage:
    import jep.adapters.openai_agents.auto   # <-- All agent runs recorded automatically.
"""

import sys

from jep.core.chain import AuditChain
from jep.primitives import judge, terminate, verify


class _OpenAIJEPTracer:
    def __init__(self, issuer: str = "openai:agent", private_key=None):
        self.chain = AuditChain(issuer=issuer, private_key=private_key)

    def trace_run(self, original_run):
        def wrapper(*args, **kwargs):
            content = {
                "type": "agent_run",
                "args": repr(args),
                "kwargs": repr(kwargs),
            }
            j_ev = judge(who=self.chain.issuer, content=content)
            self.chain.append(j_ev)

            try:
                result = original_run(*args, **kwargs)
                status = "success"
                result_content = {"result": repr(result)[:500]}
            except Exception as e:
                result = None
                status = f"error:{type(e).__name__}"
                result_content = {"error": str(e)[:500]}
                raise
            finally:
                if status == "success":
                    v_ev = verify(who=self.chain.issuer, content=result_content)
                    self.chain.append(v_ev)
                else:
                    t_ev = terminate(who=self.chain.issuer, content=result_content)
                    self.chain.append(t_ev)

            return result

        wrapper._jep_chain = self.chain
        return wrapper


def auto_patch():
    """Globally patch OpenAI client to trace all agent completions."""
    try:
        import openai
    except ImportError:
        return

    if hasattr(openai.resources.chat.completions.Completions, "create"):
        _orig = openai.resources.chat.completions.Completions.create

        def _traced_create(self, *args, **kwargs):
            tracer = _OpenAIJEPTracer(issuer="openai:chat")
            content = {
                "type": "chat_completion",
                "model": kwargs.get("model"),
                "messages_count": len(kwargs.get("messages", [])),
            }
            j_ev = judge(who=tracer.chain.issuer, content=content)
            tracer.chain.append(j_ev)

            try:
                result = _orig(self, *args, **kwargs)
                status = "success"
                result_content = {"completion": str(result)[:300]}
            except Exception as e:
                result = None
                status = f"error:{type(e).__name__}"
                result_content = {"error": str(e)}
                raise
            finally:
                if status == "success":
                    v_ev = verify(who=tracer.chain.issuer, content=result_content)
                    tracer.chain.append(v_ev)
                else:
                    t_ev = terminate(who=tracer.chain.issuer, content=result_content)
                    tracer.chain.append(t_ev)

            return result

        openai.resources.chat.completions.Completions.create = _traced_create


def wrap_agent(agent_instance, issuer: str = "openai:agent", private_key=None):
    """Wrap a specific agent instance."""
    tracer = _OpenAIJEPTracer(issuer=issuer, private_key=private_key)
    original = getattr(agent_instance, "run", None) or getattr(agent_instance, "invoke", None)
    if not original:
        raise ValueError("Agent must have run() or invoke()")
    wrapped = tracer.trace_run(original)
    agent_instance.run = wrapped
    agent_instance.invoke = wrapped
    agent_instance._jep_chain = tracer.chain
    return agent_instance


class _AutoPatchModule:
    def __init__(self):
        auto_patch()


sys.modules[__name__ + ".auto"] = _AutoPatchModule()
