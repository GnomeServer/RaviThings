"""Run a Linux setup guide top to bottom in a fresh Docker machine, as a learner would.

    python run_guide.py ubuntu [--platform linux/amd64] [--zsh]
    python run_guide.py arch
    python run_guide.py wsl

Every box is pasted exactly as published. The only other inputs are what a
learner supplies (sudo password, the hidden key, `q` in a pager, typed answers)
and clearly labelled stand-ins for things that can't run headless: the GitHub
browser sign-in, Obsidian's window, and the n8n editor in a browser. Each row of
the summary says which. A box passes only when its exit status and the lines its
Expected note names both appear.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

import blocks
import machines
from terminal import Result, Terminal

GUIDES = Path(__file__).resolve().parents[2] / "platforms"
UBUNTU_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin"
ARCH_PATH = "/usr/local/sbin:/usr/local/bin:/usr/bin:/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl"
WSL_PATH = ("/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/usr/lib/wsl/lib:"
            "/mnt/c/Windows/system32:/mnt/c/Windows:/mnt/c/Windows/System32/Wbem:/mnt/c/Windows/System32/WindowsPowerShell/v1.0/")


class Failed(RuntimeError):
    pass


class GuideRun:
    def __init__(self, platform: str, guide: str, machine: str, logdir: Path):
        self.platform, self.machine, self.logdir = platform, machine, logdir
        self.guide = GUIDES / guide
        self.boxes = blocks.read_boxes(self.guide)
        self.rows: list[dict] = []
        self.key, self.token = machines.openrouter_key(), machines.github_token()
        self.secrets = (self.key, self.token)
        self.log = logdir / "transcript.jsonl"
        self.window_count = 0

    # -- boxes ---------------------------------------------------------------
    def box(self, needle: str, heading: str | None = None) -> blocks.Box:
        exact = [b for b in self.boxes if b.code == needle and (heading is None or heading in b.heading)]
        hits = exact or [b for b in self.boxes if needle in b.code and (heading is None or heading in b.heading)]
        if len(hits) != 1:
            raise Failed(f"box lookup {needle!r} heading={heading!r} matched lines {[b.line for b in hits]}")
        return hits[0]

    def paste(self, term: Terminal, needle: str, *, expect: tuple[str, ...] = (), status: str = "ok",
              heading: str | None = None, after_enter=None, respond=None, timeout: float = 900,
              note: str = "", must_pass: bool = True) -> Result:
        box = self.box(needle, heading)
        result = term.paste(box.code, after_enter=after_enter, respond=respond, timeout=timeout,
                            meta={"line": box.line, "heading": box.heading})
        missing = [p for p in expect if not re.search(p, result.output, re.M)]
        verdict = "PASS" if result.status == status and not missing else "FAIL"
        row = {"kind": "box", "line": box.line, "heading": box.heading, "window": term.name, "status": result.status,
               "exit": result.exit, "seconds": result.seconds, "verdict": verdict, "expected_status": status,
               "missing": missing, "answered": result.answered, "note": note,
               "tail": [line for line in result.output.strip().splitlines() if line.strip()][-6:]}
        self.rows.append(row)
        print(f"[{verdict}] {box.line:4} {box.heading[:40]:40} {result.status:10} {result.seconds:7}s {note}", flush=True)
        if verdict == "FAIL":
            print("    missing:", missing, "\n    tail:", *row["tail"], sep="\n      ", flush=True)
            if must_pass:
                raise Failed(f"box {box.line} ({box.heading}) failed")
        return result

    def action(self, kind: str, what: str, detail: str = "") -> None:
        self.rows.append({"kind": kind, "what": what, "detail": detail})
        print(f"[{kind.upper()}] {what} {detail}", flush=True)

    # -- machine helpers -------------------------------------------------------
    def sh(self, script: str, *, user: str = "root", check: bool = True, stdin: str | None = None,
           container: str | None = None) -> str:
        args = ["docker", "exec", "-i", "-u", user, container or self.machine, "sh", "-c", script]
        done = subprocess.run(args, input=stdin, text=True, capture_output=True)
        if check and done.returncode != 0:
            raise Failed(f"harness command failed ({done.returncode}): {script[:120]}\n{done.stdout[-800:]}{done.stderr[-800:]}")
        return done.stdout

    def window(self, argv: list[str], *, shell: str = "bash", label: str) -> Terminal:
        self.window_count += 1
        name = f"w{self.window_count}-{label}"
        self.action("window", name, " ".join(a for a in argv if a.startswith(("PATH=", "-i", "-l", "/bin/", "/usr/bin/"))))
        return Terminal(argv, shell=shell, log=self.log, secrets=self.secrets, password="learner-pass", name=name)

    def gh_sign_in(self, term: Terminal) -> None:
        """Stand-in for the browser device sign-in: give gh the token it would have received."""
        self.sh("umask 077; cat > /tmp/gh-token", user="learner", stdin=self.token)
        result = term.type_line("gh auth login --hostname github.com --git-protocol https --with-token < /tmp/gh-token; rm -f /tmp/gh-token",
                                harness=True, timeout=60)
        if result.status != "ok":
            raise Failed("gh token sign-in stand-in failed: " + result.output[-400:])
        self.action("stand-in", "GitHub browser sign-in", "gh auth login --with-token (token from the host's gh login)")

    def obsidian_reply(self, root: str) -> str:
        """Stand-in for typing the current token into Reply in Obsidian and saving."""
        token = self.sh(f"sed -n '3p' '{root}/vault/Token.md'", user="learner").strip()
        if not re.fullmatch(r"[0-9a-f]{32}", token):
            raise Failed(f"unexpected Token.md content: {token!r}")
        self.sh(f"printf '%s\\n' '{token}' > '{root}/vault/Reply.md'", user="learner")
        self.action("simulated", "Obsidian: read Token, type it into Reply, save", f"Reply.md <- token ending {token[-4:]}")
        return token

    def n8n_browser(self, mode: str) -> dict:
        """Stand-in for the n8n editor in a browser: the same REST calls the page makes."""
        script = N8N_BROWSER.replace("__MODE__", mode)
        done = subprocess.run(["docker", "exec", "-i", "-u", "learner", self.machine, "python3", "-"],
                              input=script, text=True, capture_output=True)
        try:
            data = json.loads(done.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            raise Failed(f"n8n stand-in produced no result: {done.stdout[-400:]} {done.stderr[-600:]}")
        self.action("simulated", f"n8n editor in a browser: {mode}", json.dumps(data))
        if not data.get("ok"):
            raise Failed(f"n8n stand-in {mode} failed: {data}")
        return data

    def summary(self, outcome: str, error: str = "") -> Path:
        path = self.logdir / "summary.json"
        boxes = [r for r in self.rows if r["kind"] == "box"]
        path.write_text(json.dumps({"platform": self.platform, "guide": str(self.guide.name), "machine": self.machine,
                                    "outcome": outcome, "error": error, "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                    "boxes_passed": sum(r["verdict"] == "PASS" for r in boxes), "boxes_failed": sum(r["verdict"] == "FAIL" for r in boxes),
                                    "rows": self.rows}, indent=1), encoding="utf-8")
        return path


N8N_BROWSER = r'''
import json, time, urllib.error, urllib.request, uuid
BASE = "http://127.0.0.1:5678"
EMAIL, PASSWORD, NAME = "learner@course.test", "CoursePass123", "Module 7 readiness"
# A browser on http://localhost sends n8n's Secure auth cookie; Python's cookie jar wouldn't, so keep it by hand.
opener, browser, cookie = urllib.request.build_opener(), str(uuid.uuid4()), {}
def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "browser-id": browser}
    if cookie:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookie.items())
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with opener.open(request, timeout=60) as response:
            for header in response.headers.get_all("Set-Cookie") or []:
                key, value = header.split(";", 1)[0].split("=", 1)
                cookie[key] = value
            raw = response.read()
            try:
                return response.status, json.loads(raw or b"null")
            except json.JSONDecodeError:
                return response.status, raw[:200].decode(errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read()[:300].decode(errors="replace")
    except (urllib.error.URLError, ConnectionError, TimeoutError) as error:
        return 0, str(error)
mode = "__MODE__"
result = {"mode": mode}
for attempt in range(90):  # the page keeps loading until the editor's API answers
    status, settings = call("GET", "/rest/settings")
    if status == 200 and isinstance(settings, dict):
        break
    time.sleep(4)
result["waited_s"] = attempt * 4
setup_needed = isinstance(settings, dict) and settings.get("data", {}).get("userManagement", {}).get("showSetupOnFirstLoad")
result["setup_screen"] = bool(setup_needed)
if mode == "create":
    status, body = call("POST", "/rest/owner/setup", {"email": EMAIL, "firstName": "Course", "lastName": "Learner", "password": PASSWORD})
    result["owner_setup"] = status
    status, body = call("POST", "/rest/workflows", {"name": NAME, "nodes": [], "connections": {}, "active": False, "settings": {}})
    result["create"] = status
else:
    status, body = call("POST", "/rest/login", {"emailOrLdapLoginId": EMAIL, "password": PASSWORD})
    result["login"] = status
status, body = call("GET", "/rest/workflows")
rows = body.get("data", []) if isinstance(body, dict) else []
result["list"] = status
result["names"] = [w.get("name") for w in rows]
result["active"] = [w.get("active") for w in rows]
result["ok"] = NAME in result["names"] and not any(result["active"]) and not (mode == "verify" and setup_needed)
print(json.dumps(result))
'''


# ---------------------------------------------------------------------------
def ubuntu(args) -> None:
    arch = "amd64" if args.platform == "linux/amd64" else "arm64"
    tag = f"aihb-lab/main-ubuntu:{arch}"
    machines.run("docker", "build", "-q", "--platform", args.platform, "-t", tag, "-f",
                 str(machines.IMAGES / "ubuntu-desktop.Dockerfile"), str(machines.IMAGES))
    name = f"aihb-lab-main-ubuntu-{arch}-{time.strftime('%H%M%S')}"
    logdir = machines.LAB / "main" / name
    logdir.mkdir(parents=True, exist_ok=True)
    machines.start(tag, name, platform=args.platform)
    run = GuideRun(f"ubuntu-{arch}" + ("-zsh" if args.zsh else ""), "ubuntu.md", name, logdir)
    shell = "/usr/bin/zsh" if args.zsh else "/bin/bash"
    try:
        run.sh("Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &")
        run.action("environment", "display", "Xvfb :99 stands in for the desktop session's display")
        env = {"DISPLAY": ":99", "XDG_SESSION_TYPE": "x11"}
        if args.zsh:
            run.sh("apt-get update -qq && apt-get install -y -qq zsh >/dev/null && chsh -s /usr/bin/zsh learner && su learner -c 'touch ~/.zshrc'")
            run.action("environment", "zsh learner", "zsh installed, chosen as the login shell, empty ~/.zshrc as a zsh user has")
        def window(label):
            return run.window(machines.terminal_argv(name, shell=shell, path=UBUNTU_PATH, env=env), shell="zsh" if args.zsh else "bash", label=label)

        w = window("first")
        run.paste(w, "course_check() {", expect=(r"^OS ubuntu 24\.04", r"^PACKAGES", r"^PY /"))
        run.paste(w, "sudo apt-get update && sudo apt-get install -y git", timeout=1800)
        run.paste(w, "command -v git && git --version", expect=(r"^/usr/bin/git$", r"^git version 2\."))
        run.paste(w, "course_install_omp() {", expect=(r"^OMP_VERSION omp/[0-9.]+$", r"^PATH_LINE"), timeout=600)
        run.paste(w, "GIT_TERMINAL_PROMPT=0 git ls-remote --exit-code", heading="4. Get the course files", status="failed",
                  note="expected: a new learner has no GitHub credentials yet")
        run.paste(w, "command -v gh >/dev/null 2>&1 || { sudo apt-get", expect=(r"gh version",), timeout=1200)
        run.gh_sign_in(w)
        run.paste(w, "gh auth status --hostname github.com", heading="If GitHub access fails", expect=(r"Logged in to github\.com",))
        run.paste(w, "gh auth setup-git --hostname github.com &&", expect=(r"\tHEAD$",))
        run.paste(w, "course_use_checkout() {", expect=(r"^R /home/learner/Documents/AIHB_OCT_2026$", r"^M /home/learner/Documents/AIHB_OCT_2026/AI_Harness_Bootcamp_2/module-00-setup$"), timeout=900)
        w.close()

        if args.zsh:
            w = window("new-terminal")
            run.paste(w, "course_confirm_new_terminal() {", expect=(r"^OMP_PATH /home/learner/\.local/bin/omp$", r"^OMP_VERSION omp/[0-9.]+$", r"^MISSING$"))
            run.action("scope", "zsh variant", "steps 1 to 5 only")
            run.summary("PASS")
            return

        w = window("new-terminal")
        run.paste(w, "course_confirm_new_terminal() {", expect=(r"^OMP_PATH /home/learner/\.local/bin/omp$", r"^OMP_VERSION omp/[0-9.]+$", r"^MISSING$"))
        hidden = run.paste(w, "IFS= read -r -s OPENROUTER_API_KEY", after_enter=[(1.5, run.key + "\r")])
        if "[REDACTED-0]" in hidden.output:
            raise Failed("the key was echoed")
        run.paste(w, "export OPENROUTER_API_KEY", expect=(r"^SET$",))
        run.paste(w, "course_run_readiness() {", expect=(r"^LAUNCH_EXIT 0$", r"^READINESS CHECK PASS", r"^VERIFY_EXIT 0$"), timeout=900, note="one paid OpenRouter call")
        run.paste(w, "course_save_report() {", expect=(r"SETUP CHECK PASS", r"^REPORT_EXIT 0$", r"^omp works [0-9a-f]{32}$"))

        run.paste(w, "course_download_obsidian() {", expect=(r"SHA256 VERIFIED",), timeout=1200)
        if arch == "amd64":
            run.paste(w, "course_install_obsidian_deb() {", timeout=1800)
            run.paste(w, "obsidian &", heading="x86-64")
        else:
            run.paste(w, "course_obsidian_fuse() {", timeout=1800)
        time.sleep(15)
        alive = run.sh("pgrep -u learner -f -c -i '[o]bsidian' || true").strip()
        run.action("observed", "Obsidian process under Xvfb", f"{alive} learner processes after 15 s; the window itself was not inspected")
        if alive in ("", "0"):
            raise Failed("Obsidian did not stay running after launch")
        result = run.paste(w, "course_initialize_obsidian() {", expect=(r"^OPEN EXACT VAULT: /home/learner/course-evidence/obsidian-ubuntu-",))
        root = re.search(r"^OPEN EXACT VAULT: (\S+)/vault$", result.output, re.M).group(1)
        run.obsidian_reply(root)
        run.paste(w, "check --root \"$OBS_ROOT\" &&", expect=(r"^PASS: Obsidian file round-trip", r"Source token rotated outside Obsidian"))
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"', heading="Open the practice vault",
                  expect=(r"^Token generation 2", r"^PASS: Obsidian file round-trip"))
        w.close()

        w = window("n8n-check")
        run.paste(w, "id -un", heading="10.", expect=(r"^learner$", r"DESTINATION absent", r"DOCKER missing"))
        run.paste(w, "if command -v docker >/dev/null 2>&1; then\n  docker info", heading="10.")
        run.paste(w, "course_install_docker_ubuntu() {", timeout=2400)
        run.paste(w, "course_docker_access() {")
        w.close()
        run.action("relogin", "sign out and back in", "fresh session: groups re-read from /etc/group")
        w = window("fresh-login")
        run.paste(w, "sudo systemctl start docker.service")
        run.paste(w, "id -nG && docker context show && docker info", expect=(r"\bdocker\b", r"Server Version"))
        run.paste(w, "course_download_n8n() {", expect=(r"REVIEW",), timeout=600)
        run.paste(w, 'less "$N8N_REVIEW_SCRIPT"', after_enter=[(3, "q")], timeout=60)
        run.paste(w, "course_run_n8n_installer() {", expect=(r"Created .*compose\.yml",), timeout=900)
        run.paste(w, "course_bind_and_record() {", expect=(r"PORT bound to 127\.0\.0\.1:5678", r"PROJECT recorded: n8n-course"))
        run.paste(w, "course_n8n() {", heading="13.")
        with machines.n8n_turn():
            run.action("lock", "n8n turn acquired")
            try:
                run.paste(w, "if [ -n \"$(ss -Hltn 'sport = :5678')\" ]; then", timeout=3600)
                for attempt in range(6):
                    result = run.paste(w, "course_n8n ps --all &&", heading="14.", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), must_pass=False,
                                       note="Recovery: wait a minute and paste again" if attempt else "")
                    if run.rows[-1]["verdict"] == "PASS" and "starting" not in result.output:
                        break
                    time.sleep(60)
                else:
                    raise Failed("n8n status never settled")
                run.n8n_browser("create")
                run.paste(w, "course_n8n down &&", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), timeout=1800)
                run.n8n_browser("verify")
                w.close()
                run.action("reboot", "docker restart", "systemd boots again; nothing in the stack restarts by itself")
                machines.run("docker", "restart", name)
                for _ in range(120):
                    if run.sh("systemctl is-system-running || true").strip() in {"running", "degraded"}:
                        break
                    time.sleep(1)
                run.sh("Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &")
                w = window("later-session")
                active = run.sh("systemctl is-active docker.service || true").strip()
                run.action("observed", "docker.service after the restart", active)
                run.action("guide", "Later sessions", "paste the step 13 helper box, then the step 14 start and check boxes")
                run.paste(w, "course_n8n() {", heading="13.")
                run.paste(w, "if [ -n \"$(ss -Hltn 'sport = :5678')\" ]; then", timeout=1800)
                for attempt in range(6):
                    result = run.paste(w, "course_n8n ps --all &&", heading="14.", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), must_pass=False,
                                       note="Recovery: wait a minute and paste again" if attempt else "")
                    if run.rows[-1]["verdict"] == "PASS" and "starting" not in result.output:
                        break
                    time.sleep(60)
                for attempt in range(6):
                    try:
                        run.n8n_browser("verify")
                        break
                    except Failed:
                        time.sleep(30)
                else:
                    raise Failed("workflow not reachable after the later-session steps")
            finally:
                run.sh("su learner -c 'cd ~ && docker compose -p n8n-course --env-file n8n-course/.env -f n8n-course/compose.yml down' || true", check=False)
                run.action("cleanup", "n8n stack stopped (volumes kept until the machine is removed)")
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001 - report every failure in the summary
        run.summary("FAIL", repr(error))
        raise
    finally:
        run.sh("su learner -c 'gh auth logout --hostname github.com' </dev/null || true", check=False)
        if not args.keep:
            machines.remove(name)

def wsl(args) -> None:
    """Ubuntu on WSL 2 with Docker Desktop: a systemd Ubuntu machine whose network, home folder,
    and Docker socket are shared with a separate engine container, as Desktop's WSL integration shares them."""
    tag = "aihb-lab/main-wsl:arm64"
    machines.run("docker", "build", "-q", "-t", tag, "-f", str(machines.IMAGES / "wsl-desktop.Dockerfile"), str(machines.IMAGES))
    name = f"aihb-lab-main-wsl-{time.strftime('%H%M%S')}"
    engine = f"{name}-engine"
    volumes = [f"{name}-home", f"{name}-sock", f"{engine}-docker", f"{engine}-containerd"]
    logdir = machines.LAB / "main" / name
    logdir.mkdir(parents=True, exist_ok=True)

    def boot() -> None:
        machines.run("docker", "run", "-d", "--name", engine, "--privileged", "-e", "DOCKER_TLS_CERTDIR=",
                     "-v", f"{name}-home:/home/learner", "-v", f"{name}-sock:/shared",
                     "-v", f"{engine}-docker:/var/lib/docker", "-v", f"{engine}-containerd:/var/lib/containerd",
                     "docker:dind", "--host=unix:///shared/docker.sock")
        for _ in range(90):
            if machines.run("docker", "exec", engine, "docker", "-H", "unix:///shared/docker.sock", "info", check=False).returncode == 0:
                break
            time.sleep(1)
        else:
            raise Failed("engine stand-in did not start")
        machines.run("docker", "run", "-d", "--name", name, "--privileged", "--cgroupns=private", "--network", f"container:{engine}",
                     "--tmpfs", "/run", "--tmpfs", "/run/lock", "-v", f"{name}-home:/home/learner",
                     "-v", f"{name}-sock:/mnt/wsl/docker-desktop/shared-sockets", tag)
        for _ in range(120):
            if machines.run("docker", "exec", name, "systemctl", "is-system-running", check=False).stdout.strip() in {"running", "degraded"}:
                break
            time.sleep(1)
        else:
            raise Failed("WSL machine did not boot")

    def restart() -> None:
        machines.run("docker", "restart", engine)
        for _ in range(90):
            if machines.run("docker", "exec", engine, "docker", "-H", "unix:///shared/docker.sock", "info", check=False).returncode == 0:
                break
            time.sleep(1)
        machines.run("docker", "restart", name)
        for _ in range(120):
            if machines.run("docker", "exec", name, "systemctl", "is-system-running", check=False).stdout.strip() in {"running", "degraded"}:
                break
            time.sleep(1)

    run = GuideRun("wsl", "windows-wsl.md", name, logdir)
    env = {"WSL_DISTRO_NAME": "Ubuntu-24.04", "WSL_INTEROP": "/run/WSL/1_interop", "WSLENV": "WT_SESSION:WT_PROFILE_ID",
           "DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": "/mnt/wslg/runtime-dir"}

    def window(label: str) -> Terminal:
        return run.window(machines.terminal_argv(name, login=True, path=WSL_PATH, env=env), label=label)

    def integrate() -> None:
        gid = run.sh("getent group docker >/dev/null || groupadd docker; getent group docker | cut -d: -f3").strip()
        run.sh("ln -sfn /opt/desktop-cli/docker /usr/bin/docker && mkdir -p /usr/local/lib/docker/cli-plugins && "
               "ln -sfn /opt/desktop-cli/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose && "
               "ln -sfn /mnt/wsl/docker-desktop/shared-sockets/docker.sock /var/run/docker.sock && usermod -aG docker learner")
        run.sh(f"chgrp {gid} /shared/docker.sock && chmod 660 /shared/docker.sock", container=engine)
        run.action("stand-in", "Docker Desktop with WSL integration on", "CLI and Compose plugin on PATH, /var/run/docker.sock to the shared engine, learner in docker group")

    try:
        for volume in volumes:
            machines.run("docker", "volume", "rm", "-f", volume, check=False)
        boot()
        run.sh("[ -f /home/learner/.profile ] || cp -a /etc/skel/. /home/learner/; chown -R learner:learner /home/learner")
        run.sh("Xvfb :0 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &")
        run.action("environment", "WSL window", "login shell; Linux PATH plus appended Windows folders; WSL_DISTRO_NAME, WSLg variables; Xvfb :0 stands in for WSLg")

        w = window("opened-by-name")
        run.paste(w, "course_find_python() {", expect=(r"UBUNTU ubuntu 24\.04", r"WSL_DISTRO Ubuntu-24\.04", r"PACKAGES_TO_INSTALL"))
        run.paste(w, "sudo apt-get update && sudo apt-get install", heading="2.", expect=(r"PACKAGES_TO_INSTALL none", r"CHECK DONE"), timeout=1800)
        run.paste(w, "command -v git && git --version", expect=(r"^/usr/bin/git$", r"^git version 2\."))
        run.paste(w, "course_install_omp() {", expect=(r"SHA256 VERIFIED", r"PATH_LINE", r"^OMP_VERSION omp/[0-9.]+"), timeout=600)
        run.paste(w, "course_get_files() {", status="failed", note="expected: a new learner has no GitHub credentials yet")
        run.paste(w, "if type -P gh >/dev/null; then gh --version;", expect=(r"gh version",), timeout=1200)
        run.gh_sign_in(w)
        run.paste(w, "gh auth status --hostname github.com && gh auth setup-git", expect=(r"Logged in to github\.com", r"\tHEAD$"))
        run.paste(w, "course_get_files() {", expect=(r"Cloned the course checkout|Using the existing course checkout", r"Required course files present"), timeout=900)
        w.close()

        w = window("new-window")
        run.paste(w, "course_confirm_window() {", expect=(r"OMP_PATH /home/learner/\.local/bin/omp", r"^OMP_VERSION omp/[0-9.]+", r"^MISSING$"))
        hidden = run.paste(w, "IFS= read -r -s OPENROUTER_API_KEY", after_enter=[(1.5, run.key + "\r")])
        if "[REDACTED-0]" in hidden.output:
            raise Failed("the key was echoed")
        run.paste(w, "export OPENROUTER_API_KEY", expect=(r"^SET$",))
        run.paste(w, "course_readiness_check() {", expect=(r"^LAUNCH_EXIT 0$", r"READINESS CHECK PASS", r"^VERIFY_EXIT 0$"), timeout=900, note="one paid OpenRouter call")
        run.paste(w, "course_save_report() {", expect=(r"SETUP CHECK PASS", r"^REPORT_EXIT 0$", r"omp works [0-9a-f]{32}"))

        run.paste(w, "printf 'WSL_DISTRO %s\\nHOME %s\\nARCH %s\\n'", expect=(r"^WSLG PRESENT$",))
        run.paste(w, "course_install_obsidian() {", expect=(r"OBSIDIAN INSTALLED",), timeout=1800)
        run.paste(w, "course_open_obsidian() {", expect=(r"OBSIDIAN STARTING",))
        time.sleep(15)
        alive = run.sh("pgrep -u learner -f -c -i '[o]bsidian' || true").strip()
        run.action("observed", "Obsidian process under the WSLg stand-in", f"{alive} learner processes after 15 s; the window itself was not inspected")
        if alive in ("", "0"):
            raise Failed("Obsidian did not stay running after launch")
        result = run.paste(w, "course_start_vault() {", expect=(r"^ROOT /home/learner/obsidian-readiness-", r"^VAULT "))
        root = re.search(r"^ROOT (\S+)$", result.output, re.M).group(1)
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$ObsidianHelper" check --root "$ObsidianRoot" && "$PY"', expect=(r"^PASS: Obsidian file round-trip", r"Source token rotated outside Obsidian"))
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$ObsidianHelper" check --root "$ObsidianRoot"', expect=(r"^Token generation 2", r"^PASS: Obsidian file round-trip"))

        run.paste(w, "if dpkg-query -W -f='${Status}\\n' docker-ce", expect=(r"^NO UBUNTU DOCKER ENGINE$",))
        integrate()
        w.close()
        w = window("after-integration")
        run.paste(w, "course_confirm_window() {", expect=(r"^MISSING$",), note="the guide asks for step 5 again in the new window")
        run.paste(w, "course_docker_check() {", expect=(r"DOCKER_ENGINE", r"DOCKER READY FOR n8n"))
        # The prompt text is also in the pasted box, so answer by timing: quit less, then type INSTALL.
        run.paste(w, "course_n8n_install() {", after_enter=[(4, "q"), (7, "INSTALL\r")],
                  expect=(r"Created .*compose\.yml", r"Not starting"), timeout=900)
        run.paste(w, "course_n8n_prepare() {", expect=(r"PORT BOUND 127\.0\.0\.1:5678:5678", r"PROJECT aihb-n8n"))
        with machines.n8n_turn():
            run.action("lock", "n8n turn acquired")
            try:
                start_box = run.box("course_n8n up -d && course_n8n_status", heading="Start n8n and check it")
                result = run.paste(w, start_box.code, expect=(r"127\.0\.0\.1:5678", r"2\.41\.5"), timeout=3600, must_pass=False)
                for attempt in range(6):
                    if run.rows[-1].get("verdict") == "PASS" and "starting" not in result.output:
                        break
                    time.sleep(60)
                    result = w.type_line("course_n8n_status", timeout=600)
                    good = all(re.search(p, result.output, re.M) for p in (r"127\.0\.0\.1:5678", r"2\.41\.5"))
                    run.rows.append({"kind": "recovery", "what": "course_n8n_status (the box's Recovery: wait a minute and run it again)",
                                     "verdict": "PASS" if result.status == "ok" and good else "FAIL", "tail": result.output.strip().splitlines()[-4:]})
                else:
                    raise Failed("n8n status never settled")
                run.n8n_browser("create")
                run.paste(w, "course_n8n down && course_n8n up -d && course_n8n_status", expect=(r"127\.0\.0\.1:5678", r"2\.41\.5"), timeout=1800)
                run.n8n_browser("verify")
                w.close()
                run.action("reboot", "Windows restart", "engine and Ubuntu restarted; the stack has no restart policy")
                restart()
                integrate()
                run.sh("Xvfb :0 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &")
                w = window("later-session")
                run.action("guide", "later session", "follow: start Docker Desktop, open Ubuntu by NAME, paste the start box again")
                run.paste(w, start_box.code, expect=(r"127\.0\.0\.1:5678", r"2\.41\.5"), timeout=1800, must_pass=False)
                for attempt in range(8):
                    try:
                        run.n8n_browser("verify")
                        break
                    except Failed:
                        time.sleep(30)
                else:
                    raise Failed("workflow not reachable after the later-session steps")
            finally:
                run.sh("su learner -c 'cd ~ && docker compose -p aihb-n8n --env-file n8n-course/.env -f n8n-course/compose.yml down' || true", check=False)
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001
        run.summary("FAIL", repr(error))
        raise
    finally:
        run.sh("su learner -c 'gh auth logout --hostname github.com' </dev/null || true", check=False)
        if not args.keep:
            machines.run("docker", "rm", "-f", name, engine, check=False)
            for volume in volumes:
                machines.run("docker", "volume", "rm", "-f", volume, check=False)

