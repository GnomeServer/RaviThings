"""HTTP stream boundaries: early delivery, safe failure, request rejection."""
import http.client
import json
import threading
import unittest
from contextlib import contextmanager
from http.server import ThreadingHTTPServer

from desktop.sidecar import make_handler


@contextmanager
def sidecar(generate):
    handler = make_handler(
        {1: {"id": 1}}, lambda **kwargs: object(), lambda value: value,
        generate, generate,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(*server.server_address, timeout=3)
    try:
        yield connection
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class SidecarProgressTests(unittest.TestCase):
    def test_progress_arrives_before_generation_finishes(self):
        release = threading.Event()
        entered = threading.Event()

        async def generate(llm, intel, *, on_progress):
            on_progress({"type": "delta", "text": "é🌎", "characters": 2})
            entered.set()
            if not release.wait(5):
                raise RuntimeError("test did not release generation")
            return {"summary": "done", "steps": []}

        with sidecar(generate) as connection:
            try:
                connection.request("POST", "/kill-chain", json.dumps({"contractor_index": 1}))
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("Content-Type"), "application/x-ndjson")
                self.assertTrue(entered.wait(2))
                self.assertEqual(json.loads(response.readline())["stage"], "preparing")
                self.assertEqual(json.loads(response.readline())["text"], "é🌎")
                release.set()
                terminal = json.loads(response.readline())
                self.assertEqual(terminal["type"], "result")
                self.assertEqual(terminal["result"]["summary"], "done")
                self.assertEqual(response.read(), b"")
            finally:
                release.set()

    def test_exception_is_one_safe_error_terminal(self):
        async def generate(llm, intel, *, on_progress):
            raise RuntimeError("secret-key private prompt provider body")

        with sidecar(generate) as connection:
            connection.request("POST", "/kill-chain", json.dumps({"contractor_index": 1}))
            response = connection.getresponse()
            raw = response.read()
            frames = [json.loads(line) for line in raw.splitlines()]
            self.assertEqual([frame["type"] for frame in frames], ["stage", "error"])
            self.assertNotIn(b"secret-key", raw)
            self.assertNotIn(b"private prompt", raw)

    def test_invalid_requests_fail_before_streaming(self):
        async def generate(*args, **kwargs):
            self.fail("invalid request reached provider")

        for path, body, status in [
            ("/kill-chain", "{", 400),
            ("/kill-chain", "[]", 400),
            ("/kill-chain", '{"contractor_index": []}', 400),
            ("/kill-chain", '{"contractor_index": 99}', 404),
            ("/step-detail", '{"contractor_index": 1, "step": null}', 400),
            ("/unknown", '{"contractor_index": 1}', 404),
        ]:
            with self.subTest(path=path, body=body), sidecar(generate) as connection:
                connection.request("POST", path, body)
                response = connection.getresponse()
                self.assertEqual(response.status, status)
                self.assertEqual(response.getheader("Content-Type"), "application/json")
                self.assertIn("error", json.loads(response.read()))
