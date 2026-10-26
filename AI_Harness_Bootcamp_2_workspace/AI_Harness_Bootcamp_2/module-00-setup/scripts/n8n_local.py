#!/usr/bin/env python3
"""Staff prepare a local two-service n8n stack; use its recorded identity thereafter.

Python 3.12+. No installation, migration, credential printing, or Docker cleanup.
The CLI checks runtime configuration; browser, Code-node and persistence proof
must be observed separately on the actual machine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path

VERSION = "2.41.5"
COMPOSE = """services:
  n8n:
    image: n8nio/n8n:2.41.5
    environment:
      N8N_RUNNERS_MODE: external
      N8N_RUNNERS_BROKER_LISTEN_ADDRESS: 0.0.0.0
      N8N_RUNNERS_AUTH_TOKEN: ${N8N_RUNNERS_AUTH_TOKEN:?missing}
      N8N_DIAGNOSTICS_ENABLED: 'false'
      N8N_WEBHOOK_URL: http://localhost:${N8N_PORT:?missing}/
    ports:
      - '127.0.0.1:${N8N_PORT:?missing}:5678'
    volumes:
      - n8n_data:/home/node/.n8n
  runners:
    image: ghcr.io/n8n-io/runners:2.41.5
    environment:
      N8N_RUNNERS_TASK_BROKER_URI: http://n8n:5679
      N8N_RUNNERS_AUTH_TOKEN: ${N8N_RUNNERS_AUTH_TOKEN:?missing}
    depends_on:
      - n8n
volumes:
  n8n_data:
