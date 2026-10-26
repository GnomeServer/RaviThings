#!/usr/bin/env python3
"""Preflight admission boundaries; no model, credentials or fixed port needed."""
from collections import namedtuple
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_readiness as readiness


class ReadinessTests(unittest.TestCase):
    def test_physical_memory_boundaries_never_claim_model_performance(self):
        gib = readiness.GIB
        for amount, expected in ((16 * gib - 1, "HOLD"), (16 * gib, "CONDITIONAL"), (24 * gib - 1, "CONDITIONAL"), (24 * gib, "PLANNING_FLOOR_MET")):
            with self.subTest(bytes=amount):
                self.assertEqual(readiness.memory_band(amount), expected)

    def test_download_policy_checks_each_destination_and_not_a_second_weight_allocation(self):
        usage = namedtuple("Usage", "total used free")
        with tempfile.TemporaryDirectory(prefix="capacity with spaces ") as temporary:
            root = Path(temporary)
            work = root / "new work"
            cache = root / "separate cache"
            cache.mkdir()
            environment = {"HF_HOME": str(cache)}
            for free, expected in ((35 * readiness.GIB - 1, "HOLD"), (35 * readiness.GIB, "PASS")):
                with self.subTest(free=free), patch.object(readiness.shutil, "disk_usage", return_value=usage(100 * readiness.GIB, 100 * readiness.GIB - free, free)):
                    rows = readiness.observe_storage(work, environment, False)
                    self.assertEqual({row["status"] for row in rows}, {expected})
                    after = readiness.observe_storage(work, environment, True)
                    self.assertEqual({row["status"] for row in after}, {"PASS"})
            self.assertFalse(work.exists(), "observing capacity created a work folder")

    def test_low_separate_cache_holds_even_when_work_volume_has_space(self):
        usage = namedtuple("Usage", "total used free")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            work, cache = root / "work", root / "cache"
            work.mkdir()
            cache.mkdir()
            def disk(path):
                free = 34 * readiness.GIB if path == cache else 50 * readiness.GIB
                return usage(100 * readiness.GIB, 100 * readiness.GIB - free, free)
            with patch.object(readiness.shutil, "disk_usage", side_effect=disk):
                rows = readiness.observe_storage(work, {"HF_XET_CACHE": str(cache)}, False)
            self.assertEqual({row["destination"]: row["status"] for row in rows}, {"work/weights": "PASS", "HF Xet cache": "HOLD"})
            with patch.object(readiness.shutil, "disk_usage", side_effect=disk):
                unused_hub = readiness.observe_storage(work, {"HF_HUB_CACHE": str(cache), "HF_XET_CACHE": str(work)}, False)
            self.assertEqual({row["status"] for row in unused_hub}, {"PASS"}, "--local-dir does not allocate weights in the Hub cache")

    def test_file_in_destination_path_is_not_treated_as_a_usable_volume(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "weights"
            file.write_bytes(b"not a directory")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                readiness.existing_volume_path(file / "nested download")

    def test_occupied_endpoint_refuses_without_disrupting_its_listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as owned:
            owned.bind((readiness.LOOPBACK, 0))
            owned.listen()
            port = owned.getsockname()[1]
            with self.assertRaisesRegex(ValueError, "occupied or unavailable"):
                readiness.require_free_endpoint(port)
            with socket.create_connection((readiness.LOOPBACK, port), timeout=2) as client:
                connection, _ = owned.accept()
                with connection:
                    connection.sendall(b"still owned")
                    self.assertEqual(client.recv(32), b"still owned")
                    client.shutdown(socket.SHUT_WR)
                    self.assertEqual(connection.recv(1), b"")
                    connection.shutdown(socket.SHUT_WR)
                    self.assertEqual(client.recv(1), b"")
        readiness.require_free_endpoint(port)

    def test_explicit_missing_tool_does_not_fall_back_to_a_different_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "not executable"):
                readiness.observe_tool("hf", str(Path(temporary) / "missing approved hf"))


if __name__ == "__main__":
    unittest.main()