def arch(args) -> None:
    """Arch Linux x86_64 under amd64 emulation. systemd can't run as PID 1 there, so the one
    systemctl box is pasted as written and the service it starts is then started by the harness."""
    tag = "aihb-lab/main-arch:amd64"
    machines.run("docker", "build", "-q", "--platform", "linux/amd64", "-t", tag, "-f",
                 str(machines.IMAGES / "arch-main.Dockerfile"), str(machines.IMAGES))
    name = f"aihb-lab-main-arch-{time.strftime('%H%M%S')}"
    logdir = machines.LAB / "main" / name
    logdir.mkdir(parents=True, exist_ok=True)
    machines.start(tag, name, platform="linux/amd64", systemd=False)
    run = GuideRun("arch-amd64", "arch-linux.md", name, logdir)
    env = {"DISPLAY": ":99"}
    pacman = [(r"Enter a number \(default=1\): ?", "\r"), (r"Enter a selection \(default=all\): ?", "\r")]

    def window(label: str) -> Terminal:
        return run.window(machines.terminal_argv(name, path=ARCH_PATH, env=env), label=label)

    def start_dockerd() -> None:
        # systemd as PID 1 would have moved every process out of the root cgroup and delegated controllers;
        # do the same (as docker's own dind entrypoint does) so runc can create container cgroups.
        run.sh("mkdir -p /sys/fs/cgroup/init && xargs -rn1 < /sys/fs/cgroup/cgroup.procs > /sys/fs/cgroup/init/cgroup.procs 2>/dev/null; "
               "sed -e 's/ / +/g' -e 's/^/+/' < /sys/fs/cgroup/cgroup.controllers > /sys/fs/cgroup/cgroup.subtree_control || true")
        run.sh("nohup dockerd -H unix:///var/run/docker.sock --group docker >/var/log/dockerd.log 2>&1 &")
        for _ in range(120):
            if subprocess.run(["docker", "exec", name, "docker", "info"], capture_output=True).returncode == 0:
                break
            time.sleep(1)
        else:
            raise Failed("dockerd did not start: " + run.sh("tail -20 /var/log/dockerd.log", check=False))
        run.action("harness", "start docker.service", "dockerd started by hand with the unit's socket and group, because systemd can't be PID 1 under emulation")

    try:
        run.sh("Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &")
        run.action("environment", "display and init", "Xvfb :99 stands in for the desktop display; PID 1 is sleep, not systemd (amd64 emulation)")
        w = window("first")
        run.paste(w, "course_check_computer() {", expect=(r"^OS arch", r"^ARCH x86_64$", r"^PACKAGES"))
        run.paste(w, "sudo pacman -Syu --needed git python curl", respond=pacman, timeout=3600)
        run.paste(w, "command -v git && git --version", expect=(r"^/usr/bin/git$", r"^git version 2\."))
        run.paste(w, "course_install_omp() {", expect=(r"^OMP_VERSION omp/[0-9.]+", r"PATH_LINE"), timeout=600)
        run.paste(w, "course_use_checkout() {", status="failed", note="expected: a new learner has no GitHub credentials yet")
        run.paste(w, "if command -v gh >/dev/null 2>&1; then gh --", expect=(r"GH MISSING",))
        run.paste(w, "sudo pacman -Syu --needed github-cli", respond=pacman, timeout=1800)
        run.gh_sign_in(w)
        run.paste(w, "gh auth status --hostname github.com", heading="If GitHub access fails", expect=(r"Logged in to github\.com",))
        run.paste(w, "gh auth setup-git --hostname github.com &&", expect=(r"\tHEAD$",))
        run.paste(w, "course_use_checkout() {", expect=(r"^R /home/learner/Documents/AIHB_OCT_2026$",), timeout=900)
        w.close()

        w = window("new-terminal")
        run.paste(w, "course_confirm_new_terminal() {", expect=(r"OMP_PATH /home/learner/\.local/bin/omp", r"^OMP_VERSION omp/[0-9.]+", r"^MISSING$"))
        hidden = run.paste(w, "IFS= read -r -s OPENROUTER_API_KEY", after_enter=[(1.5, run.key + "\r")])
        if "[REDACTED-0]" in hidden.output:
            raise Failed("the key was echoed")
        run.paste(w, "export OPENROUTER_API_KEY", expect=(r"^SET$",))
        run.paste(w, "course_run_readiness() {", expect=(r"^LAUNCH_EXIT 0$", r"READINESS CHECK PASS", r"^VERIFY_EXIT 0$"), timeout=1200, note="one paid OpenRouter call")
        run.paste(w, "course_save_and_read() {", expect=(r"SETUP CHECK PASS", r"^REPORT_EXIT 0$", r"omp works [0-9a-f]{32}"))

        run.paste(w, "pacman -Q obsidian", expect=(r"^obsidian 1\.13\.7",))
        run.paste(w, "obsidian &", heading="Set up local Obsidian")
        time.sleep(20)
        alive = run.sh("pgrep -u learner -f -c -i '[o]bsidian|[e]lectron' || true").strip()
        run.action("observed", "Obsidian process under Xvfb", f"{alive} learner processes after 20 s; the window itself was not inspected")
        if alive in ("", "0"):
            raise Failed("Obsidian did not stay running after launch")
        result = run.paste(w, "course_initialize_obsidian() {", expect=(r"^OPEN EXACT VAULT: /home/learner/course-evidence/obsidian-arch-linux-",))
        root = re.search(r"^OPEN EXACT VAULT: (\S+)/vault$", result.output, re.M).group(1)
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"', heading="Open a fresh practice vault",
                  expect=(r"^Token generation 1", r"^PASS: Obsidian file round-trip"))
        run.paste(w, '"$PY" "$M/scripts/obsidian_readiness.py" refresh --root "$OBS_ROOT"', expect=(r"Source token rotated outside Obsidian",))
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"', heading="Observe an external change",
                  expect=(r"^Token generation 2", r"^PASS: Obsidian file round-trip"))
        w.close()

        w = window("n8n-check")
        run.paste(w, "id -un", heading="10.", expect=(r"^learner$", r"DESTINATION absent", r"DOCKER missing"))
        run.paste(w, "if command -v docker >/dev/null 2>&1; then\n  docker info", heading="10.", expect=(r"DOCKER missing",))
        run.paste(w, "for package in docker docker-compose", expect=(r"docker absent",))
        run.paste(w, "sudo pacman -Syu --needed docker docker-compose", respond=pacman, timeout=1800)
        run.paste(w, "course_docker_access() {")
        w.close()
        run.action("relogin", "sign out and back in", "fresh session: groups re-read from /etc/group")
        w = window("fresh-login")
        run.paste(w, "sudo systemctl start docker.service", status="failed", must_pass=False,
                  note="systemd isn't PID 1 under emulation; the next row starts the daemon instead")
        start_dockerd()
        run.paste(w, "id -un && id -nG && docker context show", expect=(r"\bdocker\b", r"Server Version"))
        run.paste(w, "course_download_n8n() {", expect=(r"REVIEW",), timeout=600)
        run.paste(w, 'less "$N8N_REVIEW_SCRIPT"', after_enter=[(3, "q")], timeout=60)
        run.paste(w, "course_run_reviewed_n8n() {", expect=(r"Created .*compose\.yml",), timeout=900)
        run.paste(w, "course_bind_loopback() {", expect=(r"PORT_BOUND 127\.0\.0\.1:5678:5678",))
        run.paste(w, "course_n8n_identify() {", expect=(r"PROJECT recorded: n8n-course",))
        run.paste(w, "course_n8n() {", heading="14.")
        run.paste(w, "ss -ltn 'sport = :5678'", heading="14.")
        with machines.n8n_turn():
            try:
                result = run.paste(w, "course_n8n up -d", heading="14.", timeout=5400, must_pass=False,
                                   note="containers can't start under amd64 emulation; steps 14-15 and later sessions run natively in `arch-arm`")
                if "runc did not terminate successfully" in result.output:
                    run.action("environment limit", "nested containers under Rosetta",
                               "runc exits with status 2 inside an emulated amd64 machine; continue on the native arm64 substitute")
            finally:
                run.sh("su learner -c 'cd ~ && docker compose -p n8n-course --env-file n8n-course/.env -f n8n-course/compose.yml down' || true", check=False)
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001
        run.summary("FAIL", repr(error))
        raise
    finally:
        run.sh("su learner -c 'gh auth logout --hostname github.com' </dev/null || true", check=False)
        if not args.keep:
            machines.remove(name)


