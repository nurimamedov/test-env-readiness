"""Measure end-to-end readiness from the host, not just container launch."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parent

def request(path):
    try:
        with urlopen("http://" + path, timeout=0.75) as response:
            return response.status, response.read(4096)
    except HTTPError as error:
        error.close()
        return error.code, b""
    except OSError:
        return 0, b""

def check_targets(*, app, registry):
    failures = []
    host, port = app.split(":")
    try:
        with closing(socket.create_connection((host, int(port)), timeout=0.75)):
            pass
    except OSError:
        failures.append("tcp")
    status, _ = request(f"{app}/ready")
    if status != 200:
        failures.append("http")
    status, body = request(f"{registry}/services")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        payload = None
    if status != 200 or not isinstance(payload, list) or "app" not in payload:
        failures.append("registration")
    return failures

def measure(mode):
    prefix = ["docker", "compose", "-p", f"readiness-{mode}-{uuid4().hex[:10]}",
              "-f", "compose.yml", "-f", f"compose.{mode}.yml"]
    def compose(*args, **kwargs):
        return subprocess.run(prefix + list(args), cwd=ROOT, text=True, **kwargs)
    started = time.monotonic()
    try:
        compose("up", "--detach", "--pull", "never", check=True, stdout=subprocess.DEVNULL,
                timeout=60)
        bindings = {
            service: compose("port", service, "8000", capture_output=True,
                             timeout=5, check=True).stdout.strip()
            for service in ("app", "registry")
        }
        if any(not address.startswith("127.0.0.1:") for address in bindings.values()):
            raise RuntimeError("Expected localhost-only published ports")
        last = []
        while time.monotonic() - started < 75:
            last = check_targets(**bindings)
            if not last:
                elapsed = round(time.monotonic() - started, 3)
                return {"mode": mode, "elapsed_seconds": elapsed, "checks": ["tcp","http","registration"]}
            time.sleep(0.2)
        raise TimeoutError(f"No ready sample; failed checks: {last}")
    finally:
        stopped_with_error = sys.exc_info()[0] is not None
        try:
            compose("down", "--timeout", "2", "--volumes", "--remove-orphans",
                    timeout=30, check=True,
                    stdout=subprocess.DEVNULL)
        except (OSError, subprocess.SubprocessError) as cleanup_error:
            if not stopped_with_error:
                raise
            print(f"Compose cleanup also failed for {prefix[3]}: {cleanup_error}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["cold","fast","both"], default="both")
    args = parser.parse_args()
    modes = ("cold", "fast") if args.mode == "both" else (args.mode,)
    print(json.dumps([measure(mode) for mode in modes], indent=2))

if __name__ == "__main__":
    main()
