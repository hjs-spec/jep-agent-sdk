"""Legacy OpenAI Chat Completions instrumentation for JEP Core 0.7.

The current Agents SDK uses the separate middleware.
"""

import sys

from jep_agent.core.chain import AuditChain
from jep_agent.core.event import event_identity_ref
from jep_agent.primitives import judge, verify


class _OpenAIJEPTracer:
    def __init__(self, issuer: str = "openai:agent", private_key=None):
        self.chain = AuditChain(issuer=issuer, private_key=private_key)

    def trace_run(self, original_run):
        from jep_agent.recorder import record

        return record(original_run, issuer=self.chain.issuer, chain=self.chain)


def auto_patch():
    """Patch synchronous Chat Completions and expose collected events through trace."""
    try:
        import openai
    except ImportError:
        return

    if not hasattr(openai.resources.chat.completions.Completions, "create"):
        return

    original = openai.resources.chat.completions.Completions.create
    if getattr(original, "_jep_instrumented", False):
        return

    def _traced_create(self, *args, **kwargs):
        from jep_agent.recorder import trace

        if not trace.enabled or trace.chain is None:
            trace.enable(issuer="openai:chat")

        tracer = _OpenAIJEPTracer(issuer=trace.chain.issuer)
        tracer.chain = trace.chain
        start_event = tracer.chain.append(
            judge(
                who=tracer.chain.issuer,
                what={
                    "claim": "chat_completion",
                    "model": kwargs.get("model"),
                    "messages_count": len(kwargs.get("messages", [])),
                },
            )
        )
        run_ref = event_identity_ref(start_event)

        status = "error:interrupted"
        result_content = {"error": status}
        try:
            result = original(self, *args, **kwargs)
            status = "success"
            result_content = {"completion": str(result)[:300]}
        except BaseException as exc:
            result = None
            status = f"error:{type(exc).__name__}"
            result_content = {"error": str(exc)}
            raise
        finally:
            tracer.chain.append(
                verify(
                    who=tracer.chain.issuer,
                    ref=run_ref,
                    verification_scope=["execution_result"],
                    result={"status": status, **result_content},
                )
            )

        return result

    _traced_create._jep_instrumented = True
    openai.resources.chat.completions.Completions.create = _traced_create


def wrap_agent(agent_instance, issuer: str = "openai:agent", private_key=None):
    """Wrap a specific legacy agent instance."""
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
