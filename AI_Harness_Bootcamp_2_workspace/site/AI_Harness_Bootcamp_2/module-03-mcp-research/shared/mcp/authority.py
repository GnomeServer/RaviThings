#!/usr/bin/env python3
"""Read and check the two files that define an MCP connection.

AUTHORITY.md declares what the connection may do. mcp.json starts the server that
does it. The launcher, the authority probe, the inspector, and the verifier all use
these functions, so a limit means the same thing everywhere.

This module does no network access and starts no process.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vault_mcp import Denied, normalize_prefix  # noqa: E402

SERVER_NAME = "vault"
PHASES = ("research", "partner", "revoked")
READ_TOOLS = ("list_directory", "read_note", "read_multiple_notes", "search_notes", "get_frontmatter", "get_vault_stats")
WRITE_TOOLS = ("write_note",)
CEILING = READ_TOOLS + WRITE_TOOLS
SERVER_FLAGS_WITH_VALUE = ("--root", "--read-prefix", "--write-prefix", "--max-results")
SERVER_FLAGS_PLAIN = ("--read-only", "--no-overwrite")
ENTRY_KEYS = {"type", "command", "args", "instructions", "timeout"}
PYTHON_NAMES = {"python", "python3", "python.exe", "python3.exe"}
AUTHORITY_KEYS = {"schema_version", "phase", "allow_tools", "read_scope", "write_scope", "create_only"}


class AuthorityError(ValueError):
    """A declaration or connection entry cannot be used."""


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise AuthorityError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject(value):
        raise AuthorityError(f"invalid JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
    except json.JSONDecodeError as error:
        raise AuthorityError(f"not valid JSON: {error.msg} (line {error.lineno})") from None


def parse_authority(text: str) -> dict:
    """Return the declaration from the one fenced json block, after full validation."""
    blocks = re.findall(r"^```json\s*\n(.*?)^```\s*$", text, re.M | re.S)
    if len(blocks) != 1:
        raise AuthorityError("AUTHORITY.md must contain exactly one json block")
    return validate_authority(strict_json(blocks[0]))


def _names(value, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AuthorityError(f"{label} must be a list of text values")
    if len(set(value)) != len(value):
        raise AuthorityError(f"{label} lists the same entry twice")
    return list(value)


def _folders(value, label: str) -> list[str]:
    folders = _names(value, label)
    for folder in folders:
        try:
            clean = normalize_prefix(folder)
        except Denied as denial:
            raise AuthorityError(f"{label}: {folder!r} is not a usable folder ({denial.reason})") from None
        if clean != folder:
            raise AuthorityError(f"{label}: write {folder!r} as a folder path ending in a slash, such as {clean!r}")
    return folders


def validate_authority(declaration) -> dict:
    if not isinstance(declaration, dict):
        raise AuthorityError("the declaration must be a JSON object")
    if set(declaration) != AUTHORITY_KEYS:
        missing = sorted(AUTHORITY_KEYS - set(declaration))
        extra = sorted(set(declaration) - AUTHORITY_KEYS)
        raise AuthorityError(f"the declaration needs exactly these fields; missing {missing or 'none'}, unexpected {extra or 'none'}")
    version = declaration["schema_version"]
    if type(version) is not int or version != 1:
        raise AuthorityError("schema_version must be the number 1")
    phase = declaration["phase"]
    if phase not in PHASES:
        raise AuthorityError(f"phase must be one of {', '.join(PHASES)}")
    tools = _names(declaration["allow_tools"], "allow_tools")
    unknown = [name for name in tools if name not in CEILING]
    if unknown:
        raise AuthorityError(f"allow_tools names a tool this exercise never connects to a live run: {', '.join(unknown)}")
    reads = _folders(declaration["read_scope"], "read_scope")
    writes = _folders(declaration["write_scope"], "write_scope")
    for folder in writes:
        if not folder.startswith("Drafts/"):
            raise AuthorityError(f"write_scope {folder!r} must be inside Drafts/")
    if type(declaration["create_only"]) is not bool:
        raise AuthorityError("create_only must be true or false")
    if phase == "revoked":
        if tools or reads or writes:
            raise AuthorityError("a revoked connection allows no tools and no folders")
        return declaration
    if not tools:
        raise AuthorityError("allow_tools is empty: name the tools this phase needs")
    if not any(name in READ_TOOLS for name in tools):
        raise AuthorityError("allow_tools needs at least one tool that reads")
    if not reads:
        raise AuthorityError("read_scope is empty: name the folders this phase may read")
    if "write_note" in tools and not writes:
        raise AuthorityError("write_note is allowed but write_scope is empty")
    if writes and "write_note" not in tools:
        raise AuthorityError("write_scope names folders but write_note is not in allow_tools")
    return declaration


def parse_config(text: str) -> dict:
    config = strict_json(text)
    if not isinstance(config, dict) or not isinstance(config.get("mcpServers"), dict):
        raise AuthorityError("mcp.json must hold an object named mcpServers")
    return config


def validate_entry(entry, work: Path, *, executable: str | None = None) -> dict:
    """Check one server entry and describe it. The entry may only start the supplied server."""
    if not isinstance(entry, dict):
        raise AuthorityError("the server entry must be an object")
    extra = set(entry) - ENTRY_KEYS
    if extra:
        raise AuthorityError(f"the server entry has fields this exercise does not allow: {', '.join(sorted(extra))}")
    if entry.get("type", "stdio") != "stdio":
        raise AuthorityError("only stdio servers are used here")
    command = entry.get("command")
    if not isinstance(command, str) or not command:
        raise AuthorityError("the server entry needs a command")
    if Path(command).name.lower() not in PYTHON_NAMES and command != (executable or sys.executable):
        raise AuthorityError(f"command {command!r} is not Python; a connection entry starts a program, so only the supplied Python server may run here")
    args = entry.get("args")
    if not isinstance(args, list) or not args or any(not isinstance(item, str) for item in args):
        raise AuthorityError("args must be a list of text values that starts with the server script")
    script = Path(args[0])
    expected = (work / "shared" / "mcp" / "vault_mcp.py").resolve()
    if script.resolve() != expected:
        raise AuthorityError(f"args must start with the supplied server {expected}; a connection entry starts a program, so it may not point anywhere else")
    parsed = {"script": expected, "root": None, "read_prefixes": [], "write_prefixes": [], "read_only": False, "no_overwrite": False, "max_results": None}
    rest = args[1:]
    index = 0
    while index < len(rest):
        flag = rest[index]
        if flag in SERVER_FLAGS_PLAIN:
            parsed[flag[2:].replace("-", "_")] = True
            index += 1
            continue
        if flag in SERVER_FLAGS_WITH_VALUE:
            if index + 1 >= len(rest):
                raise AuthorityError(f"{flag} needs a value")
            value = rest[index + 1]
            if flag == "--root":
                if parsed["root"] is not None:
                    raise AuthorityError("--root appears twice")
                parsed["root"] = Path(value)
            elif flag == "--max-results":
                if not re.fullmatch(r"[1-9][0-9]{0,2}", value):
                    raise AuthorityError("--max-results must be a whole number from 1 to 999")
                parsed["max_results"] = int(value)
            else:
                try:
                    clean = normalize_prefix(value)
                except Denied as denial:
                    raise AuthorityError(f"{flag} {value!r}: {denial.reason}") from None
                key = "read_prefixes" if flag == "--read-prefix" else "write_prefixes"
                if clean != value:
                    raise AuthorityError(f"{flag} {value!r} must be a folder path ending in a slash, such as {clean!r}")
                if clean in parsed[key]:
                    raise AuthorityError(f"{flag} {value!r} appears twice")
                parsed[key].append(clean)
            index += 2
            continue
        raise AuthorityError(f"argument {flag!r} is not one of the server's limits")
    if parsed["root"] is None:
        raise AuthorityError("args needs --root followed by the vault folder")
    if parsed["root"].resolve() != (work / "vault").resolve():
        raise AuthorityError(f"--root must be your work copy's vault, {(work / 'vault').resolve()}")
    instructions = entry.get("instructions", True)
    if type(instructions) is not bool:
        raise AuthorityError("instructions must be true or false")
    timeout = entry.get("timeout")
    if timeout is not None and (type(timeout) is not int or not 1 <= timeout <= 60000):
        raise AuthorityError("timeout must be a whole number of milliseconds up to 60000")
    parsed["instructions"] = instructions
    parsed["timeout"] = timeout
    return parsed


def server_entry(config: dict, name: str = SERVER_NAME):
    entry = config["mcpServers"].get(name)
    if entry is None:
        raise AuthorityError(f"mcp.json has no server named {name!r}")
    return entry


def consistency(declaration: dict, parsed: dict) -> list[str]:
    """Return the ways the server's limits differ from the declaration. Empty means they agree."""
    problems = []
    if sorted(parsed["read_prefixes"]) != sorted(declaration["read_scope"]):
        problems.append(f"read limits differ: AUTHORITY.md read_scope is {sorted(declaration['read_scope'])} but the server runs with --read-prefix {sorted(parsed['read_prefixes'])}")
    if sorted(parsed["write_prefixes"]) != sorted(declaration["write_scope"]):
        problems.append(f"write limits differ: AUTHORITY.md write_scope is {sorted(declaration['write_scope'])} but the server runs with --write-prefix {sorted(parsed['write_prefixes'])}")
    if parsed["no_overwrite"] != declaration["create_only"]:
        problems.append(f"create_only is {str(declaration['create_only']).lower()} in AUTHORITY.md but the server {'has' if parsed['no_overwrite'] else 'does not have'} --no-overwrite")
    if parsed["read_only"] != (not declaration["write_scope"]):
        problems.append("the server's --read-only flag must be present exactly when write_scope is empty")
    return problems
