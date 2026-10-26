#!/usr/bin/env python3
"""Behavior-first oracle for Module 10 local AI identity, boundary, and leak protections."""

from __future__ import annotations

import hashlib
import http.server
import json
import os
import shutil
import socket
import subprocess
import re
import tempfile
import threading
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS: list[str] = []
FAIL: list[str] = []



def check(cid: str, condition: bool, detail: str) -> None:
    (PASS if condition else FAIL).append(f"{cid}: {detail}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def make_workspace(tmp: str | Path, model_bytes: bytes | None = None, card_digest: str | None = None, card_size: int | None = None, control_enabled: bool = True) -> tuple[Path, Path]:
    """Build a disposable mirror of the shipped layout. Never touches the repo."""
    root = Path(tmp) / "w"
    root.mkdir(parents=True, exist_ok=False)
    (root / "scripts").mkdir()
    (root / "shared/case").mkdir(parents=True)
    (root / "shared/controls").mkdir(parents=True)
    shutil.copy(ROOT / "scripts/local_ai.py", root / "scripts/local_ai.py")
    shutil.copy(ROOT / "scripts/check_package.py", root / "scripts/check_package.py")
    for name in ("model-card.json", "SERVICE_RULES.md", "task.json", "hostile-note.md"):
        shutil.copy(ROOT / f"shared/case/{name}", root / f"shared/case/{name}")
    shutil.copy(ROOT / "shared/controls/run.json", root / "shared/controls/run.json")
    (root / "shared/controls/run.json").write_text(json.dumps({"enabled": control_enabled}) + "\n", encoding="utf-8")
    if model_bytes is not None:
        (root / "weights").mkdir()
        (root / "weights/w.gguf").write_bytes(model_bytes)
        card = json.loads((ROOT / "shared/case/model-card.json").read_text(encoding="utf-8"))
        card["weight_bytes"] = card_size if card_size is not None else len(model_bytes)
        card["weight_sha256"] = card_digest if card_digest is not None else hashlib.sha256(model_bytes).hexdigest()
        (root / "shared/case/model-card.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    return root, root / "scripts/local_ai.py"


def run_adapter(workspace: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(workspace / "scripts/local_ai.py"), *args],
        capture_output=True, text=True, cwd=str(workspace),
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class StubServer:
    """A minimal loopback service that answers /health like the real server."""

    def __init__(self, port: int) -> None:
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"ok"}')
                else:
                    self.send_response(404)
                    self.end_headers()
            def log_message(self, *args: object) -> None:
                return
        self.server = http.server.HTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()


# Source integrity (immutable staff reference)
ref = ROOT / "reference/REFERENCE.md"
hash_file = ROOT / "reference/REFERENCE.sha256"
expected_hash = read(hash_file).split()[0] if hash_file.exists() else ""
actual_hash = hashlib.sha256(ref.read_bytes()).hexdigest() if ref.exists() else ""
check("M10-REF", bool(expected_hash) and expected_hash == actual_hash, f"reference hash {actual_hash}")


rargs = subprocess.run([sys.executable, str(ROOT / "scripts/check_package.py")], capture_output=True, text=True, cwd=str(ROOT))
check("M10-CHK-ARGS", rargs.returncode == 1, "checker requires package argument")

rmiss = subprocess.run([sys.executable, str(ROOT / "scripts/check_package.py"), str(ROOT / "no-such-package.md")], capture_output=True, text=True, cwd=str(ROOT))
check("M10-CHK-MISSING", rmiss.returncode == 1, "checker rejects missing package")

# Package structure and path confinement on a disposable copy
with tempfile.TemporaryDirectory() as package_temp:
    package_root = Path(package_temp) / "received kit with spaces"
    shutil.copytree(ROOT / "shared", package_root / "shared")
    shutil.copytree(ROOT / "scripts", package_root / "scripts")
    package_path = package_root / "shared/PACKAGE.md"
    original = package_path.read_text(encoding="utf-8")

    def package_run(text: str) -> subprocess.CompletedProcess:
        package_path.write_text(text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(package_root / "scripts/check_package.py"), str(package_path)],
            cwd=package_temp, capture_output=True, text=True,
        )

    check("M10-PACKAGE-STRUCTURE", package_run(original).returncode == 0, "received package resolves its own dependencies from an unrelated cwd")
    check("M10-PACKAGE-STRUCTURE", package_run("").returncode == 1, "empty package cannot pass")
    no_restore = re.sub(r"^## Restore\n.*?(?=^## |\Z)", "", original, flags=re.M | re.S)
    check("M10-PACKAGE-STRUCTURE", package_run(no_restore).returncode == 1, "missing restore field holds")
    empty_bounds = re.sub(r"(^## Bounds\n).*?(?=^## |\Z)", r"\1\n", original, flags=re.M | re.S)
    check("M10-PACKAGE-STRUCTURE", package_run(empty_bounds).returncode == 1, "empty operating bounds hold")
    dependency = package_root / "shared/case/model-card.json"
    dependency.unlink()
    check("M10-PACKAGE-PATH", package_run(original).returncode == 1, "missing identity-card dependency holds")
    shutil.copyfile(ROOT / "shared/case/model-card.json", dependency)
    escaped = original.replace("shared/case/model-card.json", "shared/../../outside.json")
    (Path(package_temp) / "outside.json").write_text("outside package\n", encoding="utf-8")
    check("M10-PACKAGE-PATH", package_run(escaped).returncode == 1, "an existing path outside the received kit holds")
    package_path.write_bytes(b"\xff")
    unreadable = subprocess.run(
        [sys.executable, str(package_root / "scripts/check_package.py"), str(package_path)],
        cwd=package_temp, capture_output=True, text=True,
    )
    check("M10-PACKAGE-STRUCTURE", unreadable.returncode == 1 and "Traceback" not in unreadable.stderr, "invalid text receives a readable HOLD rather than a traceback")

