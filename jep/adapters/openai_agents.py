"""
Legacy OpenAI Chat Completions instrumentation; current Agents SDK uses the separate middleware.
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
        from jep.recorder import record

        return record(original_run, issuer=self.chain.issuer, chain=self.chain)


def auto_patch():
    """Patch synchronous Chat Completions; collected events are exposed through trace."""
    try:
        import openai
    except ImportError:
        return

    if hasattr(openai.resources.chat.completions.Completions, "create"):
        _orig = openai.resources.chat.completions.Completions.create
        if getattr(_orig, "_jep_instrumented", False):
            return

        def _traced_create(self, *args, **kwargs):
            from jep.recorder import trace

            if not trace.enabled or trace.chain is None:
                trace.enable(issuer="openai:chat")
            tracer = _OpenAIJEPTracer(issuer=trace.chain.issuer)
            tracer.chain = trace.chain
            content = {
                "type": "chat_completion",
                "model": kwargs.get("model"),
                "messages_count": len(kwargs.get("messages", [])),
            }
            j_ev = judge(who=tracer.chain.issuer, content=content)
            tracer.chain.append(j_ev)

            status = "error:interrupted"
            result_content = {"error": status}
            try:
                result = _orig(self, *args, **kwargs)
                status = "success"
                result_content = {"completion": str(result)[:300]}
            except BaseException as e:
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

        _traced_create._jep_instrumented = True
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
