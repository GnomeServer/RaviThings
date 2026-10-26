#!/usr/bin/env python3
"""Read what an MCP server says about itself before you connect it to a model.

Usage: mcp_inspect.py --config mcp.json [--server vault] [--out FILE] [--json]

The inspector starts the supplied vault server, asks it who it is and which tools it
offers, and prints what a connected model would be told. A connection entry is a
program the machine will run, so the inspector refuses any entry that does not start
the supplied server from this work copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authority import AuthorityError, parse_config, server_entry, validate_entry  # noqa: E402
from mcp_client import McpClient, McpClientError  # noqa: E402

MUTATING_WORDS = re.compile(r"\b(add|adds|adding|remove|removes|removing|write|writes|overwrite|overwrites|replace|replaces|rewrite|rewrites|"
                            r"update|updates|delete|deletes|move|moves|rename|renames|append|appends|create|creates|set|sets)\b", re.I)
STEERING_WORDS = re.compile(r"\b(add|adding|overwrit\w*|delet\w*|remov\w*|rewrit\w*|replac\w*|edit\w*|modif\w*|updat\w*|fix|tag)\b", re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def first_sentence(text: str) -> str:
    match = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    return match.group(1) if match else text.strip()


def describe_tools(tools: list[dict]) -> list[dict]:
    rows = []
    for tool in tools:
        annotations = tool.get("annotations") or {}
        claims = annotations.get("readOnlyHint") is True
        verbs = sorted({word.lower() for word in MUTATING_WORDS.findall(tool.get("description", ""))})
        mutates = (not claims) or bool(verbs)
        rows.append({"name": tool["name"], "claims_read_only": claims, "mutates": mutates, "description": tool.get("description", ""), "verbs": verbs})
    return rows


def find_findings(tool_rows: list[dict], instructions: str) -> list[dict]:
    findings = []
    for row in tool_rows:
        if row["claims_read_only"] and row["verbs"]:
            findings.append({"code": "ANNOTATION_CLAIMS_READ_ONLY_BUT_DESCRIBES_CHANGE", "tool": row["name"],
                             "detail": f"{row['name']} is marked read-only, but its own description mentions: {', '.join(row['verbs'])}. "
                                       "A harness that trusts the mark may approve it without asking."})
    mutating_names = [row["name"] for row in tool_rows if row["mutates"]]
    named = sorted(name for name in mutating_names if re.search(rf"\b{re.escape(name)}\b", instructions))
    bare = instructions
    for name in mutating_names:
        bare = re.sub(rf"\b{re.escape(name)}\b", " ", bare)
    verbs = sorted({word.lower() for word in STEERING_WORDS.findall(bare)})
    if named or verbs:
        parts = []
        if named:
            parts.append("it tells the model to use " + ", ".join(named))
        if verbs:
            parts.append("its wording asks for: " + ", ".join(verbs))
        findings.append({"code": "INSTRUCTIONS_STEER_WRITES", "tool": None,
                         "detail": "The server's instructions go into the model's prompt. " + "; ".join(parts).capitalize() + "."})
    return findings


def inspect(config_path: Path, server: str) -> dict:
    config_bytes = config_path.read_bytes()
    config = parse_config(config_bytes.decode("utf-8"))
    work = config_path.resolve().parent
    entry = server_entry(config, server)
    parsed = validate_entry(entry, work)
    argv = [sys.executable, str(parsed["script"]), *entry["args"][1:]]
    client = McpClient(argv, cwd=str(work))
    try:
        info = client.initialize("course-inspector")
        tools = client.list_tools()
    finally:
        client.close()
    rows = describe_tools(tools)
    instructions = info.get("instructions", "") or ""
    return {
        "schema_version": 1,
        "inspected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "config_sha256": sha256_bytes(config_bytes),
        "server": {"name": info.get("serverInfo", {}).get("name"), "version": info.get("serverInfo", {}).get("version"), "protocol": info.get("protocolVersion")},
        "instructions": instructions,
        "instructions_sha256": sha256_bytes(instructions.encode("utf-8")),
        "script_sha256": sha256_bytes(parsed["script"].read_bytes()),
        "tools": [{"name": r["name"], "claims_read_only": r["claims_read_only"], "mutates": r["mutates"], "description": r["description"]} for r in rows],
        "findings": find_findings(rows, instructions),
    }


def render(report: dict) -> str:
    lines = [f"Server: {report['server']['name']} {report['server']['version']} (protocol {report['server']['protocol']})", "",
             "What this server tells the model (its instructions):"]
    lines += [f"  {line}" for line in (report["instructions"] or "(none)").splitlines()]
    lines += ["", f"Tools ({len(report['tools'])})", f"  {'name':<22}{'claims read-only':<19}{'can change notes':<18}description"]
    for tool in report["tools"]:
        lines.append(f"  {tool['name']:<22}{'yes' if tool['claims_read_only'] else 'no':<19}{'yes' if tool['mutates'] else 'no':<18}{first_sentence(tool['description'])}")
    lines += ["", "FINDINGS"]
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(f"  {finding['code']}" + (f"  {finding['tool']}" if finding["tool"] else ""))
            lines.append(f"    {finding['detail']}")
    else:
        lines.append("  none")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--server", default="vault")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.out is not None and (args.out.exists() or args.out.is_symlink()):
            raise AuthorityError(f"{args.out} already exists; choose a new file so the first inspection is kept")
        report = inspect(args.config, args.server)
    except (AuthorityError, McpClientError, OSError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    if args.out is not None:
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else render(report))
    if args.out is not None:
        print(f"\nSaved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
