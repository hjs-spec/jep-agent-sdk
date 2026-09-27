"""Create and independently reopen one signed event; no API or private-key file."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from jep_agent.core.event import build_event, event_hash, parse_json, sign_event
from jep_agent.core.verifier import JEPVerifier


def create(directory: Path) -> dict:
    # Never overwrite an existing example or a user's evidence archive.
    directory.mkdir(parents=True, exist_ok=False)
    key = Ed25519PrivateKey.generate()
    public = key.public_key()
    kid = "did:example:local-demo#temporary-key"
    event = sign_event(
        build_event("J", "did:example:local-demo", {"claim": "local demonstration"}),
        key,
        kid=kid,
    )
    raw = public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    keys = {
        kid: {
            "kty": "OKP",
            "crv": "Ed25519",
            "x": base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"),
        }
    }
    (directory / "event.json").write_text(json.dumps(event, indent=2) + "\n", encoding="utf-8")
    (directory / "keys.json").write_text(json.dumps(keys, indent=2) + "\n", encoding="utf-8")
    (directory / "public-key.pem").write_bytes(
        public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    return {"created": str(directory), "event_hash": event_hash(event), "private_key_saved": False}


def verify(directory: Path) -> dict:
    event = parse_json((directory / "event.json").read_text(encoding="utf-8"))
    public = serialization.load_pem_public_key((directory / "public-key.pem").read_bytes())
    return JEPVerifier().verify_result(event, public, mode="archival")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result = create(args.directory) if args.command == "create" else verify(args.directory)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Example failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return int(args.command == "verify" and result["status"] != "valid")


if __name__ == "__main__":
    raise SystemExit(main())
