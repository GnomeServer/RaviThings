#!/usr/bin/env python3
"""Observe local-model prerequisites; never install, authenticate, download or launch.

A clear preflight permits a staff rehearsal, not a claim that the model runs.
The 35 GiB policy applies before a new download. --before-launch reports current
storage without requiring another two weight allocations after verification.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess

from local_ai import CONTEXT_WINDOW, LOOPBACK, load_card

GIB = 1024 ** 3
DOWNLOAD_FREE_BYTES = 35 * GIB
PORT = 8080


def command_output(argv: list[str]) -> str:
    names = ("PATH", "HOME", "USERPROFILE", "SystemRoot", "SYSTEMROOT", "WINDIR", "PATHEXT", "TEMP", "TMP", "TMPDIR")
    environment = {name: os.environ[name] for name in names if name in os.environ}
    environment.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_UPDATE_CHECK="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1", NO_COLOR="1")
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, env=environment)
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode:
        raise ValueError(f"{Path(argv[0]).name} {' '.join(argv[1:])} exited {result.returncode}: {output}")
    if not output:
        raise ValueError(f"{Path(argv[0]).name} returned no version/help output")
    return output


def observe_tool(name: str, override: str | None) -> dict:
    executable = shutil.which(override or name)
    if not executable:
        raise ValueError(f"{name} not executable; device/support owner must provision the missing tool or supply its approved full path")
    executable = str(Path(executable).absolute())
    version = command_output([executable, "--version"])
    general_help = command_output([executable, "--help"])
    if name == "hf":
        help_text = command_output([executable, "download", "--help"])
        required = ("--revision", "--local-dir")
    else:
        help_text = general_help
        required = ("-m", "--host", "--port", "-c")
    missing = [flag for flag in required if not re.search(r"(?<![\w-])" + re.escape(flag) + r"(?![\w-])", help_text)]
    if missing:
        raise ValueError(f"{name} help lacks required flags: {', '.join(missing)}; staff must qualify this binary")
    return {"path": executable, "version": version, "help_sha256": hashlib.sha256(general_help.encode()).hexdigest(), "required_flags": list(required), "command_help_sha256": hashlib.sha256(help_text.encode()).hexdigest()}


def storage_destinations(work: Path, environment: dict[str, str]) -> dict[str, Path]:
    cache = Path(environment.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))).expanduser()
    home = Path(environment.get("HF_HOME", str(cache / "huggingface"))).expanduser()
    # The authored --local-dir weights route bypasses HF_HUB_CACHE. Its
    # download metadata is under weights/.cache; Xet has a separate cache.
    return {"work/weights": work / "weights", "HF Xet cache": Path(environment.get("HF_XET_CACHE", str(home / "xet"))).expanduser()}


def existing_volume_path(destination: Path) -> tuple[Path, Path]:
    resolved = destination.expanduser().resolve()
    current = resolved
    while not current.exists():
        if current == current.parent:
            raise ValueError(f"no accessible volume for {destination}")
        current = current.parent
    if not current.is_dir():
        raise ValueError(f"storage destination is not a directory: {current}")
    return resolved, current


def observe_storage(work: Path, environment: dict[str, str], before_launch: bool) -> list[dict]:
    rows = []
    for label, destination in storage_destinations(work, environment).items():
        resolved, existing = existing_volume_path(destination)
        free = shutil.disk_usage(existing).free
        rows.append({"destination": label, "path": str(resolved), "measured_at": str(existing), "device_id": existing.stat().st_dev, "free_bytes": free, "free_gib": round(free / GIB, 3), "required_free_bytes": None if before_launch else DOWNLOAD_FREE_BYTES, "status": "PASS" if before_launch or free >= DOWNLOAD_FREE_BYTES else "HOLD"})
    return rows


def memory_band(total_bytes: int) -> str:
    if total_bytes < 16 * GIB:
        return "HOLD"
    if total_bytes < 24 * GIB:
        return "CONDITIONAL"
    return "PLANNING_FLOOR_MET"


def observe_memory(owner_installed_bytes: int | None = None) -> dict:
    system = platform.system()
    installed = None
    installed_source = "unobserved; device-owner inventory required"
    if system == "Darwin":
        total = int(command_output(["/usr/sbin/sysctl", "-n", "hw.memsize"]))
        installed, installed_source = total, "sysctl hw.memsize"
        text = command_output(["/usr/bin/vm_stat"])
        page = re.search(r"page size of (\d+) bytes", text)
        fields = dict(re.findall(r"^(Pages (?:free|inactive|speculative)):\s+(\d+)\.", text, re.MULTILINE))
        if not page or len(fields) != 3:
            raise ValueError("cannot identify vm_stat page size/free/inactive/speculative counts")
        available = int(page[1]) * sum(map(int, fields.values()))
        method = "sysctl hw.memsize; available is vm_stat free+inactive+speculative estimate, not an allocation guarantee"
    elif system == "Linux":
        values = dict(re.findall(r"^(MemTotal|MemAvailable):\s+(\d+) kB$", Path("/proc/meminfo").read_text(), re.MULTILINE))
        if set(values) != {"MemTotal", "MemAvailable"}:
            raise ValueError("MemTotal/MemAvailable unavailable")
        total, available = int(values["MemTotal"]) * 1024, int(values["MemAvailable"]) * 1024
        method = "/proc/meminfo MemTotal/MemAvailable; report container/VM limits separately"
    elif system == "Windows":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [(name, ctypes.c_uint64) for name in ("total_phys", "avail_phys", "total_page", "avail_page", "total_virtual", "avail_virtual", "avail_extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        observe = kernel.GlobalMemoryStatusEx
        observe.argtypes = [ctypes.POINTER(MemoryStatus)]
        observe.restype = ctypes.c_int
        if not observe(ctypes.byref(status)):
            raise ctypes.WinError(ctypes.get_last_error())
        total, available = status.total_phys, status.avail_phys
        method = "GlobalMemoryStatusEx ullTotalPhys/ullAvailPhys"
        physical_kib = ctypes.c_uint64()
        physical = kernel.GetPhysicallyInstalledSystemMemory
        physical.argtypes = [ctypes.POINTER(ctypes.c_uint64)]
        physical.restype = ctypes.c_int
        if not physical(ctypes.byref(physical_kib)):
            raise ctypes.WinError(ctypes.get_last_error())
        installed, installed_source = physical_kib.value * 1024, "GetPhysicallyInstalledSystemMemory"
    else:
        raise ValueError(f"unsupported memory observation platform: {system}")
    if owner_installed_bytes is not None:
        if installed is not None and installed != owner_installed_bytes:
            raise ValueError("owner RAM record conflicts with the native installed-capacity observation")
        if installed is None:
            installed = owner_installed_bytes
            installed_source = "owner-supplied inventory (--installed-ram-gib); not measured by this check"
    if installed is not None and installed < total:
        raise ValueError("installed RAM record is smaller than OS-usable RAM; resolve the inventory")
    return {"installed_bytes": installed, "installed_gib": round(installed / GIB, 3) if installed is not None else None, "installed_source": installed_source,
            "total_bytes": total, "total_gib": round(total / GIB, 3), "available_bytes": available, "available_gib": round(available / GIB, 3),
            "method": method, "band": memory_band(installed) if installed is not None else "UNVERIFIED_PHYSICAL_CAPACITY"}


def require_free_endpoint(port: int = PORT) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            probe.bind((LOOPBACK, port))
        except OSError as error:
            raise ValueError(f"{LOOPBACK}:{port} is occupied or unavailable; leave the existing service untouched and contact its device/service owner") from error


def check(work: Path, hf: str | None = None, llama_server: str | None = None, before_launch: bool = False, owner_installed_bytes: int | None = None) -> dict:
    report = {"observed_at_utc": datetime.now(timezone.utc).isoformat(), "platform": platform.platform(), "architecture": platform.machine(), "stage": "before-launch" if before_launch else "before-download", "status": "HOLD", "holds": [], "tools": {}, "storage": [], "memory": None, "endpoint": f"{LOOPBACK}:{PORT}", "endpoint_free": False, "context": CONTEXT_WINDOW, "model": None, "full_rehearsal": "NOT_OBSERVED_BY_THIS_CHECK"}
    case = Path(__file__).resolve().parents[1] / "shared/case"
    try:
        card = load_card(case / "model-card.json")
        task = json.loads((case / "task.json").read_text(encoding="utf-8"))
        if not re.fullmatch(r"[0-9a-f]{64}", card["weight_sha256"]) or not re.fullmatch(r"[0-9a-f]{40}", card["repo_pin"]):
            raise ValueError("model card lacks a fixed digest/revision")
        if task["port"] != PORT or task["context"] != CONTEXT_WINDOW:
            raise ValueError("task differs from the declared endpoint/context; do not change the boundary")
        report["model"] = {key: card[key] for key in ("model_id", "weight_file", "weight_bytes", "weight_sha256", "repo_pin")}
    except (OSError, ValueError, KeyError) as error:
        report["holds"].append(f"identity: {error}")
    for name, override in (("hf", hf), ("llama-server", llama_server)):
        try:
            report["tools"][name] = observe_tool(name, override)
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            report["holds"].append(str(error))
    try:
        report["storage"] = observe_storage(work, os.environ, before_launch)
        for row in report["storage"]:
            if row["status"] == "HOLD":
                report["holds"].append(f"{row['destination']}: needs {DOWNLOAD_FREE_BYTES} bytes (35 GiB) free before a new download; ask device/support owner")
    except (OSError, ValueError) as error:
        report["holds"].append(f"storage: {error}")
    try:
        report["memory"] = observe_memory(owner_installed_bytes)
        if report["memory"]["band"] == "HOLD":
            report["holds"].append("physical RAM below 16 GiB: arrange an owner-approved qualified machine")
        elif report["memory"]["band"] == "UNVERIFIED_PHYSICAL_CAPACITY":
            report["holds"].append("Linux MemTotal is usable, not installed RAM. Obtain device-owner physical-capacity evidence and supply --installed-ram-gib; keep its source in the private readiness register")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        report["holds"].append(f"memory: {error}")
    try:
        require_free_endpoint()
        report["endpoint_free"] = True
    except ValueError as error:
        report["holds"].append(str(error))
    if not report["holds"]:
        report["status"] = "CONDITIONAL" if report["memory"]["band"] == "CONDITIONAL" else "READY_FOR_REHEARSAL"
    return report


def gib_capacity(value: str) -> int:
    try:
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0 or amount * GIB != (amount * GIB).to_integral_value():
            raise ValueError("capacity must be positive, finite and resolve to whole bytes")
        return int(amount * GIB)
    except (InvalidOperation, ValueError) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--hf", help="approved executable path; otherwise resolve hf from PATH")
    parser.add_argument("--llama-server", help="approved executable path; otherwise resolve llama-server from PATH")
    parser.add_argument("--before-launch", action="store_true", help="after verified download: report storage; repeat tool/RAM/free-endpoint checks")
    parser.add_argument("--installed-ram-gib", type=gib_capacity, dest="owner_installed_bytes", help="actual device-owner installed-RAM inventory on Linux, where MemTotal excludes reservations; never a guessed value")
    args = parser.parse_args()
    report = check(args.work_dir, args.hf, args.llama_server, args.before_launch, args.owner_installed_bytes)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("A preflight does not prove model operation. Record actual workload and complete the exact-model/context-32768 rehearsal on this machine. Any failed rehearsal requires an owner-approved qualified machine; a later preflight cannot erase it.")
    return 1 if report["status"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
