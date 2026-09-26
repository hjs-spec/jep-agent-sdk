"""JEP Agent CLI for Core 0.7 event archives."""

from __future__ import annotations

import json
from html import escape

import click
from rich.console import Console
from rich.table import Table

from jep_agent.core.event import parse_json

console = Console()

CHAIN_EXTENSION = "jep-agent.chain"


def _read_events(file):
    events = []
    with open(file, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = parse_json(line)
            except ValueError as exc:
                raise click.ClickException(f"Invalid JSON on line {number}") from exc
            if not isinstance(event, dict):
                raise click.ClickException(f"Event on line {number} must be an object")
            events.append(event)
    return events


def _identity_key(event):
    return json.dumps(
        [event.get("who"), event.get("id")], ensure_ascii=False, separators=(",", ":")
    )


def _ref_key(ref):
    if (
        isinstance(ref, dict)
        and ref.get("type") == "jep:event"
        and isinstance(ref.get("value"), dict)
    ):
        value = ref["value"]
        if isinstance(value.get("who"), str) and isinstance(value.get("id"), str):
            return _identity_key(value)
    return None


@click.group()
def cli():
    """JEP-Agent SDK CLI v2.1 / JEP Core 0.7."""
    pass


@cli.command()
@click.option("--port", default=8080, help="Web viewer port")
@click.option("--host", default="127.0.0.1", help="Bind host")
@click.option("--reload", is_flag=True, help="Auto-reload")
def web(port, host, reload):
    from jep_agent.web.server import start_server

    console.print(f"[bold green]JEP Event Viewer[/bold green] http://{host}:{port}")
    start_server(host=host, port=port, reload=reload)


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--public-key", type=click.Path(exists=True), help="Ed25519 public key PEM")
@click.option("--aud", help="Expected audience")
def verify(file, public_key, aud):
    """Verify Core 0.7 signatures and report companion chain integrity."""
    from cryptography.hazmat.primitives import serialization

    from jep_agent.core.chain import AuditChain
    from jep_agent.core.verifier import JEPVerifier

    public = None
    if public_key:
        with open(public_key, "rb") as handle:
            public = serialization.load_pem_public_key(handle.read())

    events = _read_events(file)
    if not events:
        raise click.ClickException("No events to verify")

    verifier = JEPVerifier()
    table = Table(title="JEP Core 0.7 Verification Results")
    table.add_column("Verb", style="cyan")
    table.add_column("Event ID", style="dim")
    table.add_column("Status", style="bold")

    invalid = 0
    for event in events:
        result = verifier.verify_result(
            event,
            public_key=public,
            mode="archival",
            expected_aud=aud,
        )
        status = result["status"]
        if status == "valid":
            color = "green"
        elif status == "indeterminate":
            color = "yellow"
        else:
            color = "red"
        table.add_row(
            str(event.get("verb", "?")),
            str(event.get("id", "?"))[:24],
            f"[{color}]{status}[/{color}]",
        )
        if status != "valid":
            invalid += 1
            for error in result["errors"]:
                console.print(f"{error['code']}: {error['message']}", markup=False)

    chain_links = sum(
        1
        for event in events
        if isinstance(event.get("ext"), dict)
        and isinstance(event["ext"].get(CHAIN_EXTENSION), dict)
    )
    if chain_links:
        chain = AuditChain(issuer=str(events[0].get("who", "agent")))
        chain.events = events
        if not chain.verify_chain(public_key=public):
            invalid += 1
            console.print("[red]Companion audit-chain verification failed[/red]")

    console.print(table)
    console.print(f"[bold]Events: {len(events)} | Invalid/indeterminate: {invalid}[/bold]")
    if invalid:
        raise click.exceptions.Exit(1)


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="Output HTML path")
@click.option("--title", default="JEP Audit Report", help="Report title")
def export(file, output, title):
    events = _read_events(file)
    with open(output, "w", encoding="utf-8") as handle:
        handle.write(_generate_full_report(events, title))
    console.print(f"[green]Report exported: {output} ({len(events)} events)[/green]")


def _generate_full_report(events, title):
    from jep_agent.core.event import event_hash

    title_text = str(title)
    nodes = []
    links = []
    identities = {}

    for index, event in enumerate(events):
        key = _identity_key(event)
        identities[key] = index
        nodes.append(
            {
                "id": key,
                "event_hash": event_hash(event),
                "verb": event.get("verb"),
                "who": event.get("who"),
                "event_id": event.get("id"),
                "when": event.get("when"),
                "what": str(event.get("what", ""))[:120],
                "sig": bool(event.get("sig")),
            }
        )

    for index, event in enumerate(events):
        ref_key = _ref_key(event.get("ref"))
        if ref_key in identities:
            links.append(
                {
                    "source": identities[ref_key],
                    "target": index,
                    "type": "ref",
                }
            )

        chain = (event.get("ext") or {}).get(CHAIN_EXTENSION)
        if isinstance(chain, dict) and isinstance(chain.get("previous"), dict):
            previous = chain["previous"]
            prev_key = _identity_key(previous)
            if prev_key in identities:
                links.append(
                    {
                        "source": identities[prev_key],
                        "target": index,
                        "type": "chain",
                    }
                )

    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f"<td>{escape(str(event.get('verb', '?')))}</td>"
            f"<td>{escape(str(event.get('who', '')))}</td>"
            f"<td>{escape(str(event.get('id', '')))}</td>"
            f"<td>{escape(str(event.get('when', '')))}</td>"
            f"<td>{escape(str(event.get('what', ''))[:80])}</td>"
            f"<td>{escape(str(event.get('ref', '')))}</td>"
            f"<td>{'yes' if event.get('sig') else 'no'}</td>"
            "</tr>"
        )

    data = json.dumps(
        {"nodes": nodes, "links": links},
        ensure_ascii=False,
    )
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    style = (
        "body{font-family:system-ui;margin:32px;max-width:1200px}"
        "table{width:100%;border-collapse:collapse}"
        "td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}"
        "code{font-size:12px}"
    )
    signed = sum(1 for event in events if event.get("sig"))
    header = (
        "JEP-Agent SDK 2.1 / JEP Core 0.7. "
        "Event Identity is <code>(who,id)</code>; "
        "Event Hash identifies the exact signed artifact."
    )
    columns = (
        "<tr><th>Verb</th><th>Who</th><th>Event ID</th>"
        "<th>When</th><th>What</th><th>Ref</th><th>Signed</th></tr>"
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(title_text)}</title><style>{style}</style></head>"
        f"<body><h1>{escape(title_text)}</h1><p>{header}</p>"
        f"<p>Events: {len(events)} · Signed (unverified): {signed} · "
        f"Companion links: {len(links)}</p>"
        f"<table>{columns}{''.join(rows)}</table>"
        f"<script>const graph = {data};</script></body></html>"
    )