def arch_arm(args) -> None:
    """Arch Linux ARM, native arm64, systemd as PID 1: the guide's Docker, n8n, and later-session
    boxes (steps 10 to 15). Step 1 accepts only x86_64, so steps 1 to 9 run in `arch`; here the
    packages step 2 installs are already present."""
    tag = "aihb-lab/main-arch-arm:arm64"
    machines.run("docker", "build", "-q", "-t", tag, "-f", str(machines.IMAGES / "arch-arm-main.Dockerfile"), str(machines.IMAGES))
    name = f"aihb-lab-main-arch-arm-{time.strftime('%H%M%S')}"
    logdir = machines.LAB / "main" / name
    logdir.mkdir(parents=True, exist_ok=True)
    machines.start(tag, name)
    run = GuideRun("arch-arm64-substitute", "arch-linux.md", name, logdir)
    run.action("substitute", "Arch Linux ARM (aarch64) with systemd", "steps 10 to 15 and later sessions; git, python, curl, less, diffutils preinstalled as step 2 leaves them")

    def window(label: str) -> Terminal:
        return run.window(machines.terminal_argv(name, path=ARCH_PATH), label=label)

    def inspect_until_settled(w: Terminal, note: str) -> None:
        for attempt in range(10):
            result = run.paste(w, "course_n8n ps --all &&", heading="14.", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), must_pass=False,
                               note=(note + "; " if note else "") + ("Recovery: let it settle and check again" if attempt else ""))
            if run.rows[-1]["verdict"] == "PASS" and "starting" not in result.output:
                return
            time.sleep(60)
        raise Failed("n8n status never settled")

    try:
        w = window("n8n-check")
        run.paste(w, "id -un", heading="10.", expect=(r"^learner$", r"DESTINATION absent", r"DOCKER missing"))
        run.paste(w, "if command -v docker >/dev/null 2>&1; then\n  docker info", heading="10.", expect=(r"DOCKER missing",))
        run.paste(w, "for package in docker docker-compose", expect=(r"docker absent",))
        run.paste(w, "sudo pacman -Syu --needed docker docker-compose",
                  respond=[(r"Enter a number \(default=1\): ?", "\r"), (r"Enter a selection \(default=all\): ?", "\r")], timeout=1800)
        run.paste(w, "course_docker_access() {")
        w.close()
        run.action("relogin", "sign out and back in", "fresh session: groups re-read from /etc/group")
        w = window("fresh-login")
        run.paste(w, "sudo systemctl start docker.service", heading="12.")
        run.paste(w, "id -un && id -nG && docker context show", expect=(r"\bdocker\b", r"Server Version"))
        run.paste(w, "course_download_n8n() {", expect=(r"REVIEW",), timeout=600)
        run.paste(w, 'less "$N8N_REVIEW_SCRIPT"', after_enter=[(3, "q")], timeout=60)
        run.paste(w, "course_run_reviewed_n8n() {", expect=(r"Created .*compose\.yml",), timeout=900)
        run.paste(w, "course_bind_loopback() {", expect=(r"PORT_BOUND 127\.0\.0\.1:5678:5678",))
        run.paste(w, "course_n8n_identify() {", expect=(r"PROJECT recorded: n8n-course",))
        run.paste(w, "course_n8n() {", heading="14.")
        run.paste(w, "ss -ltn 'sport = :5678'", heading="14.")
        with machines.n8n_turn():
            run.action("lock", "n8n turn acquired")
            try:
                run.paste(w, "course_n8n up -d", heading="14.", timeout=3600)
                inspect_until_settled(w, "")
                run.n8n_browser("create")
                run.paste(w, "course_n8n down", heading="15.")
                run.paste(w, "course_n8n up -d &&", heading="15.", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), timeout=1800)
                run.n8n_browser("verify")
                w.close()
                run.action("reboot", "docker restart", "systemd boots again")
                machines.run("docker", "restart", name)
                for _ in range(120):
                    if run.sh("systemctl is-system-running || true").strip() in {"running", "degraded"}:
                        break
                    time.sleep(1)
                run.action("observed", "docker.service after the restart", run.sh("systemctl is-active docker.service || true").strip())
                w = window("later-session")
                run.action("guide", "Later sessions", "start docker.service (step 12), then the step 14 helper, up -d, and inspect boxes")
                run.paste(w, "sudo systemctl start docker.service", heading="12.")
                run.paste(w, "course_n8n() {", heading="14.")
                run.paste(w, "course_n8n up -d", heading="14.", timeout=1800)
                inspect_until_settled(w, "after restart")
                run.n8n_browser("verify")
            finally:
                run.sh("su learner -c 'cd ~ && docker compose -p n8n-course --env-file n8n-course/.env -f n8n-course/compose.yml down' || true", check=False)
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001
        run.summary("FAIL", repr(error))
        raise
    finally:
        if not args.keep:
            machines.remove(name)

