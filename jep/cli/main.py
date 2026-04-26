"""
JEP CLI — jep web, jep verify, jep export (causal report)
"""

import json

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """JEP-Agent SDK CLI v1.0"""
    pass


@cli.command()
@click.option("--port", default=8080, help="Web viewer port")
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--reload", is_flag=True, help="Auto-reload")
def web(port, host, reload):
    """Launch the causal web viewer."""
    from jep.web.server import start_server

    console.print(f"[bold green]JEP Causal Viewer[/bold green] http://{host}:{port}")
    start_server(host=host, port=port, reload=reload)


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--public-key", type=click.Path(exists=True), help="Ed25519 public key PEM")
@click.option("--aud", help="Expected audience")
def verify(file, public_key, aud):
    """Verify JEP events (signature, chain, replay)."""
    from cryptography.hazmat.primitives import serialization

    from jep.core.verifier import JEPVerifier

    verifier = JEPVerifier()
    pk = None
    if public_key:
        with open(public_key, "rb") as f:
            pk = serialization.load_pem_public_key(f.read())

    events = []
    with open(file, "r") as f:
        events = [json.loads(line) for line in f if line.strip()]

    table = Table(title="JEP Verification Results")
    table.add_column("Verb", style="cyan")
    table.add_column("Nonce", style="dim")
    table.add_column("Result", style="bold")

    valid = 0
    invalid = 0
    for ev in events:
        result = verifier.verify(ev, public_key=pk, expected_aud=aud)
        color = "green" if result == "VALID" else "yellow" if "FAULT" in result else "red"
        table.add_row(
            ev.get("verb", "?"),
            ev["nonce"][:8],
            f"[{color}]{result}[/{color}]",
        )
        if result == "VALID":
            valid += 1
        else:
            invalid += 1

    console.print(table)
    console.print(
        f"[bold]Events: {len(events)} | Valid: {valid} | Invalid: {invalid}[/bold]"  # noqa: E501
    )


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="Output HTML path")
@click.option("--title", default="JEP Audit Report", help="Report title")
def export(file, output, title):
    """Export a full causal audit report (HTML with embedded graph)."""
    events = []
    with open(file, "r") as f:
        events = [json.loads(line) for line in f if line.strip()]

    html = _generate_full_report(events, title)
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    console.print(f"[green]Report exported: {output} ({len(events)} events)[/green]")


