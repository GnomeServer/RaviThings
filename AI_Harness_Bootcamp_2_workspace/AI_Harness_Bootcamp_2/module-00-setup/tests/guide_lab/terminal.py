"""Drive a real interactive shell the way a learner pastes boxes into a terminal.

A box is sent the way a modern terminal pastes it: wrapped in bracketed-paste
markers while the shell has that mode on, followed by one Return. The driver
then answers only the prompts a learner would answer (sudo password, a
default package question, the pager) and waits until the shell has finished.
A shell left waiting for more input after the paste is reported as
``incomplete`` -- the symptom a learner sees as a ``>`` prompt that never ends.

Completion is read from a marker the shell prints just before each new prompt
(bash PROMPT_COMMAND, zsh precmd), so redisplays of the prompt while a paste
is being edited are never mistaken for a finished command.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import pexpect

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]|\x1b[=>]")
PASTE_ON, PASTE_OFF = "\x1b[?2004h", "\x1b[?2004l"
DONE = re.compile(r"__AIHB_DONE_(\d+)__")
MORE = "__AIHB_MORE__ "
SETTERS = {
    "bash": "PROMPT_COMMAND='printf \"\\n__AIHB\"\"_DONE_%s__\\n\" \"$?\"'; PS1='$ '; PS2='__AIHB''_MORE__ '",
    "zsh": "precmd() { local s=$?; print -r -- ''; print -r -- \"__AIHB\"\"_DONE_${s}__\"; }; PROMPT='%% '; PROMPT2='__AIHB''_MORE__ '; RPROMPT=''",
}


@dataclass
class Result:
    status: str  # ok | failed | incomplete | timeout | closed | needs-password
    exit: int | None
    seconds: float
    transcript: str  # the pasted echo plus everything the shell printed
    answered: list[str] = field(default_factory=list)
    output: str = ""  # only what the shell printed after Return

    def lines(self, pattern: str) -> list[str]:
        return [line for line in self.transcript.splitlines() if re.search(pattern, line)]


class Terminal:
    """One open terminal window. Create a new instance for each new window."""

    def __init__(self, argv: list[str], *, shell: str = "bash", log: Path | None = None,
                 secrets: tuple[str, ...] = (), password: str | None = None,
                 env: dict[str, str] | None = None, cwd: str | None = None, name: str = "terminal"):
        self.shell, self.log, self.password, self.name = shell, log, password, name
        self.secrets = tuple(s for s in secrets if s)
        self.bracketed = False
        self.child = pexpect.spawn(argv[0], argv[1:], encoding="utf-8", codec_errors="replace",
                                   dimensions=(50, 220), env=env, cwd=cwd, timeout=60)
        startup = self._drain(quiet=2.0, limit=90)
        self._record({"event": "open", "argv": argv, "startup": self._clean(startup)})
        setter = self.type_line(SETTERS[shell], harness=True, timeout=60)
        if setter.status != "ok":
            raise RuntimeError(f"{name}: could not set the completion marker: {setter.transcript[-800:]}")

    # -- low level -------------------------------------------------------
    def _track(self, raw: str) -> None:
        on, off = raw.rfind(PASTE_ON), raw.rfind(PASTE_OFF)
        if on > off:
            self.bracketed = True
        elif off > on:
            self.bracketed = False

    def _drain(self, quiet: float, limit: float) -> str:
        leftover, self.child.buffer = self.child.buffer, ""
        self._track(leftover)
        chunks, start, last = [leftover], time.monotonic(), time.monotonic()
        while time.monotonic() - start < limit and time.monotonic() - last < quiet:
            try:
                data = self.child.read_nonblocking(65536, timeout=0.1)
            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                break
            chunks.append(data)
            self._track(data)
            last = time.monotonic()
        return "".join(chunks)

    def _clean(self, raw: str) -> str:
        text = ANSI.sub("", raw).replace("\r", "")
        for index, secret in enumerate(self.secrets):
            text = text.replace(secret, f"[REDACTED-{index}]")
        return text

    def _record(self, entry: dict) -> None:
        if self.log:
            self.log.parent.mkdir(parents=True, exist_ok=True)
            with self.log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"terminal": self.name, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}) + "\n")

    # -- what a learner does --------------------------------------------
    def paste(self, code: str, *, after_enter: list[tuple[float, str]] | None = None,
              respond: list[tuple[str, str]] | None = None, timeout: float = 900, meta: dict | None = None) -> Result:
        """Paste one box, press Return, answer ordinary prompts, wait for the shell.
        `respond` pairs a prompt regex with the text a learner types at it; each fires once."""
        self._drain(quiet=0.3, limit=3)
        if not self.bracketed:
            raise RuntimeError(f"{self.name}: bracketed paste is off; a real terminal would type the box line by line")
        self.child.send("\x1b[200~" + code + "\x1b[201~")
        echo = self._drain(quiet=0.5, limit=10)
        self.child.send("\r")
        return self._wait(after_enter or [], respond or [], timeout, {"kind": "paste", "code": self._clean(code), **(meta or {})}, echo)

    def type_line(self, line: str, *, harness: bool = False, timeout: float = 120,
                  after_enter: list[tuple[float, str]] | None = None, respond: list[tuple[str, str]] | None = None,
                  meta: dict | None = None) -> Result:
        """Type one line and press Return (setup a learner would do by hand, or harness setup)."""
        self._drain(quiet=0.3, limit=3)
        self.child.send(line + "\r")
        return self._wait(after_enter or [], respond or [], timeout, {"kind": "harness" if harness else "type", "code": self._clean(line), **(meta or {})}, "")

    def _wait(self, scheduled: list[tuple[float, str]], respond: list[tuple[str, str]], timeout: float,
              entry: dict, echo: str) -> Result:
        base = [DONE, re.escape(MORE), r"\[sudo\] password for [^:\r\n]+: ?", r"(?m)^Password: ?$",
                r"\[Y/n\] ?", r"\[y/N\] ?", r"\(END\)"]
        start, raw, answered = time.monotonic(), [echo], []
        pending = sorted(scheduled)
        answers = list(respond)
        status, code = "timeout", None
        while True:
            if pending and time.monotonic() - start >= pending[0][0]:
                _, text = pending.pop(0)
                self.child.send(text)
                answered.append("scheduled input")
                continue
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                break
            patterns = base + [pattern for pattern, _ in answers] + [pexpect.EOF, pexpect.TIMEOUT]
            index = self.child.expect(patterns, timeout=min(remaining, 0.5 if pending else 5.0))
            chunk = (self.child.before or "") + (self.child.after if isinstance(self.child.after, str) else "")
            raw.append(chunk)
            self._track(chunk)
            if index == 0:
                code = int(self.child.match.group(1))
                status = "ok" if code == 0 else "failed"
                break
            if index == 1:
                status = "incomplete"
                self.child.send("\x03")
                try:
                    self.child.expect(DONE, timeout=20)
                    raw.append((self.child.before or "") + self.child.after)
                except pexpect.TIMEOUT:
                    pass
                break
            if index in (2, 3):
                if self.password is None:
                    status = "needs-password"
                    break
                self.child.sendline(self.password)
                answered.append("password")
            elif index in (4, 5):
                self.child.send("\r")
                answered.append("default answer " + self.child.after.strip())
            elif index == 6:
                self.child.send("q")
                answered.append("pager q")
            elif index < len(base) + len(answers):
                pattern, text = answers.pop(index - len(base))
                self.child.send(text)
                answered.append(f"answered {pattern!r}")
            elif index == len(base) + len(answers):
                status = "closed"
                break
        if status == "timeout":
            self.child.send("\x03")
            raw.append(self._drain(quiet=2, limit=15))
        raw.append(self._drain(quiet=0.3, limit=3))
        seconds = round(time.monotonic() - start, 1)
        transcript = self._clean("".join(raw))
        result = Result(status, code, seconds, transcript, answered, self._clean("".join(raw[1:])))
        self._record({**entry, "status": status, "exit": code, "seconds": seconds, "answered": answered, "transcript": transcript})
        return result

    def close(self) -> None:
        if self.child.isalive():
            self.child.send("exit\r")
            try:
                self.child.expect(pexpect.EOF, timeout=10)
            except pexpect.TIMEOUT:
                self.child.terminate(force=True)
        self._record({"event": "close"})