def winps(args) -> None:
    """The Windows PowerShell route's Ubuntu part (local n8n through WSL). Its PowerShell boxes need
    native Windows and aren't run here; Ubuntu, Docker Desktop and the restart are emulated as in wsl()."""
    tag = "aihb-lab/main-wsl:arm64"
    machines.run("docker", "build", "-q", "-t", tag, "-f", str(machines.IMAGES / "wsl-desktop.Dockerfile"), str(machines.IMAGES))
    name = f"aihb-lab-main-winps-{time.strftime('%H%M%S')}"
    engine = f"{name}-engine"
    volumes = [f"{name}-home", f"{name}-sock", f"{engine}-docker", f"{engine}-containerd"]
    logdir = machines.LAB / "main" / name
    logdir.mkdir(parents=True, exist_ok=True)
    run = GuideRun("windows-powershell-ubuntu-part", "windows-powershell.md", name, logdir)
    env = {"WSL_DISTRO_NAME": "Ubuntu-24.04", "WSL_INTEROP": "/run/WSL/1_interop", "WSLENV": "WT_SESSION:WT_PROFILE_ID",
           "DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": "/mnt/wslg/runtime-dir"}

    def wait_engine() -> None:
        for _ in range(90):
            if machines.run("docker", "exec", engine, "docker", "-H", "unix:///shared/docker.sock", "info", check=False).returncode == 0:
                return
            time.sleep(1)
        raise Failed("engine stand-in did not start")

    def wait_ubuntu() -> None:
        for _ in range(120):
            if machines.run("docker", "exec", name, "systemctl", "is-system-running", check=False).stdout.strip() in {"running", "degraded"}:
                return
            time.sleep(1)
        raise Failed("Ubuntu did not boot")

    def integrate() -> None:
        gid = run.sh("getent group docker >/dev/null || groupadd docker; getent group docker | cut -d: -f3").strip()
        run.sh("ln -sfn /opt/desktop-cli/docker /usr/bin/docker && mkdir -p /usr/local/lib/docker/cli-plugins && "
               "ln -sfn /opt/desktop-cli/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose && "
               "ln -sfn /mnt/wsl/docker-desktop/shared-sockets/docker.sock /var/run/docker.sock && usermod -aG docker learner")
        run.sh(f"chgrp {gid} /shared/docker.sock && chmod 660 /shared/docker.sock", container=engine)
        run.action("stand-in", "Docker Desktop with WSL integration on", "CLI and Compose plugin on PATH, /var/run/docker.sock to the shared engine, learner in docker group")

    def window(label: str) -> Terminal:
        run.action("not run", "PowerShell box: wsl --distribution Ubuntu-24.04 --cd ~", "needs Windows; a WSL login window opens instead")
        return run.window(machines.terminal_argv(name, login=True, path=WSL_PATH, env=env), label=label)

    try:
        for volume in volumes:
            machines.run("docker", "volume", "rm", "-f", volume, check=False)
        machines.run("docker", "run", "-d", "--name", engine, "--privileged", "-e", "DOCKER_TLS_CERTDIR=",
                     "-v", f"{name}-home:/home/learner", "-v", f"{name}-sock:/shared",
                     "-v", f"{engine}-docker:/var/lib/docker", "-v", f"{engine}-containerd:/var/lib/containerd",
                     "docker:dind", "--host=unix:///shared/docker.sock")
        wait_engine()
        machines.run("docker", "run", "-d", "--name", name, "--privileged", "--cgroupns=private", "--network", f"container:{engine}",
                     "--tmpfs", "/run", "--tmpfs", "/run/lock", "-v", f"{name}-home:/home/learner",
                     "-v", f"{name}-sock:/mnt/wsl/docker-desktop/shared-sockets", tag)
        wait_ubuntu()
        run.sh("[ -f /home/learner/.profile ] || cp -a /etc/skel/. /home/learner/; chown -R learner:learner /home/learner")

        w = window("opened-by-name")
        run.paste(w, "course_check_ubuntu() {", status="failed", expect=(r"^STOP: curl is missing$",),
                  note="expected: this Ubuntu has no curl yet; the box's Recovery points to the fix")
        run.paste(w, "sudo apt-get update && sudo apt-get install --no-upgrade curl", timeout=1800, note="Recovery from If a step stops")
        run.paste(w, "course_check_ubuntu() {", expect=(r"^UBUNTU ubuntu:24\.04 ",))
        integrate()
        w.close()
        w = window("reopened-after-integration")
        run.paste(w, "course_n8n_configure() {", after_enter=[(4, "q"), (7, "INSTALL\r")],
                  expect=(r"Not starting", r"^N8N CONFIGURED "), timeout=900)
        run.paste(w, "course_n8n() {", heading="Start n8n and inspect it")
        start = run.box("course_n8n up -d &&\n  course_n8n ps --all", heading="Start n8n and inspect it")
        with machines.n8n_turn():
            run.action("lock", "n8n turn acquired")
            try:
                for attempt in range(8):
                    result = run.paste(w, start.code, expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), timeout=3600, must_pass=False,
                                       note="Recovery: give it a minute and run the block again" if attempt else "")
                    if run.rows[-1]["verdict"] == "PASS" and "starting" not in result.output:
                        break
                    time.sleep(60)
                else:
                    raise Failed("n8n status never settled")
                run.n8n_browser("create")
                run.paste(w, "course_n8n down &&\n  course_n8n up -d", expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), timeout=1800)
                run.n8n_browser("verify")
                w.close()
                run.action("reboot", "Windows restart", "engine and Ubuntu restarted; the stack has no restart policy")
                machines.run("docker", "restart", engine)
                wait_engine()
                machines.run("docker", "restart", name)
                wait_ubuntu()
                integrate()
                w = window("later-session")
                run.action("guide", "later session", "define course_n8n again, then run the start block again")
                run.paste(w, "course_n8n() {", heading="Start n8n and inspect it")
                run.paste(w, start.code, expect=(r"127\.0\.0\.1:5678", r"^2\.41\.5"), timeout=1800, must_pass=False)
                for attempt in range(8):
                    try:
                        run.n8n_browser("verify")
                        break
                    except Failed:
                        time.sleep(30)
                else:
                    raise Failed("workflow not reachable after the later-session steps")
            finally:
                run.sh("su learner -c 'cd ~ && docker compose -p n8n-course --env-file n8n-course/.env -f n8n-course/compose.yml down' || true", check=False)
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001
        run.summary("FAIL", repr(error))
        raise
    finally:
        if not args.keep:
            machines.run("docker", "rm", "-f", name, engine, check=False)
            for volume in volumes:
                machines.run("docker", "volume", "rm", "-f", volume, check=False)

