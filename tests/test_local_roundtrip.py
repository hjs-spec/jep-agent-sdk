"""The README local path works across processes and fails closed on tampering."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/local_roundtrip.py"


def run(command, directory):
    return subprocess.run(
        [sys.executable, str(EXAMPLE), command, str(directory)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_independent_process_verification_and_tamper_rejection(tmp_path):
    directory = tmp_path / "evidence"
    made = run("create", directory)
    assert made.returncode == 0, made.stderr
    assert json.loads(made.stdout)["private_key_saved"] is False
    assert {p.name for p in directory.iterdir()} == {"event.json", "keys.json", "public-key.pem"}
    verified = run("verify", directory)
    assert verified.returncode == 0, verified.stderr
    result = json.loads(verified.stdout)
    assert result["status"] == "valid"
    assert result["checks"]["cryptographic"] == "pass"
    assert result["checks"]["actor_binding"] == "not_checked"
    assert result["event_hash"] == json.loads(made.stdout)["event_hash"]
    original_bytes = (directory / "event.json").read_bytes()
    assert run("create", directory).returncode != 0
    assert (directory / "event.json").read_bytes() == original_bytes
    event = json.loads(original_bytes)
    event["what"]["claim"] = "modified after signing"
    (directory / "event.json").write_text(json.dumps(event), encoding="utf-8")
    tampered = run("verify", directory)
    assert tampered.returncode == 1
    assert json.loads(tampered.stdout)["status"] == "invalid"


def test_missing_public_key_does_not_claim_success(tmp_path):
    directory = tmp_path / "evidence"
    assert run("create", directory).returncode == 0
    (directory / "public-key.pem").unlink()
    result = run("verify", directory)
    assert result.returncode == 2
    assert "Example failed" in result.stderr


def test_documented_core_validator_command_works(tmp_path):
    directory = tmp_path / "evidence"
    assert run("create", directory).returncode == 0

    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    assert (
        "jep-validate validate ./local-evidence/event.json --keys "
        "./local-evidence/keys.json"
        in readme
    )

    command = shutil.which("jep-validate")
    assert command is not None
    verified = subprocess.run(
        [
            command,
            "validate",
            str(directory / "event.json"),
            "--keys",
            str(directory / "keys.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    result = json.loads(verified.stdout)
    assert result["status"] == "valid"
    assert result["checks"]["cryptographic"] == "pass"
