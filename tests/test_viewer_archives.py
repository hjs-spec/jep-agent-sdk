import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from jep_agent.cli.main import _generate_full_report
from jep_agent.core.event import build_event, event_hash
from jep_agent.web.server import app


@pytest.mark.parametrize(
    "data,detail",
    [
        (b'{"id":"first","id":"second"}\n', "line 1"),
        (b'{"what":{"claim":1,"\\u0063laim":2}}\n', "line 1"),
        (b"\nnot-json\n", "line 2"),
        (b"[]\n", "line 1"),
        (b'{"value":NaN}\n', "line 1"),
        (b'{"value":1e400}\n', "line 1"),
        (b'{"value":9007199254740993}\n', "line 1"),
        (b'{"value":"\\ud800"}\n', "line 1"),
        (b"\xff", "UTF-8"),
        (b"\n \n", "No events"),
    ],
)
def test_upload_rejects_ambiguous_or_invalid_json(data, detail):
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post("/api/upload", files={"file": ("events.jsonl", data)})
    assert result.status_code == 400
    assert detail in result.json()["detail"]


def test_upload_preserves_events_without_claiming_verification():
    event = build_event(
        "J",
        "agent",
        {"claim": "display", "number": 1000000000000000100, "unicode": "a\u2028b\u0085c😀"},
    )
    data = "\n" + json.dumps(event, ensure_ascii=False) + "\n\n"
    with TestClient(app) as client:
        result = client.post("/api/upload", files={"file": ("events.jsonl", data)})
    assert result.status_code == 200
    assert result.json() == {"count": 1, "events": [event]}


def reference_events():
    original = build_event("J", "agent", {"claim": "first", "text": "</script><img src=x>"})
    other = copy.deepcopy(original)
    other["what"]["claim"] = "conflicting artifact"
    ref = {
        "type": "jep:event",
        "value": {"who": original["who"], "id": original["id"]},
    }
    child = build_event("J", "agent", {"claim": "child"}, ref=ref)
    return original, other, child


@pytest.mark.parametrize("pin", ["missing", "wrong", "exact", "digest", "chain-wrong"])
def test_cli_report_only_links_resolved_artifacts(pin):
    original, other, child = reference_events()
    if pin in ("wrong", "exact"):
        child["ref"]["hash"] = event_hash(original) if pin == "exact" else "sha256:" + "0" * 64
    elif pin == "digest":
        child["ref"] = event_hash(original)
    elif pin == "chain-wrong":
        child.pop("ref")
        child["ext"] = {
            "jep-agent.chain": {
                "previous": {"who": original["who"], "id": original["id"]},
                "artifact_hash": "sha256:" + "0" * 64,
            }
        }
    report = _generate_full_report([original, other, child], "Audit")
    graph = json.loads(re.search(r"const graph = (.*);", report).group(1))
    expected = [{"source": 0, "target": 2, "type": "ref"}] if pin in ("exact", "digest") else []
    assert graph["links"] == expected


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required for viewer runtime test")
def test_viewer_strict_import_links_and_portable_report():
    viewer = Path(__file__).resolve().parents[1] / "jep_agent/web/static/index.html"
    html = viewer.read_text()
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    original, other, child = reference_events()
    child["ref"]["hash"] = event_hash(original)
    events = [original, other, child]
    harness = r"""
const vm = require('node:vm'), fs = require('node:fs');
const {webcrypto} = require('node:crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
function create(saved = '') {
    const elements = new Map(), handlers = {};
    function element() {
        return {children: [], style: {}, clientWidth: 800, clientHeight: 600,
            classList: {add() {}, remove() {}}, addEventListener() {}, setAttribute() {},
            appendChild(child) {this.children.push(child)}, textContent: '',
            set innerHTML(value) {this.children = []}};
    }
    const context = {crypto: webcrypto, TextEncoder, console,
        alert(message) {throw Error(message)},
        window: {addEventListener() {}},
        document: {addEventListener(name, fn) {handlers[name] = fn},
            createElementNS() {return element()},
            getElementById(id) {
                if (!elements.has(id)) elements.set(id, element());
                return elements.get(id);
            }}};
    vm.createContext(context);
    vm.runInContext(input.script, context);
    context.document.getElementById('embeddedArchive').textContent = saved;
    return {context, handlers, elements};
}
(async () => {
    const current = create();
    const bad = [
        '{"id":1,"id":2}', '{"what":{"claim":1,"\\u0063laim":2}}',
        '{"value":9007199254740993}', '{"value":1000000000000000101}',
        '{"value":1e400}', '{"value":"\\ud800"}'
    ];
    for (const text of bad) {
        let failed = false;
        try {current.context.parseArchiveJSON(text)} catch {failed = true}
        if (!failed) throw Error('Ambiguous JSON accepted: ' + text);
    }
    for (const text of [
        '{"a":[{"k":1},{"k":2}],"value":1000000000000000100}',
        '{"value":1000000000000000128,"a":[true,false,null,"a\\\\\\"b"]}'
    ]) current.context.parseArchiveJSON(text);
    await current.context.setEvents(input.events);
    const count = () => vm.runInContext('links.length', current.context);
    if (count() !== 1) throw Error('Exact pin did not select the earlier artifact');
    const conflicting = structuredClone(input.events);
    delete conflicting[2].ref.hash;
    await current.context.setEvents(conflicting);
    if (count() !== 0) throw Error('Ambiguous identity was linked');
    conflicting[2].ref.hash = 'sha256:' + '0'.repeat(64);
    await current.context.setEvents(conflicting);
    if (count() !== 0) throw Error('Wrong artifact hash was linked');
    await current.context.setEvents(input.events);
    const report = current.context.reportHTML(input.html, input.events);
    const slot = /<script id="embeddedArchive" type="application\/json">([\s\S]*?)<\/script>/;
    const saved = report.match(slot)[1];
    if (saved.includes('<') || saved.includes('&')) throw Error('Unsafe embedded JSON');
    const reopened = create(saved);
    await reopened.handlers.DOMContentLoaded();
    const restored = vm.runInContext(
        '({events, hashes: eventHashes, links: links.length})', reopened.context);
    reopened.context.resetZoom();
    if (vm.runInContext('nodes.length', reopened.context) !== input.events.length) {
        throw Error('Reset lost archive');
    }
    process.stdout.write(JSON.stringify(restored));
})().catch(error => {console.error(error); process.exitCode = 1});
"""
    process = subprocess.run(
        [shutil.which("node"), "-e", harness],
        input=json.dumps({"html": html, "script": script, "events": events}),
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(process.stdout)
    assert result == {
        "events": events,
        "hashes": [event_hash(event) for event in events],
        "links": 1,
    }