class MacRun(GuideRun):
    """GuideRun on this Mac: the 'machine' is a throwaway HOME, and harness commands run locally."""

    def sh(self, script: str, *, user: str = "learner", check: bool = True, stdin: str | None = None,
           container: str | None = None) -> str:
        done = subprocess.run(["/bin/sh", "-c", script], input=stdin, text=True, capture_output=True,
                              env={"HOME": self.machine, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})
        if check and done.returncode != 0:
            raise Failed(f"harness command failed ({done.returncode}): {script[:120]}\n{done.stdout[-600:]}{done.stderr[-600:]}")
        return done.stdout


def macos(args) -> None:
    """macOS, sandboxed on this Mac (Docker can't run macOS). Each window is a Terminal.app login zsh with a
    fresh HOME under /private/tmp; nothing installs system-wide, no keychain item is written, and the other
    session's n8n stack on 127.0.0.1:5678 is left alone."""
    import os
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    home = Path(f"/private/tmp/aihb-guide-lab/main/mac-{stamp}/home")
    for folder in ("Documents", "Downloads", "tmp", ".docker"):
        (home / folder).mkdir(parents=True, exist_ok=True)
    (home / ".docker" / "cli-plugins").symlink_to("/Applications/Docker.app/Contents/Resources/cli-plugins")
    logdir = home.parent
    run = MacRun("macos-arm64-sandbox", "macos.md", str(home), logdir)
    run.action("environment", "sandbox HOME", f"{home}; Docker Desktop's per-user cli-plugins link created as Docker Desktop does for each user")
    base = {"HOME": str(home), "USER": os.environ["USER"], "LOGNAME": os.environ["USER"], "SHELL": "/bin/zsh",
            "TERM": "xterm-256color", "LANG": "en_US.UTF-8", "TMPDIR": str(home / "tmp"), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}

    def window(label: str, **extra: str) -> Terminal:
        env = {**base, **extra}
        run.window_count += 1
        name = f"w{run.window_count}-{label}"
        run.action("window", name, "Terminal.app login zsh: env -i, /bin/zsh -l -i" + (f" + {sorted(extra)}" if extra else ""))
        return Terminal(["/usr/bin/env", "-i", *[f"{k}={v}" for k, v in env.items()], "/bin/zsh", "-l", "-i"],
                        shell="zsh", log=run.log, secrets=run.secrets, name=name)

    before = {p: (Path(p).stat().st_mtime if Path(p).exists() else None) for p in
              (os.path.expanduser("~/.zprofile"), os.path.expanduser("~/.zshrc"), os.path.expanduser("~/.local/bin/omp"))}
    try:
        w = window("first", GIT_CONFIG_NOSYSTEM="1")
        run.action("environment", "no saved GitHub credential", "GIT_CONFIG_NOSYSTEM=1 hides the system osxkeychain helper, as for a learner with nothing stored")
        run.paste(w, "course_find_python() {", expect=(r"^MACOS ", r"^ARCH arm64$", r"^FREE_GB "))
        run.paste(w, "course_install_missing() {", expect=(r"^Homebrew ", r"^TOOLS READY /"), note="nothing missing on this Mac, so nothing installs")
        run.paste(w, "command -v git && git --version", expect=(r"^git version 2\.",))
        run.paste(w, "course_add_line() {", expect=(r"^SHA256 VERIFIED ", r"^OMP_VERSION omp/[0-9.]+"), timeout=600)
        run.paste(w, "course_get_checkout() {", status="failed", expect=(r"^ACCESS HOLD",), note="expected: no GitHub credentials yet")
        w.close()
        w = window("github", GIT_CONFIG_NOSYSTEM="1", GH_TOKEN=run.token)
        run.action("stand-in", "GitHub browser sign-in", "GH_TOKEN in this window's environment only; nothing is written to the keychain")
        run.paste(w, "course_get_gh() {", expect=(r"gh version",))
        run.action("not run", "gh auth login --web", "would write a token to the login keychain shared with the real account")
        run.paste(w, "gh auth status --hostname github.com &&", expect=(r"Logged in to github\.com", r"\tHEAD$"))
        run.paste(w, "course_get_checkout() {", expect=(r"^CHECKOUT READY ",), timeout=900)
        w.close()

        w = window("new-terminal")
        run.paste(w, "course_confirm_new_terminal() {", expect=(r"OMP_PATH .*/\.local/bin/omp$", r"^OMP_VERSION omp/[0-9.]+", r"^MISSING$"))
        hidden = run.paste(w, "IFS= read -r -s OPENROUTER_API_KEY", after_enter=[(1.5, run.key + "\r")])
        if "[REDACTED-0]" in hidden.output:
            raise Failed("the key was echoed")
        run.paste(w, "export OPENROUTER_API_KEY", expect=(r"^SET$",))
        run.paste(w, "course_readiness_check() {", expect=(r"^LAUNCH_EXIT 0$", r"READINESS CHECK PASS", r"^VERIFY_EXIT 0$"), timeout=900, note="one paid OpenRouter call")
        run.paste(w, "course_report_and_read() {", expect=(r"SETUP CHECK PASS", r"^REPORT_EXIT 0$", r"omp works [0-9a-f]{32}"))

        run.action("not run again", "Install Obsidian if it is missing (box 555)",
                   "ran in pass mac-20261004T074442Z: downloaded the 1.13.7 .dmg, SHA256 VERIFIED 05daa54f…, and opened the disk image; "
                   "rerunning would open Finder on this Mac again, so this pass skips it. Dragging to Applications was not done.")
        result = run.paste(w, "course_start_vault() {", expect=(r"^OPEN EXACT VAULT: ",))
        root = re.search(r"^OPEN EXACT VAULT: (\S+)/vault$", result.output, re.M).group(1)
        run.obsidian_reply(root)
        run.paste(w, "check --root \"$OBS_ROOT\" &&", expect=(r"^PASS: Obsidian file round-trip", r"Source token rotated outside Obsidian"))
        run.obsidian_reply(root)
        run.paste(w, '"$PY" "$M/scripts/obsidian_readiness.py" check --root "$OBS_ROOT"', heading="Practice in a fresh vault",
                  expect=(r"^Token generation 2", r"^PASS: Obsidian file round-trip"))

        run.paste(w, "course_check_docker() {", status="failed", expect=(r"ENGINE .*Docker Desktop", r"HOLD: something is already listening on port 5678"),
                  note="another session's n8n holds 127.0.0.1:5678 on this Mac")
        shim = home.parent / "shim"
        shim.mkdir()
        (shim / "nc").write_text("#!/bin/sh\n# harness: report 5678 free so generation can run beside the other stack\nexit 1\n")
        (shim / "nc").chmod(0o755)
        w.type_line(f'PATH="{shim}:$PATH"', harness=True)
        run.action("harness", "nc shim", "the generate box's port guard sees 5678 as free; the stack itself is never started")
        run.paste(w, "course_n8n_generate() {", expect=(r"Created .*compose\.yml", r"^PORT BOUND 127\.0\.0\.1:5678$", r"^PROJECT n8n-course$"), timeout=600)
        compose = (home / "n8n-course" / "compose.yml").read_text()
        run.action("observed", "compose.yml", f"{compose.count(chr(39) + '127.0.0.1:5678:5678' + chr(39))} loopback port line, {compose.count(chr(39) + '5678:5678' + chr(39))} open port lines")
        run.action("not run", "start, save, restart (n8n steps 3 to 5)", "port 5678 belongs to the other session's stack on this Mac; the same boxes ran on Linux")
        w.close()
        run.summary("PASS")
    except Exception as error:  # noqa: BLE001
        run.summary("FAIL", repr(error))
        raise
    finally:
        after = {p: (Path(p).stat().st_mtime if Path(p).exists() else None) for p in before}
        run.action("host unchanged" if after == before else "HOST CHANGED", "real ~/.zprofile, ~/.zshrc, ~/.local/bin/omp", json.dumps({p: after[p] == before[p] for p in before}))
        leftovers = subprocess.run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=n8n-course"], capture_output=True, text=True).stdout.split()
        run.action("docker", "n8n-course containers created", str(len(leftovers)))
        run.summary(json.loads((logdir / "summary.json").read_text())["outcome"])
        import shutil
        shutil.rmtree(home / "n8n-course", ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=["ubuntu", "arch", "arch-arm", "wsl", "winps", "macos"])
    parser.add_argument("--platform", dest="docker_platform", default="linux/amd64")
    parser.add_argument("--zsh", action="store_true")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    args.platform, platform = args.docker_platform, args.platform
    {"ubuntu": ubuntu, "wsl": wsl, "arch": arch, "arch-arm": arch_arm, "winps": winps, "macos": macos}[platform](args)


if __name__ == "__main__":
    main()