"""
PROJECT = re.compile(r"[a-z][a-z0-9_-]{2,40}\Z")
FILES = {"compose.yaml", ".env", ".course-n8n.json"}


def hold(reason: str) -> None:
    raise ValueError(reason)


def safe_directory(value: Path) -> Path:
    path = value.expanduser().absolute()
    if ".." in path.parts or str(path).startswith(("//", "\\\\")):
        hold("use a local directory without '..' or network-path components")
    for part in reversed((path, *path.parents)):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            hold(f"linked directory is not allowed: {part}")
        if part != path and part.exists() and not part.is_dir():
            hold(f"parent is not a directory: {part}")
        if (part / ".git").exists():
            hold("n8n private configuration must stay outside a checkout")
    return path


def private_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        hold(f"missing or linked configuration: {path.name}")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 16384:
        hold(f"unsafe configuration: {path.name}")
    if os.name != "nt" and path.name == ".env" and info.st_mode & 0o077:
        hold(".env must be accessible only to its owner")
    return path.read_bytes()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def overrides() -> None:
    conflict = sorted(k for k in os.environ if k.startswith(("DOCKER_", "COMPOSE_", "N8N_")))
    if conflict:
        hold("remove inherited Docker/Compose/n8n overrides: " + ", ".join(conflict))


def docker_binary() -> str:
    binary = shutil.which("docker.exe" if os.name == "nt" else "docker")
    if not binary:
        hold("Docker CLI is missing; ask the device owner to install approved Docker")
    return str(Path(binary).resolve())


def command(docker: str, *args: str, timeout: int = 60) -> str:
    try:
        result = subprocess.run([docker, *args], capture_output=True, text=True,
                                encoding="utf-8", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Docker command unavailable ({args[0]}); ask the device owner") from exc
    if result.returncode:
        # Docker/Compose diagnostics can contain interpolated secrets. Never echo them.
        hold(f"Docker command failed ({args[0]}); ask the device owner to inspect Docker privately")
    return result.stdout.strip()


def document(value: str, description: str):
    try:
        return json.loads(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid Docker {description} response") from exc


def engine(docker: str) -> dict:
    context = command(docker, "context", "show")
    details = document(command(docker, "context", "inspect", context), "context")
    if not isinstance(details, list) or len(details) != 1:
        hold("Docker context cannot be verified")
    host = details[0].get("Endpoints", {}).get("docker", {}).get("Host")
    if not isinstance(host, str) or not host.startswith(("unix:///", "npipe:////./pipe/")):
        hold("remote or unapproved Docker engine; use the device owner's local engine")
    if (os.name == "nt") != host.startswith("npipe:"):
        hold("Docker context does not match this shell's local engine")
    info = document(command(docker, "info", "--format", "{{json .}}"), "engine")
    if info.get("OSType", "").lower() != "linux" or not info.get("ID"):
        hold("a local Linux-container Docker engine is required")
    command(docker, "compose", "version")
    return {"docker": docker, "context": context, "host": host, "engine_id": info["ID"]}


def names(docker: str, kind: str) -> set[str]:
    if kind == "container":
        args = ("container", "ls", "-a", "--format", "{{.Names}}")
    else:
        args = (kind, "ls", "--format", "{{.Name}}")
    return set(command(docker, *args).splitlines()) - {""}


def project_ids(docker: str, kind: str, project: str) -> list[str]:
    args = ("container", "ls", "-a", "-q") if kind == "container" else (kind, "ls", "-q")
    return command(docker, *args, "--filter", f"label=com.docker.compose.project={project}").splitlines()


def resources(docker: str, project: str) -> tuple[list[dict], list[dict], list[dict]]:
    result = []
    for kind in ("container", "volume", "network"):
        ids = project_ids(docker, kind, project)
        items = document(command(docker, "inspect", f"--type={kind}", *ids), kind) if ids else []
        if not isinstance(items, list) or len(items) != len(ids):
            hold(f"cannot inspect all project {kind} resources")
        result.append(items)
    return result[0], result[1], result[2]


def collisions(docker: str, project: str) -> None:
    containers, volumes, networks = resources(docker, project)
    if containers or volumes or networks:
        hold("project already owns Docker resources; choose a fresh approved project")
    expected = {"container": {f"{project}-n8n-1", f"{project}-runners-1"},
                "volume": {f"{project}_n8n_data"}, "network": {f"{project}_default"}}
    for kind, targets in expected.items():
        if names(docker, kind) & targets:
            hold(f"reserved {kind} name is already in use; choose another project")


def free_port(port: int) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if os.name != "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))
    except OSError as exc:
        raise ValueError(f"127.0.0.1:{port} is occupied; preserve its owner") from exc


def create_file(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    if os.name != "nt":
        path.chmod(0o600)


def prepare(path: Path, project: str, port: int) -> None:
    if not PROJECT.fullmatch(project):
        hold("project must start with a lowercase letter and contain 3-41 lowercase letters, digits, '-' or '_'")
    if not 1024 <= port <= 65535:
        hold("port must be an unprivileged TCP port (1024-65535)")
    if path.exists() or path.is_symlink():
        hold("destination already exists; preserve it and choose a fresh directory")
    docker = docker_binary()
    identity = engine(docker)
    collisions(docker, project)
    free_port(port)
    token = secrets.token_hex(32)
    env = f"N8N_RUNNERS_AUTH_TOKEN={token}\nN8N_PORT={port}\n".encode()
    config = COMPOSE.encode()
    record = {"schema": "course-n8n-v1", "directory": str(path), "project": project,
              "port": port, **identity, "compose_sha256": sha(config), "env_sha256": sha(env)}
    path.mkdir(parents=True)  # An exclusive reservation; never replace an existing attempt.
    create_file(path / "compose.yaml", config)
    create_file(path / ".env", env)
    create_file(path / ".course-n8n.json", (json.dumps(record, indent=2) + "\n").encode())
    print(f"PREPARED: {path} (project {project}, browser http://localhost:{port}); staff start next")


def recorded(path: Path) -> tuple[dict, str]:
    if not path.is_dir():
        hold("prepared directory is missing; ask staff")
    if {p.name for p in path.iterdir()} != FILES:
        hold("prepared directory has missing or extra files; ask staff to review")
    raw = private_file(path / ".course-n8n.json")
    data = document(raw.decode("utf-8"), "identity")
    if not isinstance(data, dict) or set(data) != {"schema", "directory", "project", "port", "docker",
                                                "context", "host", "engine_id", "compose_sha256", "env_sha256"}:
        hold("prepared identity changed")
    if data["schema"] != "course-n8n-v1" or data["directory"] != str(path):
        hold("prepared identity does not match this directory")
    project, port = data["project"], data["port"]
    if not isinstance(project, str) or not PROJECT.fullmatch(project) or type(port) is not int or not 1024 <= port <= 65535:
        hold("prepared project or port is invalid")
    config, env = private_file(path / "compose.yaml"), private_file(path / ".env")
    if config != COMPOSE.encode() or sha(config) != data["compose_sha256"]:
        hold("reviewed Compose configuration changed; no automatic migration")
    if sha(env) != data["env_sha256"] or not re.fullmatch(
            rb"N8N_RUNNERS_AUTH_TOKEN=([0-9a-f]{64})\nN8N_PORT=" + str(port).encode() + rb"\n", env):
        hold("private runner token or port configuration changed")
    docker = docker_binary()
    if engine(docker) != {key: data[key] for key in ("docker", "context", "host", "engine_id")}:
        hold("Docker engine/context/CLI changed; ask the device owner")
    return data, env.decode().splitlines()[0].split("=", 1)[1]


def inspect_project(data: dict, token: str) -> tuple[list[dict], list[dict], list[dict]]:
    docker, project, port = data["docker"], data["project"], data["port"]
    containers, volumes, networks = resources(docker, project)
    allowed = {"n8n", "runners"}
    expected_names = {f"{project}-{service}-1" for service in allowed}
    if (names(docker, "container") & expected_names) != {c.get("Name", "").lstrip("/") for c in containers}:
        hold("project container name collision or changed project label")
    expected_volume, expected_network = f"{project}_n8n_data", f"{project}_default"
    for kind, target, found in (("volume", expected_volume, volumes), ("network", expected_network, networks)):
        if (target in names(docker, kind)) != any(obj.get("Name") == target for obj in found):
            hold(f"project {kind} name collision or changed label")
        if len(found) > 1 or (found and found[0].get("Name") != target):
            hold(f"unexpected project {kind}; ask staff")
    if volumes and (volumes[0].get("Driver") != "local" or
                    volumes[0].get("Labels", {}).get("com.docker.compose.volume") != "n8n_data"):
        hold("named data volume is not the reviewed Compose volume")
    if networks and networks[0].get("Labels", {}).get("com.docker.compose.network") != "default":
        hold("network does not match the reviewed Compose network")
    if len(containers) not in (0, 2):
        hold("partial project containers; staff must inspect without automatic cleanup")
    if containers and (not volumes or not networks):
        hold("project data volume or network is missing")
    if not containers and networks:
        hold("orphaned project network; staff must inspect")
    for item in containers:
        labels = item.get("Config", {}).get("Labels") or {}
        service = labels.get("com.docker.compose.service")
        if (service not in allowed or item.get("Name") != f"/{project}-{service}-1" or
                labels.get("com.docker.compose.project") != project or
                item.get("Config", {}).get("Image") !=
                ("n8nio/n8n:2.41.5" if service == "n8n" else "ghcr.io/n8n-io/runners:2.41.5")):
            hold("unexpected project service, image, or container identity")
        host = item.get("HostConfig") or {}
        mounts = item.get("Mounts") or []
        ports = host.get("PortBindings") or {}
        wanted = {"5678/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(port)}]} if service == "n8n" else {}
        if (host.get("Privileged") is not False or
                host.get("NetworkMode") != expected_network or ports != wanted):
            hold("service privilege, network or host-port configuration changed")
        if service == "n8n":
            if (len(mounts) != 1 or mounts[0].get("Type") != "volume" or
                    mounts[0].get("Name") != expected_volume or
                    mounts[0].get("Destination") != "/home/node/.n8n"):
                hold("n8n data mount differs from the recorded volume")
        elif mounts or host.get("Binds"):
            hold("runner must not mount host files or Docker sockets")
        env = item.get("Config", {}).get("Env") or []
        values = dict(field.split("=", 1) for field in env if isinstance(field, str) and "=" in field)
        wanted_env = ({"N8N_RUNNERS_MODE": "external", "N8N_RUNNERS_BROKER_LISTEN_ADDRESS": "0.0.0.0",
                       "N8N_RUNNERS_AUTH_TOKEN": token, "N8N_DIAGNOSTICS_ENABLED": "false",
                       "N8N_WEBHOOK_URL": f"http://localhost:{port}/"} if service == "n8n" else
                      {"N8N_RUNNERS_TASK_BROKER_URI": "http://n8n:5679", "N8N_RUNNERS_AUTH_TOKEN": token})
        if any(values.get(key) != value for key, value in wanted_env.items()):
            hold("runtime environment differs from the reviewed stack")
        if any(key.startswith(("N8N_INSTANCE_AI_", "N8N_SANDBOX_")) or key == "N8N_AI_ASSISTANT_BASE_URL"
               for key in values):
            hold("Assistant/sandbox configuration detected; staff review required")
        if service == "n8n" and item.get("State", {}).get("Status") == "running":
            actual = item.get("NetworkSettings", {}).get("Ports", {}).get("5678/tcp")
            if actual != wanted["5678/tcp"]:
                hold("n8n published editor address differs from 127.0.0.1")
    if len({c["Config"]["Labels"]["com.docker.compose.service"] for c in containers}) != len(containers):
        hold("duplicate project services")
    return containers, volumes, networks


def compose(data: dict, action: str) -> None:
    args = ("compose", "-p", data["project"], "--env-file", str(Path(data["directory"]) / ".env"),
            "-f", str(Path(data["directory"]) / "compose.yaml"), action)
    to = 300 if action == "up" else 60
    command(data["docker"], *args, *(["-d", "--no-build"] if action == "up" else []), timeout=to)


def lifecycle(action: str, path: Path) -> None:
    data, token = recorded(path)
    containers, volumes, _ = inspect_project(data, token)
    if action == "start":
        if containers and all(c.get("State", {}).get("Status") == "running" for c in containers):
            print(f"RUNNING: prepared instance already started at http://localhost:{data['port']}")
            return
        if any(c.get("State", {}).get("Status") not in {"running", "exited", "created"} for c in containers):
            hold("project has an unhealthy lifecycle state; ask staff to inspect")
        editor_running = any(c["Config"]["Labels"]["com.docker.compose.service"] == "n8n"
                             and c.get("State", {}).get("Status") == "running" for c in containers)
        if not editor_running:
            free_port(data["port"])
        compose(data, "up")
        containers, volumes, _ = inspect_project(data, token)
        if len(containers) != 2 or any(c.get("State", {}).get("Status") != "running" for c in containers):
            hold("start incomplete; preserve the attempt for staff inspection")
        print(f"STARTED: containers running; open http://localhost:{data['port']} and verify browser and Code node")
    elif action == "status":
        if len(containers) != 2 or any(c.get("State", {}).get("Status") != "running" for c in containers):
            hold("n8n and external runners are not both running; ask staff")
        print(f"RUNNING: n8n {VERSION} and external runners, editor bound to 127.0.0.1:{data['port']}; browser, Code-node execution and saved-workflow persistence still need real observation")
    else:
        if not containers:
            hold("no course containers to stop; named volume remains untouched")
        compose(data, "down")  # Deliberately no -v, --remove-orphans, image removal, or prune.
        remaining, kept, _ = inspect_project(data, token)
        if remaining or not kept:
            hold("stop incomplete or named data volume missing; staff inspect before restarting")
        print("STOPPED: course containers removed; named workflow data volume retained")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "start", "status", "stop"))
    parser.add_argument("--directory", type=Path, default=Path.home() / "n8n-course")
    parser.add_argument("--project", help="staff-only, unused Compose project (prepare only)")
    parser.add_argument("--port", type=int, default=None, help="staff-only browser port (prepare only; default 5678)")
    args = parser.parse_args()
    try:
        overrides()
        path = safe_directory(args.directory)
        if args.action == "prepare":
            if args.project is None:
                parser.error("prepare requires --project NAME (staff only)")
            prepare(path, args.project, 5678 if args.port is None else args.port)
        else:
            if args.project is not None or args.port is not None:
                parser.error("--project and --port are prepare-only; lifecycle uses recorded identity")
            lifecycle(args.action, path)
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
