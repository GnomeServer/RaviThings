"""Start throwaway machines in Docker and open learner terminals on them.

A machine is a privileged container that boots systemd, so services start the
way the guides expect. /var/lib/docker and /var/lib/containerd sit on named
volumes, as they would on a real disk, so an engine the guide installs can run.
"""
from __future__ import annotations

import fcntl
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "images"
LAB = Path("/tmp/aihb-guide-lab")


@contextmanager
def n8n_turn():
    """Hold the shared lock while an n8n stack runs; the Docker VM has room for one test stack at a time."""
    LAB.mkdir(parents=True, exist_ok=True)
    with (LAB / "n8n.lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run(*args: str, check: bool = True, capture: bool = True, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), check=check, text=True, capture_output=capture, timeout=timeout)


def openrouter_key() -> str:
    """The key typed at the guide's hidden prompt: $OPENROUTER_API_KEY, else the checkout's ignored .env."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    env_file = Path(os.environ.get("AIHB_LAB_ENV", HERE.parents[3] / ".env"))
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError(f"set OPENROUTER_API_KEY, or put it in {env_file} (git-ignored)")


def github_token() -> str:
    return run("gh", "auth", "token", "--hostname", "github.com").stdout.strip()


def build(tag: str, dockerfile: str, platform: str | None = None) -> None:
    args = ["docker", "build", "-t", tag, "-f", str(IMAGES / dockerfile)]
    if platform:
        args += ["--platform", platform]
    run(*args, str(IMAGES), capture=False)


def start(image: str, name: str, *, platform: str | None = None, extra: tuple[str, ...] = (),
          systemd: bool = True, engine_volumes: bool = True, boot_seconds: int = 300) -> str:
    """Start a machine. With systemd=False the container idles under `sleep infinity` instead
    (systemd can't run as PID 1 under amd64 emulation on Apple Silicon); services the guide
    starts with systemctl must then be started by the harness and reported as such."""
    run("docker", "rm", "-f", name, check=False)
    args = ["docker", "run", "-d", "--name", name, "--hostname", name, "--privileged", "--cgroupns=private"]
    if platform:
        args += ["--platform", platform]
    if systemd:
        args += ["--tmpfs", "/run", "--tmpfs", "/run/lock"]
    else:
        args += ["--entrypoint", "/bin/sleep"]
    if engine_volumes:
        args += ["-v", f"{name}-docker:/var/lib/docker", "-v", f"{name}-containerd:/var/lib/containerd"]
    run(*args, *extra, image, *([] if systemd else ["infinity"]))
    if systemd:
        state = ""
        for _ in range(boot_seconds):
            state = run("docker", "exec", name, "systemctl", "is-system-running", check=False).stdout.strip()
            if state in {"running", "degraded"}:
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{name}: systemd did not finish booting ({state or 'container exited'})")
    return name


def remove(name: str) -> None:
    run("docker", "rm", "-f", name, check=False)
    run("docker", "volume", "rm", "-f", f"{name}-docker", f"{name}-containerd", check=False)


def terminal_argv(container: str, *, user: str = "learner", shell: str = "/bin/bash", login: bool = False,
                  path: str = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                  env: dict[str, str] | None = None) -> list[str]:
    """argv for a terminal window opened from the desktop: a clean session environment plus the shell's own startup files."""
    home = run("docker", "exec", container, "getent", "passwd", user).stdout.strip().split(":")[5]
    session = {"HOME": home, "USER": user, "LOGNAME": user, "SHELL": shell, "TERM": "xterm-256color",
               "LANG": "C.UTF-8", "PATH": path, **(env or {})}
    flags = ["-l", "-i"] if login else ["-i"]
    return ["docker", "exec", "-it", "-u", user, "-w", home, container, "env", "-i",
            *[f"{key}={value}" for key, value in session.items()], shell, *flags]


def host_env() -> dict[str, str]:
    return {key: os.environ[key] for key in ("PATH", "HOME", "USER", "TERM") if key in os.environ}
