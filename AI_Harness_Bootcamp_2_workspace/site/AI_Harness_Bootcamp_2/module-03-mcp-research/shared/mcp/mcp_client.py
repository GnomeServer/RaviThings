#!/usr/bin/env python3
"""A minimal MCP client for local stdio servers (standard library only).

It starts one server process, sends newline-delimited JSON-RPC messages, and reads the
replies. The inspector, the authority probe, and the tests use it so they talk to the
server exactly as a harness would.
"""
from __future__ import annotations

import json
import queue
import subprocess
import threading


class McpClientError(RuntimeError):
    pass


class McpClient:
    def __init__(self, argv, *, cwd=None, env=None, timeout: float = 20.0):
        self.timeout = timeout
        self.process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding="utf-8", shell=False)
        self.lines: queue.Queue = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def notify(self, method: str, params=None) -> None:
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def request(self, method: str, params=None) -> dict:
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except OSError as error:
            raise McpClientError(f"the server closed its input: {error}") from None
        while True:
            try:
                line = self.lines.get(timeout=self.timeout)
            except queue.Empty:
                raise McpClientError(f"the server did not answer {method} within {self.timeout:g} seconds") from None
            if line is None:
                raise McpClientError(f"the server exited before answering {method}")
            if not line.strip():
                continue
            try:
                reply = json.loads(line)
            except json.JSONDecodeError:
                raise McpClientError(f"the server sent a line that is not JSON: {line[:80]!r}") from None
            if reply.get("id") == self.next_id:
                return reply

    def initialize(self, client_name: str = "course-client", client_version: str = "1") -> dict:
        reply = self.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": client_name, "version": client_version}})
        if "result" not in reply:
            raise McpClientError(f"initialize failed: {reply.get('error')}")
        self.notify("notifications/initialized")
        return reply["result"]

    def list_tools(self) -> list[dict]:
        reply = self.request("tools/list")
        if "result" not in reply:
            raise McpClientError(f"tools/list failed: {reply.get('error')}")
        return reply["result"]["tools"]

    def call(self, name: str, arguments=None) -> dict:
        """Return {"rpc_error": str|None, "is_error": bool, "text": str}."""
        reply = self.request("tools/call", {"name": name, "arguments": arguments if arguments is not None else {}})
        if "error" in reply:
            return {"rpc_error": reply["error"].get("message", "error"), "is_error": True, "text": ""}
        result = reply["result"]
        text = "".join(block.get("text", "") for block in result.get("content", []) if block.get("type") == "text")
        return {"rpc_error": None, "is_error": bool(result.get("isError")), "text": text}

    def close(self) -> tuple[int, str]:
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        return self.process.returncode, self.process.stderr.read()
