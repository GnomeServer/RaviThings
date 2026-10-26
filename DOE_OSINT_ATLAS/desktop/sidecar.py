#!/usr/bin/env python3
"""Local kill-chain sidecar. Imports backend.kill_chain; does not reimplement the prompt."""
import asyncio
import copy
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _list(value):
    return value if isinstance(value, list) else []


def _dict(value):
    return value if isinstance(value, dict) else {}


def coerce(contractor):
    """Replace explicit None collections that assemble_contractor_intel iterates."""
    contractor = copy.deepcopy(contractor)
    osint = _dict(contractor.get("osint"))
    contractor["osint"] = osint
    sip = _dict(osint.get("shodan_ip"))
    osint["shodan_ip"] = sip
    sip["hosts"] = _list(sip.get("hosts"))
    for host in sip["hosts"]:
        if isinstance(host, dict):
            host["services"] = _list(host.get("services"))
            host["vulns"] = _list(host.get("vulns"))
    shodan = _dict(contractor.get("shodan"))
    contractor["shodan"] = shodan
    shodan["vulns"] = _list(shodan.get("vulns"))
    shodan["top_ports"] = _list(shodan.get("top_ports"))
    shodan["sample_hosts"] = _list(shodan.get("sample_hosts"))
    ct = osint.get("ct")
    if isinstance(ct, dict):
        hints = ct.get("infrastructure_hints")
        if not isinstance(hints, dict):
            ct["infrastructure_hints"] = {"vpn": [], "auth": []}
        else:
            hints["vpn"] = _list(hints.get("vpn"))
            hints["auth"] = _list(hints.get("auth"))
        ct["subdomains"] = _list(ct.get("subdomains"))
    if contractor.get("obligation") is None:
        contractor["obligation"] = 0
    return contractor


def scrub(result):
    blob = json.dumps(result)
    if "NoneType" in blob and "not iterable" in blob:
        return {
            "summary": "Kill chain generation failed: model returned an empty response.",
            "risk_level": "unknown",
            "steps": [],
            "remediation": [],
            "error": "model returned an empty response",
        }
    return result


def make_handler(by_index, client_factory, assemble_intel, generate_chain, generate_detail):
    """Bind request dependencies while keeping each stream local to its handler."""
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            path = self.path.rstrip("/")
            if path not in ("/kill-chain", "/step-detail"):
                self._send(404, {"error": "unknown endpoint"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError("invalid length")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("invalid body")
                index = body.get("contractor_index")
                if not isinstance(index, int) or isinstance(index, bool):
                    raise ValueError("invalid index")
            except (ValueError, UnicodeError):
                self._send(400, {"error": "invalid request"})
                return
            contractor = by_index.get(index)
            if contractor is None:
                error = {"error": "contractor not found"}
                if path == "/kill-chain":
                    error["steps"] = []
                self._send(404, error)
                return
            step = body.get("step")
            if path == "/step-detail" and not isinstance(step, dict):
                self._send(400, {"error": "step is not an object"})
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            disconnected = False

            def frame(obj):
                nonlocal disconnected
                if disconnected:
                    return
                data = (json.dumps(obj, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
                try:
                    self.wfile.write(data)
                    self.wfile.flush()
                except OSError:
                    # A disappearing view does not cancel provider work.
                    disconnected = True

            def emit(event):
                # Only public progress fields cross this boundary.
                kind = event.get("type")
                fields = {
                    "stage": ("type", "stage", "message", "model", "attempt"),
                    "delta": ("type", "text", "characters", "model"),
                    "activity": ("type", "model"),
                }.get(kind)
                if fields is None:
                    raise ValueError("invalid progress type")
                frame({key: event[key] for key in fields if key in event})

            try:
                emit({"type": "stage", "stage": "preparing", "message": "Preparing contractor evidence"})
                intel = assemble_intel(coerce(contractor))
                llm = client_factory(on_progress=emit)
                if path == "/step-detail":
                    result = asyncio.run(generate_detail(llm, intel, step, on_progress=emit))
                else:
                    result = asyncio.run(generate_chain(llm, intel, on_progress=emit))
                result = scrub(result)
                if not isinstance(result, dict):
                    raise ValueError("invalid result")
                frame({"type": "result", "result": result})
            except Exception:
                # Exceptions can include prompts, headers, and provider bodies.
                frame({"type": "error", "message": "Analysis failed. Check provider configuration and retry."})

        def log_message(self, fmt, *args):
            return

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

    return Handler


def main():
    repo = os.environ["ATLAS_REPO_ROOT"]
    port_file = os.environ["ATLAS_PORT_FILE"]
    with open(os.path.join(repo, "frontend", "static", "contractors.json")) as handle:
        contractors = json.load(handle)["contractors"]
    by_index = {c.get("id"): c for c in contractors}

    from backend.glm_client import GLMClient
    from backend.kill_chain import assemble_contractor_intel, generate_kill_chain, generate_step_detail

    Handler = make_handler(by_index, GLMClient, assemble_contractor_intel,
                           generate_kill_chain, generate_step_detail)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    with open(port_file, "w") as handle:
        handle.write(str(server.server_address[1]))
    server.serve_forever()


if __name__ == "__main__":
    main()
