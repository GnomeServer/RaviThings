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


def main():
    repo = os.environ["ATLAS_REPO_ROOT"]
    port_file = os.environ["ATLAS_PORT_FILE"]
    with open(os.path.join(repo, "frontend", "static", "contractors.json")) as handle:
        contractors = json.load(handle)["contractors"]
    by_index = {c.get("id"): c for c in contractors}

    from backend.glm_client import GLMClient
    from backend.kill_chain import assemble_contractor_intel, generate_kill_chain, generate_step_detail

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            contractor = by_index.get(body.get("contractor_index"))
            if contractor is None:
                if self.path.rstrip("/") == "/step-detail":
                    self._send(404, {"error": "contractor not found"})
                else:
                    self._send(404, {"error": "contractor not found", "steps": []})
                return
            intel = assemble_contractor_intel(coerce(contractor))
            if self.path.rstrip("/") == "/step-detail":
                step = body.get("step")
                if not isinstance(step, dict):
                    self._send(400, {"error": "step is not an object"})
                    return
                result = asyncio.run(generate_step_detail(GLMClient(), intel, step))
                self._send(200, scrub(result))
                return
            # /kill-chain (and default) - original behavior and error shape preserved
            result = asyncio.run(generate_kill_chain(GLMClient(), intel))
            self._send(200, scrub(result))
        def log_message(self, fmt, *args):
            return

        def _send(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    with open(port_file, "w") as handle:
        handle.write(str(server.server_address[1]))
    server.serve_forever()


if __name__ == "__main__":
    main()
