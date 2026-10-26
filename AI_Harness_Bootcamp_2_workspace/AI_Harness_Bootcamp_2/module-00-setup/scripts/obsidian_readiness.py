#!/usr/bin/env python3
"""Check a local Obsidian file round-trip without claiming GUI observation.

Python 3.12+. Open only ROOT/vault in Obsidian. Expected values and append-only
observations stay outside the vault. This helper never launches or installs an
application, changes an existing vault, or determines OMP/n8n readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import stat
import sys
from pathlib import Path

PASS = "PASS: Obsidian file round-trip; GUI observation still required"
START = (
    "# Obsidian file round-trip\n\n"
    "Follow [[Token]] and read the current token in Obsidian.\n"
    "Open [[Reply]] and enter only that token on one line, then save.\n"
    "Run the helper's check command in your terminal.\n\n"
    "Next, run refresh while this vault is open. Return to Token in Obsidian\n"
    "and observe the changed token. Replace the old reply with the new token\n"
    "and save. Close and reopen this vault, then run check again.\n\n"
    "A disk match does not prove that you followed a link, used Obsidian,\n"
    "observed an external update, or reopened the vault. Record those actual\n"
    "GUI observations separately before recording Obsidian READY.\n"
)


def token_note(token: str) -> bytes:
    return (
        "# Current token\n\n" + token + "\n\n"
        "Enter this token in [[Reply]], then return to [[Start]].\n"
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(path: Path) -> None:
    """Inspect lexical parents before resolving; reject even dangling links."""
    for part in reversed((path, *path.parents)):
        if part.is_symlink() or part.is_junction():
            raise ValueError(f"linked path is not allowed: {part}")
        if part.exists() and part != path and not part.is_dir():
            raise ValueError(f"parent is not a directory: {part}")


def directory(path: Path) -> None:
    safe_path(path)
    if not path.is_dir():
        raise ValueError(f"missing directory: {path}")
    names: set[str] = set()
    for child in path.iterdir():
        folded = child.name.casefold()
        if folded in names:
            raise ValueError(f"case-colliding name: {child}")
        names.add(folded)


def read_file(path: Path) -> bytes:
    safe_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError(f"expected a regular, unlinked file: {path}")
    if info.st_size > 65536:
        raise ValueError(f"readiness file exceeds 64 KiB: {path}")
    return path.read_bytes()


def create(path: Path, data: bytes) -> None:
    safe_path(path)
    with path.open("xb") as stream:
        stream.write(data)


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def unique_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate expected-record field: {key}")
        result[key] = value
    return result


def external_root(value: Path) -> Path:
    path = value.expanduser().absolute()
    if ".." in path.parts or str(path).startswith(("//", "\\\\")):
        raise ValueError(f"use a local path without '..' or UNC components: {path}")
    safe_path(path)
    path = path.resolve()
    # Works from the repository or from a separately downloaded helper.
    for anchor in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        for parent in (anchor, *anchor.parents):
            if (parent / ".git").exists():
                if path.is_relative_to(parent) or parent.is_relative_to(path):
                    raise ValueError(f"root must not overlap the checkout: {path}")
                break
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            raise ValueError(f"root must be outside every checkout: {path}")
    home = Path.home().resolve()
    if home.is_relative_to(path):
        raise ValueError(f"choose a fresh child directory, not a home/system root: {path}")
    kernel = Path("/proc/sys/kernel/osrelease")
    if sys.platform == "linux" and kernel.is_file():
        if "microsoft" in kernel.read_text(encoding="utf-8").lower():
            if not path.is_relative_to(home) or path.is_relative_to(Path("/mnt")):
                raise ValueError("WSLg readiness requires a directory in your Linux home")
    return path


def expected(root: Path) -> tuple[dict, bytes]:
    directory(root / "expected")
    paths = sorted((root / "expected").iterdir())
    if not paths:
        raise ValueError(f"missing expected record: {root / 'expected'}")
    previous = None
    tokens: set[str] = set()
    raw = b""
    record = {}
    for generation, path in enumerate(paths, 1):
        if path.name != f"{generation:06d}.json":
            raise ValueError(f"unexpected or missing expected generation: {path}")
        raw = read_file(path)
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_fields)
        keys = {"schema", "root", "generation", "token", "previous_sha256"}
        if not isinstance(record, dict) or set(record) != keys:
            raise ValueError(f"invalid expected record: {path}")
        token = record["token"]
        if (record["schema"] != "obsidian-readiness-v1"
                or record["root"] != str(root)
                or type(record["generation"]) is not int
                or record["generation"] != generation
                or record["previous_sha256"] != previous
                or not isinstance(token, str) or len(token) != 32
                or any(c not in "0123456789abcdef" for c in token)
                or token in tokens):
            raise ValueError(f"changed or invalid expected identity: {path}")
        tokens.add(token)
        previous = digest(raw)
    return record, raw


def new_expected(root: Path, generation: int, previous: bytes | None) -> dict:
    return {"schema": "obsidian-readiness-v1", "root": str(root),
            "generation": generation, "token": secrets.token_hex(16),
            "previous_sha256": digest(previous) if previous is not None else None}


def selected(root: Path, record: dict) -> dict[str, bytes]:
    directory(root / "vault")
    files = {name: read_file(root / "vault" / name)
             for name in ("Start.md", "Token.md", "Reply.md")}
    if files["Start.md"] != START.encode("utf-8"):
        raise ValueError(f"linked instructions changed: {root / 'vault/Start.md'}")
    if files["Token.md"] != token_note(record["token"]):
        raise ValueError(f"source token differs from expected record: {root / 'vault/Token.md'}")
    return files


def initialize(root: Path) -> int:
    if root.exists():
        raise ValueError(f"destination already exists; preserve it and choose a fresh root: {root}")
    # An exclusive reservation also preserves incomplete attempts on failure.
    root.mkdir(parents=True)
    (root / "vault").mkdir()
    (root / "expected").mkdir()
    (root / "observations").mkdir()
    record = new_expected(root, 1, None)
    create(root / "vault/Start.md", START.encode("utf-8"))
    create(root / "vault/Token.md", token_note(record["token"]))
    create(root / "vault/Reply.md", b"")
    create(root / "expected/000001.json", encoded(record))
    print(f"Created practice vault: {root / 'vault'}")
    print("Open that folder as a vault in Obsidian, with Sync off and community plugins restricted.")
    print("Open Start, follow Token, enter the observed token in Reply, save, then run check.")
    return 0


def refresh(root: Path) -> int:
    record, raw = expected(root)
    files = selected(root, record)
    directory(root / "observations")
    generation = record["generation"] + 1
    if generation > 999999:
        raise ValueError("generation limit reached; preserve this attempt and use a fresh root")
    next_record = new_expected(root, generation, raw)
    while next_record["token"] == record["token"]:
        next_record = new_expected(root, generation, raw)
    # Preserve the old source and reply before changing the source externally.
    create(root / "observations" / f"refresh-{secrets.token_hex(16)}.json", encoded({
        "operation": "refresh", "generation": record["generation"],
        "expected_sha256": digest(raw), "gui_observed": False,
        "files": {name: data.decode("utf-8") for name, data in files.items()},
    }))
    # Publishing the next expectation first makes interrupted refreshes HOLD;
    # they cannot silently pass against an old expectation.
    create(root / "expected" / f"{generation:06d}.json", encoded(next_record))
    source = root / "vault/Token.md"
    if read_file(source) != files["Token.md"]:
        raise ValueError(f"source changed during refresh; preserve this attempt: {source}")
    source.write_bytes(token_note(next_record["token"]))
    print("Source token rotated outside Obsidian; your saved reply was preserved.")
    print("Observe Token in Obsidian, replace Reply with the new token, and save.")
    print("Close and reopen the vault, then run check. Record actual GUI observations separately.")
    return 0


def check(root: Path) -> int:
    directory(root / "observations")
    observation = {"operation": "check", "root": str(root),
                   "gui_observed": False, "gui_observation_required": True}
    try:
        record, raw = expected(root)
        observation.update(generation=record["generation"], expected_sha256=digest(raw))
        files = selected(root, record)
        observation["files"] = {name: {"sha256": digest(data), "size": len(data)}
                                for name, data in files.items()}
        reply = files["Reply.md"].decode("utf-8").replace("\r\n", "\n")
        if reply not in (record["token"], record["token"] + "\n"):
            raise ValueError(f"saved reply does not match the current token: {root / 'vault/Reply.md'}; "
                             "enter only the token on one line in Obsidian and save")
        message, status = PASS, 0
    except (OSError, ValueError) as error:
        message, status = f"HOLD: {error}", 1
    observation.update(result=message, exit_code=status)
    target = root / "observations" / f"check-{secrets.token_hex(16)}.json"
    create(target, encoded(observation))
    if "generation" in observation:
        generation = observation["generation"]
        stage = ("initial token; external refresh not yet exercised"
                 if generation == 1 else "refreshed token; GUI observation still required")
        print(f"Token generation {generation}: {stage}")
    print(message)
    print(f"Disk observation saved: {target}")
    print("This does not prove GUI use, link navigation, external refresh visibility, or reopening.")
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("initialize", "refresh", "check"))
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args(argv)
    if sys.version_info < (3, 12):
        print("HOLD: Python 3.12 or newer is required")
        return 2
    try:
        root = external_root(args.root)
        if args.command == "initialize":
            return initialize(root)
        directory(root)
        # Serialize helper operations; an interrupted operation leaves a named
        # HOLD rather than allowing another command to overwrite its work.
        lock = root / ".readiness-operation"
        safe_path(lock)
        lock.mkdir()
        try:
            return refresh(root) if args.command == "refresh" else check(root)
        finally:
            lock.rmdir()
    except (OSError, ValueError) as error:
        print(f"HOLD: {error}; preserve this attempt")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
