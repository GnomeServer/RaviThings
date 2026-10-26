#!/usr/bin/env python3
"""Verify, wire, probe, and stop one local uncensored model service.

The adapter never downloads weights, never serves traffic, and never
exposes an interface beyond the loopback address. A community note is
context only; it cannot relax the loopback boundary or the identity check.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

USAGE = "usage: local_ai.py {verify|wire|probe|stop} --control <run.json> [--model PATH] [--port N] [--work-dir DIR] [--receipt R]"
CONTROL_KEYS = {"enabled"}
CARD_KEYS = {
    "model_id",
    "weight_file",
    "weight_bytes",
    "weight_sha256",
    "repo_pin",
    "hf_blob",
    "license",
    "base_model",
    "gated",
}
COMMANDS = ("verify", "wire", "probe", "stop")
LOOPBACK = "127.0.0.1"
BASE_MODEL_ID = "OrcaSAQ-2-27B-Uncensored"
CONTEXT_WINDOW = 32768
MAX_TOKENS = 4096


def finish(message: str, code: int) -> int:
    print(f"HOLD: {message}", file=sys.stderr)
    return code


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 22), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(path.name)
    return path.read_bytes()


def load_json_bytes(payload: bytes):
    if payload.startswith(b"\xef\xbb\xbf"):
        payload = payload[3:]
    text = payload.decode("utf-8")

    def _no_dup(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key in json")
            result[key] = value
        return result

    try:
        return json.loads(text, object_pairs_hook=_no_dup)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("malformed input") from error


def dump(document: dict) -> bytes:
    return (json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def read_control(path: Path) -> bool:
    payload = read_regular(path)
    try:
        data = load_json_bytes(payload)
    except ValueError as error:
        raise ValueError("malformed control") from error
    if not isinstance(data, dict) or set(data) != CONTROL_KEYS or not isinstance(data["enabled"], bool):
        raise ValueError("malformed control")
    return data["enabled"]


def parse_args(argv: list[str]) -> tuple[dict, int | None]:
    options: dict[str, str] = {}
    index = 1
    while index < len(argv):
        arg = argv[index]
        if arg in {"--control", "--model", "--port", "--work-dir", "--receipt"}:
            if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                return {}, finish("malformed invocation", 2)
            name = arg[2:]
            if name in options:
                return {}, finish("malformed invocation", 2)
            options[name] = argv[index + 1]
            index += 2
            continue
        if arg.startswith("-") or arg not in COMMANDS:
            print(USAGE, file=sys.stderr)
            return {}, finish("malformed invocation", 2)
        options["command"] = arg
        index += 1
    if "command" not in options or "control" not in options:
        print(USAGE, file=sys.stderr)
        return {}, finish("malformed invocation", 2)
    return options, None


def parse_port(value: str) -> int:
    if not value.isdigit() or value != str(int(value)):
        raise ValueError("malformed port")
    port = int(value)
    if not 1024 <= port <= 65535:
        raise ValueError("port outside the permitted range")
    return port


def exclusive_write(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError("output exists")
    if path.parent.is_symlink() or (path.parent.exists() and not path.parent.is_dir()):
        raise ValueError("malformed invocation")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    fd = os.open(tmp, flags, 0o644)
    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(fd, view[written:])
        os.fsync(fd)
    except Exception:
        os.close(fd)
        tmp.unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    try:
        os.link(tmp, path)
    except FileExistsError:
        tmp.unlink(missing_ok=True)
        raise FileExistsError("output exists")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.unlink(missing_ok=True)


def load_card(path: Path) -> dict:
    payload = read_regular(path)
    try:
        card = load_json_bytes(payload)
    except ValueError as error:
        raise ValueError("malformed model card") from error
    if not isinstance(card, dict) or set(card) != CARD_KEYS:
        raise ValueError("malformed model card")
    for field in ("model_id", "weight_file", "repo_pin", "hf_blob", "license", "base_model", "gated", "weight_sha256"):
        value = card[field]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError("malformed model card")
    if not isinstance(card["weight_bytes"], int) or isinstance(card["weight_bytes"], bool) or card["weight_bytes"] <= 0:
        raise ValueError("malformed model card")
    if card["weight_sha256"] != "PENDING_REAL_HASH" and (len(card["weight_sha256"]) != 64 or any(char not in "0123456789abcdef" for char in card["weight_sha256"])):
        raise ValueError("malformed model card")
    return card


def health_probe(port: int, timeout: float = 3.0) -> tuple[bool, str]:
    url = f"http://{LOOPBACK}:{port}/health"
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(4096).decode("utf-8", errors="replace")
            return True, body
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, socket.timeout):
        return False, ""


def main(argv: list[str]) -> int:
    options, error = parse_args(argv)
    if error is not None:
        return error
    command = options["command"]
    control_path = Path(options["control"])
    try:
        enabled = read_control(control_path)
    except FileNotFoundError:
        return finish("missing control", 2)
    except ValueError as error:
        return finish(str(error), 2)
    if not enabled:
        return finish("control disabled", 1)

    if command == "verify":
        if "model" not in options:
            print(USAGE, file=sys.stderr)
            return finish("malformed invocation", 2)
        model_path = Path(options["model"])
        try:
            card = load_card(Path("shared/case/model-card.json"))
        except FileNotFoundError:
            return finish("missing model card", 2)
        except ValueError as error:
            return finish(str(error), 2)
        try:
            payload = read_regular(model_path)
        except FileNotFoundError:
            return finish("model file is missing or is not a regular file", 1)
        actual_size = model_path.stat().st_size
        if actual_size != card["weight_bytes"]:
            return finish(f"weight size {actual_size} does not match pinned {card['weight_bytes']}", 1)
        actual_hash = sha256_file(model_path)
        if actual_hash != card["weight_sha256"]:
            return finish(f"weight digest {actual_hash} does not match pinned identity for {card['weight_file']}", 1)
        card_result = {
            "base_model": card["base_model"],
            "gated": card["gated"],
            "license": card["license"],
            "model_id": card["model_id"],
            "weight_file": card["weight_file"],
            "weight_sha256": actual_hash,
            "weight_size": actual_size,
        }
        print(json.dumps(card_result, ensure_ascii=True, indent=2, sort_keys=True))
        print("PASS: pinned weight identity verified")
        return 0

    if command == "wire":
        if "port" not in options or "work-dir" not in options:
            print(USAGE, file=sys.stderr)
            return finish("malformed invocation", 2)
        try:
            port = parse_port(options["port"])
        except ValueError as error:
            return finish(str(error), 2)
        work_dir = Path(options["work-dir"])
        overlay_path = work_dir / "omp-local.yml"
        launch_path = work_dir / "omp-launch.json"
        try:
            card = load_card(Path("shared/case/model-card.json"))
        except FileNotFoundError:
            return finish("missing model card", 2)
        except ValueError as error:
            return finish(str(error), 2)
        overlay = (
            "providers:\n"
            "  llama.cpp:\n"
            f"    baseUrl: http://{LOOPBACK}:{port}/v1\n"
            "    api: openai-completions\n"
            "    auth: none\n"
            "    models:\n"
            f"      - id: {card['weight_file'].removesuffix('.gguf')}\n"
            "        name: Local Uncensored 27B\n"
            "        reasoning: false\n"
            "        supportsTools: true\n"
            f"        contextWindow: {CONTEXT_WINDOW}\n"
            f"        maxTokens: {MAX_TOKENS}\n"
        )
        launch = {
            "argv": [
                "omp",
                "--model",
                f"llama.cpp/{BASE_MODEL_ID}",
                "--config",
                str(overlay_path),
                "--no-session",
                "--no-title",
                "--no-skills",
                "--no-rules",
                "--no-extensions",
                "--no-lsp",
                "--no-prewalk",
                "--mode",
                "json",
            ],
            "base_url": f"http://{LOOPBACK}:{port}/v1",
            "loopback_only": True,
        }
        try:
            exclusive_write(overlay_path, overlay.encode("utf-8"))
            exclusive_write(launch_path, dump(launch))
        except FileExistsError:
            return finish("output exists", 2)
        except (OSError, ValueError):
            return finish("malformed invocation", 2)
        print(f"WIRED loopback service at {LOOPBACK}:{port}")
        print("LOOPBACK-ONLY: no interface beyond 127.0.0.1 is authorized by this overlay")
        return 0

    if command == "probe":
        if "port" not in options:
            print(USAGE, file=sys.stderr)
            return finish("malformed invocation", 2)
        try:
            port = parse_port(options["port"])
        except ValueError as error:
            return finish(str(error), 2)
        reachable, body = health_probe(port)
        if not reachable or '"status":"ok"' not in body.replace(" ", ""):
            return finish(f"service is not reachable on {LOOPBACK}:{port}; bring-up is incomplete", 1)
        print(json.dumps({"loopback": LOOPBACK, "port": port, "status": "ok"}, ensure_ascii=True, sort_keys=True))
        print("PASS: local service reachable on loopback")
        return 0

    if command == "stop":
        if "port" not in options or "receipt" not in options:
            print(USAGE, file=sys.stderr)
            return finish("malformed invocation", 2)
        try:
            port = parse_port(options["port"])
        except ValueError as error:
            return finish(str(error), 2)
        receipt_path = Path(options["receipt"])
        try:
            receipt = load_json_bytes(read_regular(receipt_path))
        except FileNotFoundError:
            return finish("missing stop receipt", 2)
        except ValueError:
            return finish("malformed stop receipt", 2)
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"action", "port", "stopped_by"}
            or receipt.get("action") != "stop"
            or receipt.get("port") != port
            or not isinstance(receipt.get("stopped_by"), str)
            or not receipt["stopped_by"].strip()
        ):
            return finish("stop receipt does not name this port and a stopped service", 1)
        reachable, _ = health_probe(port)
        if reachable:
            return finish(f"service is still reachable on {LOOPBACK}:{port}; it is not stopped", 1)
        print(json.dumps({"loopback": LOOPBACK, "port": port, "stopped": True}, ensure_ascii=True, sort_keys=True))
        print("PASS: service is stopped and unreachable on loopback")
        return 0

    print(USAGE, file=sys.stderr)
    return finish("malformed invocation", 2)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