def _generate_full_report(events, title):
    nodes_data = [
        {
            "id": e.get("event_id", i),
            "verb": e.get("verb"),
            "who": e.get("who"),
            "when": e.get("when"),
            "what": str(e.get("what", ""))[:80],
            "nonce": e.get("nonce"),
            "ref": e.get("ref"),
            "task_based_on": e.get("task_based_on"),
            "sig": bool(e.get("sig")),
        }
        for i, e in enumerate(events)
    ]

    total = len(events)
    signed = sum(1 for e in events if e.get("sig"))
    chains = len(set(e.get("ref") for e in events if e.get("ref")))
    cross = sum(1 for e in events if e.get("task_based_on"))

    rows = []
    for e in events:
        verb = e.get("verb", "?")
        who = e.get("who", "")
        when = e.get("when", "")
        what = str(e.get("what", ""))[:60]
        ref = str(e.get("ref", ""))[:20]
        signed_mark = "✓" if e.get("sig") else "—"
        rows.append(
            f"<tr>"
            f"<td><span class='badge badge-{verb}'>{verb}</span></td>"
            f"<td>{who}</td><td>{when}</td>"
            f"<td class='mono'>{what}</td>"
            f"<td class='mono'>{ref}</td>"
            f"<td>{signed_mark}</td>"
            f"</tr>"
        )

    html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        '<meta charset="UTF-8">\n'
        f"<title>{title}</title>\n"
        "<style>\n"
        "body{font-family:system-ui,-apple-system,sans-serif;"
        "background:#0b0f19;color:#e2e8f0;margin:0;}\n"
        ".header{padding:32px;border-bottom:1px solid #1e293b;}\n"
        ".header h1{margin:0;font-size:24px;}\n"
        ".header p{margin:8px 0 0;color:#64748b;font-size:14px;}\n"
        ".stats{display:grid;grid-template-columns:repeat(4,1fr);"
        "gap:16px;padding:24px 32px;}\n"
        ".card{background:#0f172a;border:1px solid #1e293b;"
        "border-radius:8px;padding:20px;}\n"
        ".card .label{font-size:11px;color:#64748b;"
        "text-transform:uppercase;letter-spacing:0.05em;"
        "margin-bottom:8px;}\n"
        ".card .value{font-size:32px;font-weight:700;color:#f8fafc;}\n"
        ".section{padding:0 32px 32px;}\n"
        ".section h2{font-size:16px;margin-bottom:16px;color:#94a3b8;}\n"
        "table{width:100%;border-collapse:collapse;font-size:13px;}\n"
        "th{text-align:left;padding:10px;background:#0f172a;"
        "color:#94a3b8;border-bottom:1px solid #334155;}\n"
        "td{padding:10px;border-bottom:1px solid #1e293b;"
        "word-break:break-all;}\n"
        "td.mono{font-family:monospace;font-size:11px;color:#cbd5e1;}\n"
        ".badge{display:inline-block;padding:2px 8px;"
        "border-radius:4px;font-size:11px;font-weight:600;}\n"
        ".badge-J{background:#dbeafe;color:#1e40af;}\n"
        ".badge-D{background:#fef3c7;color:#92400e;}\n"
        ".badge-T{background:#fee2e2;color:#991b1b;}\n"
        ".badge-V{background:#dcfce7;color:#166534;}\n"
        "#graph{width:100%;height:500px;background:#0b0f19;"
        "border:1px solid #1e293b;border-radius:8px;"
        "margin-bottom:32px;}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="header"><h1>'
        f"{title}</h1><p>Generated by JEP-Agent SDK v1.0 | {total} events"
        "</p></div>\n"
        '<div class="stats">\n'
        f'<div class="card"><div class="label">Total Events</div>'
        f'<div class="value">{total}</div></div>\n'
        f'<div class="card"><div class="label">Signed</div>'
        f'<div class="value">{signed}</div></div>\n'
        f'<div class="card"><div class="label">Chains</div>'
        f'<div class="value">{chains}</div></div>\n'
        f'<div class="card"><div class="label">Cross-Agent</div>'
        f'<div class="value">{cross}</div></div>\n'
        "</div>\n"
        '<div class="section">\n'
        "<h2>Causal Topology</h2>\n"
        '<svg id="graph"></svg>\n'
        "</div>\n"
        '<div class="section">\n'
        "<h2>Event Log</h2>\n"
        "<table>\n"
        "<tr><th>Verb</th><th>Who</th><th>When</th>"
        "<th>What</th><th>Ref</th><th>Signed</th></tr>\n" + "".join(rows) + "</table>\n"
        "</div>\n"
        "<script>\n"
        f"const nodes = {json.dumps(nodes_data)};\n"
        "const links = [];\n"
        "const nodeMap = new Map();\n"
        "nodes.forEach((n,i) => nodeMap.set(n.id, i));\n"
        "nodes.forEach((n,i) => {\n"
        "  if(n.ref && nodeMap.has(n.ref)) "
        "links.push({source:nodeMap.get(n.ref), target:i, type:'ref'});\n"
        "  if(n.task_based_on && nodeMap.has(n.task_based_on)) "
        "links.push({source:nodeMap.get(n.task_based_on), target:i, type:'task'});\n"  # noqa: E501
        "});\n"
        "const svg = document.getElementById('graph');\n"
        "const width = svg.clientWidth || 800;\n"
        "const height = 500;\n"
        "svg.setAttribute('viewBox', `0 0 ${width} ${height}`);\n"
        "const colors = {J:'#60a5fa', D:'#fbbf24', T:'#f87171', V:'#34d399'};\n"
        "for(let iter=0; iter<200; iter++) {\n"
        "  for(let i=0;i<nodes.length;i++) {\n"
        "    for(let j=i+1;j<nodes.length;j++) {\n"
        "      const dx=nodes[j].x-nodes[i].x;\n"
        "      const dy=nodes[j].y-nodes[i].y;\n"
        "      const dist=Math.sqrt(dx*dx+dy*dy)||1;\n"
        "      const f=3000/(dist*dist);\n"
        "      const fx=(dx/dist)*f;\n"
        "      nodes[i].vx=(nodes[i].vx||0)-fx;\n"
        "      nodes[i].vy=(nodes[i].vy||0)-(dy/dist)*f;\n"
        "      nodes[j].vx=(nodes[j].vx||0)+fx;\n"
        "      nodes[j].vy=(nodes[j].vy||0)+(dy/dist)*f;\n"
        "    }\n"
        "  }\n"
        "  links.forEach(l => {\n"
        "    const dx=nodes[l.target].x-nodes[l.source].x;\n"
        "    const dy=nodes[l.target].y-nodes[l.source].y;\n"
        "    const dist=Math.sqrt(dx*dx+dy*dy)||1;\n"
        "    const f=(dist-100)*0.03;\n"
        "    nodes[l.source].vx+=(dx/dist)*f;\n"
        "    nodes[l.source].vy+=(dy/dist)*f;\n"
        "    nodes[l.target].vx-=(dx/dist)*f;\n"
        "    nodes[l.target].vy-=(dy/dist)*f;\n"
        "  });\n"
        "  nodes.forEach(n => {\n"
        "    n.vx=(n.vx||0)+(width/2-n.x)*0.003;\n"
        "    n.vy=(n.vy||0)+(height/2-n.y)*0.003;\n"
        "    n.x+=n.vx; n.y+=n.vy; n.vx*=0.5; n.vy*=0.5;\n"
        "    if(!n.x) n.x=width/2+(Math.random()-0.5)*300;\n"
        "    if(!n.y) n.y=height/2+(Math.random()-0.5)*300;\n"
        "  });\n"
        "}\n"
        "links.forEach(l => {\n"
        "  const line=document.createElementNS("
        "'http://www.w3.org/2000/svg','line');\n"
        "  line.setAttribute('x1',nodes[l.source].x);\n"
        "  line.setAttribute('y1',nodes[l.source].y);\n"
        "  line.setAttribute('x2',nodes[l.target].x);\n"
        "  line.setAttribute('y2',nodes[l.target].y);\n"
        "  line.setAttribute('stroke',l.type==='task'?'#a78bfa':'#475569');\n"
        "  line.setAttribute('stroke-width',l.type==='task'?2:1);\n"
        "  line.setAttribute('stroke-dasharray',"
        "l.type==='task'?'4,4':'none');\n"
        "  svg.appendChild(line);\n"
        "});\n"
        "nodes.forEach(n => {\n"
        "  const c=document.createElementNS("
        "'http://www.w3.org/2000/svg','circle');\n"
        "  c.setAttribute('cx',n.x); c.setAttribute('cy',n.y);\n"
        "  c.setAttribute('r',n.task_based_on?12:8);\n"
        "  c.setAttribute('fill',colors[n.verb]||'#94a3b8');\n"
        "  c.setAttribute('stroke',n.task_based_on?'#a78bfa':'#0b0f19');\n"
        "  c.setAttribute('stroke-width',n.task_based_on?2:1);\n"
        "  svg.appendChild(c);\n"
        "});\n"
        "</script>\n"
        "</body>\n"
        "</html>"
    )

    return html
