"""Check installed wheels in both orders, including uninstall independence.

Usage: python scripts/check_coexistence.py AGENT.whl [CURRENT_SDK.whl]
Uses temporary environments and loopback-free imports/CLI help only.
"""

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def run(args, cwd):
    result = subprocess.run(
        [str(a) for a in args], cwd=cwd, capture_output=True, text=True, timeout=180
    )
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent_wheel", type=Path)
    parser.add_argument("sdk", nargs="?", default="jep-sdk-py==0.6.1")
    args = parser.parse_args()
    agent = str(args.agent_wheel.resolve())
    sdk = str(Path(args.sdk).resolve()) if Path(args.sdk).exists() else args.sdk
    for order in [(agent, sdk), (sdk, agent)]:
        with tempfile.TemporaryDirectory(prefix="jep-coexist-") as directory:
            root = Path(directory)
            venv.create(root / "env", with_pip=True)
            bin_dir = root / "env" / ("Scripts" if os.name == "nt" else "bin")
            python = bin_dir / "python"
            for package in [*order, "jep-cli==0.6.1"]:
                run([python, "-m", "pip", "install", package], root)
            run(
                [
                    python,
                    "-c",
                    """from importlib.metadata import distribution
from jep import JEPClient
from jep_agent import AuditChain, judge
from jep_agent.core.event import sign_event, verify_event_signature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
key = Ed25519PrivateKey.generate()
event = sign_event(judge(who="test", content={"test":True}), key)
assert verify_event_signature(event, key.public_key())
names = ["jep-sdk-py", "jep-agent-sdk", "jep-cli"]
files = []
for name in names:
    package = distribution(name)
    files.append({str(package.locate_file(p).resolve()) for p in package.files})
for i, owned in enumerate(files):
    for other in files[i+1:]:
        assert not owned & other, owned & other
""",
                ],
                root,
            )
            run([bin_dir / "jep", "--help"], root)
            run([bin_dir / "jep-agent", "--help"], root)
            removed = "jep-agent-sdk" if order[0] == agent else "jep-sdk-py"
            run([python, "-m", "pip", "uninstall", "-y", removed], root)
            check = (
                "from jep import JEPClient"
                if removed == "jep-agent-sdk"
                else "from jep_agent import AuditChain, judge"
            )
            run([python, "-c", check], root)
            run([bin_dir / "jep", "--help"], root)
            if removed != "jep-agent-sdk":
                run([bin_dir / "jep-agent", "--help"], root)
    print("Both install orders and independent uninstalls passed; legacy signatures verified.")


if __name__ == "__main__":
    main()
