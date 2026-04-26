#!/usr/bin/env python3
import sys

print("========== JEP-Agent SDK 1.0 全面运行验证 ==========")

# 1. 基础导入
print("\n[1/6] 基础导入...")
from jep import judge, verify, trace, DeterminabilityGuard
from jep.core.chain import AuditChain
print("✓ 核心模块导入成功")

# 2. 生成真实 JEP 事件
print("\n[2/6] 生成 JEP 事件...")
ev1 = judge(who="agent-A", what="task-1")
ev2 = verify(who="agent-B", what="task-1", ref=ev1["nonce"])
chain = AuditChain()
chain.append(ev1)
chain.append(ev2)
chain.save("demo_events.jsonl")
print("✓ 生成 2 个签名事件")

# 3. 链结构验证
print("\n[3/6] 链结构验证...")
assert ev1["nonce"] != ev2["nonce"]
assert ev2["ref"] == ev1["nonce"]
print("✓ 链式引用关联正确 (ref -> nonce)")

# 4. 重新加载验证
print("\n[4/6] 重新加载验证...")
loaded = AuditChain("demo_events.jsonl")
events = list(loaded)
assert len(events) == 2
print(f"✓ 加载 {len(events)} 个事件")

# 5. 运行时门控
print("\n[5/6] 运行时门控...")
guard = DeterminabilityGuard(
    evidence_fn=lambda ctx: len(ctx.get("tools_used", [])),
    target_fn=lambda ctx: ctx.get("ok", "ok"),
    knowledge_base=[
        {"tools_used": ["a", "b"], "ok": "ok"},
        {"tools_used": ["a"], "ok": 0},
    ],
    on_insufficient="raise",
)

@guard.require_determinable
def my_agent(tools_used):
    return "ok"

try:
    my_agent(["a", "b"])
    print("✓ 门控放行（知识库匹配）")
except RuntimeError:
    print("✗ 门控误拦截"); sys.exit(1)

try:
    my_agent(["a"])
    print("✗ 门控未拦截异常输入"); sys.exit(1)
except RuntimeError:
    print("✓ 门控正确拦截异常输入")

# 6. 密码学验证
print("\n[6/6] 密码学验证...")
from jep.core.verifier import JEPVerifier
v = JEPVerifier()
for ev in events:
    result = v.verify(ev)
    assert result == "VALID", f"验证失败: {result}"
print("✓ 所有事件密码学验证通过")

print("\n========== 全部验证完成，SDK 可用 ==========")