# Adapter behavior on disposable copies only
with tempfile.TemporaryDirectory() as tmp:
    weights = os.urandom(4096)
    workspace, _ = make_workspace(tmp, model_bytes=weights)
    control = "shared/controls/run.json"

    # verify: matching fixture passes; wrong digest refuses
    r = run_adapter(workspace, "verify", "--model", "weights/w.gguf", "--control", control)
    check("M10-BEHAV-VERIFY", r.returncode == 0 and "PASS: pinned weight identity verified" in r.stdout, "verified fixture passes")
    tampered = bytearray(weights)
    tampered[0] ^= 0xFF
    (workspace / "weights/w.gguf").write_bytes(bytes(tampered))
    r_bad = run_adapter(workspace, "verify", "--model", "weights/w.gguf", "--control", control)
    check("M10-BEHAV-VERIFY", r_bad.returncode == 1 and "does not match pinned identity" in r_bad.stderr, "tampered weights refuse with a named reason")
    (workspace / "weights/w.gguf").write_bytes(weights[:-1])
    r_short = run_adapter(workspace, "verify", "--model", "weights/w.gguf", "--control", control)
    check("M10-BEHAV-VERIFY", r_short.returncode == 1 and "does not match pinned" in r_short.stderr, "wrong-size weights refuse")
    (workspace / "weights/w.gguf").write_bytes(weights)
    (workspace / "weights/link.gguf").symlink_to(workspace / "weights/w.gguf")
    r_link = run_adapter(workspace, "verify", "--model", "weights/link.gguf", "--control", control)
    check("M10-BEHAV-VERIFY", r_link.returncode == 1, "symlinked weights refuse")

    # wire: deterministic loopback overlay; overwrite refused; port floor enforced; no .tmp leftovers
    port = free_port()
    r_wire = run_adapter(workspace, "wire", "--port", str(port), "--control", control, "--work-dir", ".")
    check("M10-BEHAV-WIRE", r_wire.returncode == 0 and f"127.0.0.1:{port}" in r_wire.stdout, "wire emits the loopback service")
    overlay = (workspace / "omp-local.yml").read_text(encoding="utf-8")
    launch = json.loads((workspace / "omp-launch.json").read_text(encoding="utf-8"))
    check("M10-BEHAV-LOOPBACK", "0.0.0.0" not in overlay and "127.0.0.1" in overlay, "overlay binds loopback only")
    check("M10-BEHAV-LOOPBACK", launch["base_url"].startswith("http://127.0.0.1"), "launch records a loopback base url")
    r_rewire = run_adapter(workspace, "wire", "--port", str(port), "--control", control, "--work-dir", ".")
    check("M10-BEHAV-EXISTS", r_rewire.returncode == 2 and "output exists" in r_rewire.stderr, "rewiring an existing output refuses")
    r_priv = run_adapter(workspace, "wire", "--port", "80", "--control", control, "--work-dir", "fresh2")
    check("M10-BEHAV-WIRE", r_priv.returncode == 2 and "port" in r_priv.stderr, "privileged port refuses")
    leftovers = [p.name for p in (workspace).rglob("*.tmp")]
    check("M10-BEHAV-ATOMIC", not leftovers, "no temp files remain")

    # disabled control: every adapter command refuses
    (workspace / "shared/controls/run.json").write_text('{"enabled": false}\n', encoding="utf-8")
    r_off_probe = run_adapter(workspace, "probe", "--port", str(port), "--control", control)
    check("M10-BEHAV-DISABLE", r_off_probe.returncode == 1 and "control disabled" in r_off_probe.stderr, "probe refuses under a disabled control")
    r_off_verify = run_adapter(workspace, "verify", "--model", "weights/w.gguf", "--control", control)
    check("M10-BEHAV-DISABLE", r_off_verify.returncode == 1 and "control disabled" in r_off_verify.stderr, "verify refuses under a disabled control")
    r_off_wire = run_adapter(workspace, "wire", "--port", str(free_port()), "--control", control, "--work-dir", "fresh3")
    check("M10-BEHAV-DISABLE", r_off_wire.returncode == 1 and "control disabled" in r_off_wire.stderr and not (workspace / "fresh3").exists(), "wire refuses and writes nothing under a disabled control")
    r_off_stop = run_adapter(workspace, "stop", "--port", str(port), "--control", control, "--receipt", "stop-receipt.json")
    check("M10-BEHAV-DISABLE", r_off_stop.returncode == 1 and "control disabled" in r_off_stop.stderr, "stop refuses under a disabled control")
    (workspace / "shared/controls/run.json").write_text('{"enabled": true}\n', encoding="utf-8")

    # malformed inputs: exit 2, no output created
    (workspace / "shared/case/model-card.json").write_text("{not json", encoding="utf-8")
    r_malformed = run_adapter(workspace, "verify", "--model", "weights/w.gguf", "--control", control)
    check("M10-BEHAV-MALFORMED", r_malformed.returncode == 2, "malformed identity card exits 2")
    shutil.copy(ROOT / "shared/case/model-card.json", workspace / "shared/case/model-card.json")

    # probe: live stub passes; dead port holds; the stub is loopback-only
    stub_port = free_port()
    stub = StubServer(stub_port)
    stub.start()
    try:
        r_live = run_adapter(workspace, "probe", "--port", str(stub_port), "--control", control)
        check("M10-BEHAV-PROBE", r_live.returncode == 0 and "reachable on loopback" in r_live.stdout, "probe passes against a live loopback service")
    finally:
        stub.stop()
    r_dead = run_adapter(workspace, "probe", "--port", str(free_port()), "--control", control)
    check("M10-BEHAV-PROBE", r_dead.returncode == 1 and "not reachable" in r_dead.stderr, "probe holds on a dead port")

    # stop: valid receipt plus dead port passes; live service holds; wrong receipt refuses
    stop_port = free_port()
    receipt = {"action": "stop", "port": stop_port, "stopped_by": "operator"}
    (workspace / "stop-receipt.json").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    r_stop = run_adapter(workspace, "stop", "--port", str(stop_port), "--control", control, "--receipt", "stop-receipt.json")
    check("M10-BEHAV-STOP", r_stop.returncode == 0 and "stopped and unreachable" in r_stop.stdout, "stop passes with a valid receipt on a dead port")
    stub2 = StubServer(stop_port)
    stub2.start()
    try:
        r_stop_live = run_adapter(workspace, "stop", "--port", str(stop_port), "--control", control, "--receipt", "stop-receipt.json")
        check("M10-BEHAV-STOP", r_stop_live.returncode == 1 and "still reachable" in r_stop_live.stderr, "stop holds while the service is still up")
    finally:
        stub2.stop()
    wrong = {"action": "stop", "port": stop_port + 1, "stopped_by": "operator"}
    (workspace / "wrong-receipt.json").write_text(json.dumps(wrong) + "\n", encoding="utf-8")
    r_wrong = run_adapter(workspace, "stop", "--port", str(stop_port), "--control", control, "--receipt", "wrong-receipt.json")
    check("M10-BEHAV-STOP", r_wrong.returncode == 1, "a receipt naming another port refuses")
    leftovers = [p.name for p in workspace.rglob("*.tmp")]
    check("M10-BEHAV-ATOMIC", not leftovers, "no temp files remain after the stop cycle")

    # fresh-location determinism: wire bytes are identical across fresh directories
    port_b = free_port()
    r_wire_b = run_adapter(workspace, "wire", "--port", str(port_b), "--control", control, "--work-dir", "determinism")
    check("M10-BEHAV-WIRE", r_wire_b.returncode == 0, "second wire run succeeds")
    first = (workspace / "omp-launch.json").read_bytes()
    second = (workspace / "determinism/omp-launch.json").read_bytes()
    first_overlay = (workspace / "omp-local.yml").read_bytes()
    second_overlay = (workspace / "determinism/omp-local.yml").read_bytes()
    def normalize(payload: bytes, port: str) -> bytes:
        payload = payload.replace(port.encode(), b"PORT")
        return payload.replace(b"determinism/omp-local.yml", b"omp-local.yml").replace(b"determinism/omp-launch.json", b"omp-launch.json")
    same = normalize(first, str(port)) == normalize(second, str(port_b))
    same_overlay = normalize(first_overlay, str(port)) == normalize(second_overlay, str(port_b))
    check("M10-BEHAV-FRESH", same and same_overlay, "wire outputs are identical modulo the port argument")

print(f"PASS {len(PASS)}")
for item in PASS:
    print("  PASS", item)
print(f"FAIL {len(FAIL)}")
for item in FAIL:
    print("  FAIL", item)
sys.exit(1 if FAIL else 0)
