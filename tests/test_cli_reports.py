import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest
from click.testing import CliRunner
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.cli.main import _generate_full_report, cli
from jep_agent.core.chain import AuditChain
from jep_agent.core.event import build_event, event_hash, sign_event


@pytest.fixture
def signed_chain(tmp_path):
    key = Ed25519PrivateKey.generate()
    pem = tmp_path / "public.pem"
    pem.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    chain = AuditChain("agent", private_key=key)
    chain.append(build_event("J", "agent", what="sha256:" + "a" * 64))
    chain.append(build_event("J", "agent", what="sha256:" + "b" * 64))
    return key, pem, chain.export()


@pytest.mark.parametrize(
    "case", ["valid", "tamper", "broken-ref", "unsigned", "no-key", "empty", "missing-nonce"]
)
def test_cli_exit_code_and_reference_validation(case, signed_chain, tmp_path):
    key, pem, events = signed_chain
    if case == "tamper":
        events[0]["what"] = "sha256:" + "c" * 64
    elif case == "broken-ref":
        events[1]["ref"] = "sha256:" + "f" * 64
        sign_event(events[1], key)
    elif case == "unsigned":
        events[0]["sig"] = ""
    elif case == "empty":
        events = []
    elif case == "missing-nonce":
        del events[0]["nonce"]
    archive = tmp_path / "events.jsonl"
    archive.write_text("".join(json.dumps(event) + "\n" for event in events))
    args = ["verify", str(archive)]
    if case != "no-key":
        args += ["--public-key", str(pem)]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == (0 if case == "valid" else 1), result.output
    if case == "broken-ref":
        assert "reference not found" in result.output
    if case == "tamper":
        assert "signature verification failed" in result.output
    if case == "missing-nonce":
        assert "missing required field" in result.output


@pytest.mark.parametrize("content", ["[]\n", "not-json\n"])
def test_cli_rejects_malformed_archive(content, tmp_path):
    archive = tmp_path / "invalid.jsonl"
    archive.write_text(content)
    result = CliRunner().invoke(cli, ["verify", str(archive)])
    assert result.exit_code == 1
    assert "line 1" in result.output


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


@pytest.mark.parametrize("field", ["who", "what", "ref", "when", "verb", "title"])
def test_report_keeps_untrusted_markup_in_text(field):
    payload = '</script><script>window.injected=1</script><img src=x onerror="alert(1)">'
    event = build_event("J", "agent")
    title = "Audit"
    if field == "title":
        title = payload
    else:
        event[field] = payload
    html = _generate_full_report([event], title)
    parser = Tags()
    parser.feed(html)
    assert [tag for tag, _ in parser.tags].count("script") == 1
    assert all(tag != "img" for tag, _ in parser.tags)
    assert all(not any(name.startswith("on") for name in attrs) for _, attrs in parser.tags)
    assert "&lt;" in html
    data = json.loads(re.search(r"const nodes = (.*);", html).group(1))
    if field == "who":
        assert data[0]["who"] == payload


def test_export_links_use_legacy_unsigned_event_hash(signed_chain):
    _, _, events = signed_chain
    html = _generate_full_report(events, "Audit")
    nodes = json.loads(re.search(r"const nodes = (.*);", html).group(1))
    assert nodes[0]["id"] == event_hash(events[0]) == nodes[1]["ref"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js required for viewer runtime test")
def test_browser_hashes_match_sdk_and_render_real_links(signed_chain):
    key, _, _ = signed_chain
    chain = AuditChain("测试😀", private_key=key)
    chain.append(
        build_event(
            "J", "agent", extensions={"edge": {"𐀀": 1, "\ufffd": 2, "html": "<>&", "float": 1e-7}}
        )
    )
    chain.append(build_event("V", "agent"))
    events = chain.export()
    expected = [event_hash(event) for event in events]
    # Signature presence must never be described as verified by the viewer.
    events[0]["sig"] = "not-a-signature"
    viewer = Path(__file__).resolve().parents[1] / "jep_agent/web/static/index.html"
    html = viewer.read_text()
    assert "Signed (unverified)" in html
    assert 'id="statValid"' not in html
    script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
    harness = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const { webcrypto } = require('node:crypto');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = new Map();
function element() {
    return { children: [], style: {}, clientWidth: 800, clientHeight: 600,
        classList: { add() {}, remove() {} }, addEventListener() {}, setAttribute() {},
        appendChild(child) { this.children.push(child); }, textContent: '',
        set innerHTML(value) { this.children = []; } };
}
const context = { crypto: webcrypto, TextEncoder, console,
    window: { addEventListener() {} },
    document: { addEventListener() {}, createElementNS() { return element(); },
        getElementById(id) {
            if (!elements.has(id)) elements.set(id, element());
            return elements.get(id);
        } } };
vm.createContext(context);
vm.runInContext(input.script, context);
(async () => {
    await context.setEvents(input.events);
    const result = vm.runInContext('({ hashes: eventHashes, links: links.length })', context);
    result.signed = elements.get('statSigned').textContent;
    process.stdout.write(JSON.stringify(result));
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    process = subprocess.run(
        [shutil.which("node"), "-e", harness],
        input=json.dumps({"events": events, "script": script}),
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(process.stdout)
    assert result == {"hashes": expected, "links": 1, "signed": 2}
