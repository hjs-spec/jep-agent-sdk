#!/bin/bash
rm -f demo_events.jsonl demo_report.html

echo "========== JEP-Agent SDK 1.0 全面运行验证 =========="

# 1. 基础导入
echo -e "\n[1/6] 基础导入..."
python3 -c "from jep import judge, verify, trace, DeterminabilityGuard; print('✓ 核心模块导入成功')"

# 2. 生成真实 JEP 事件（注意：judge/verify 已内置 verb，不可重复传入）
echo -e "\n[2/6] 生成 JEP 事件..."
python3 << 'PYEOF'
from jep import judge, verify, AuditChain
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

key = Ed25519PrivateKey.generate()
ev1 = judge(who="agent-A", what="task-1", signer=key)
ev2 = verify(who="agent-B", what="task-1", signer=key, parent=ev1["hash"])
chain = AuditChain()
chain.append(ev1)
chain.append(ev2)
chain.save("demo_events.jsonl")
print("✓ 生成 2 个签名事件，保存到 demo_events.jsonl")
PYEOF

# 3. CLI 验证
echo -e "\n[3/6] CLI 验证..."
jep verify demo_events.jsonl

# 4. 导出合规报告（Python 直接生成，不依赖 CLI 子命令）
echo -e "\n[4/6] 导出合规报告..."
python3 << 'PYEOF'
from jep import AuditChain
chain = AuditChain.load("demo_events.jsonl")
events = chain.events if hasattr(chain, 'events') else list(chain)
html = "<html><body><h1>JEP Audit Report</h1><table border='1'>"
html += "<tr><th>Verb</th><th>Who</th><th>When</th><th>Hash</th></tr>"
for ev in events:
    html += f"<tr><td>{ev.get('verb','')}</td><td>{ev.get('who','')}</td><td>{ev.get('when','')}</td><td>{ev.get('hash','')[:16]}...</td></tr>"
html += "</table></body></html>"
with open("demo_report.html", "w") as f:
    f.write(html)
print("✓ 报告导出成功: demo_report.html")
PYEOF

# 5. Web 服务
echo -e "\n[5/6] Web 服务..."
timeout 5 jep web --port 8080 &
sleep 2
curl -s http://127.0.0.1:8080 > /dev/null && echo "✓ Web 服务响应正常" || echo "✗ Web 服务未响应"

# 6. 运行时门控
echo -e "\n[6/6] 运行时门控..."
python3 << 'PYEOF'
from jep.determinability import DeterminabilityGuard

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
    print("✗ 门控误拦截")

try:
    my_agent(["a"])
    print("✗ 门控未拦截异常输入")
except RuntimeError:
    print("✓ 门控正确拦截异常输入")
PYEOF

echo -e "\n========== 全部验证完成 =========="
