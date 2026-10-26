#!/usr/bin/env python3
"""State and preservation boundaries; real Docker execution is a separate smoke."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import socket
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("n8n_local", Path(__file__).resolve().parents[1] / "scripts/n8n_local.py")
n8n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n8n)
IDENTITY = {"docker": "/approved/docker", "context": "desktop-linux", "host": "unix:///approved.sock", "engine_id": "approved-engine"}


class LifecycleBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="n8n boundary ")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / "prepared instance"
        self.addCleanup(patch.stopall)
        patch.object(n8n, "docker_binary", return_value=IDENTITY["docker"]).start()
        patch.object(n8n, "engine", return_value=IDENTITY).start()
        self.collisions = patch.object(n8n, "collisions").start()
        self.output = StringIO()
        self.redirect = redirect_stdout(self.output)
        self.redirect.__enter__()
        self.addCleanup(self.redirect.__exit__, None, None, None)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            self.port = listener.getsockname()[1]

    def prepare(self):
        n8n.prepare(self.directory, "course-test", self.port)
        return n8n.recorded(self.directory)

    def test_preparation_records_private_identity_without_disclosing_token(self):
        data, token = self.prepare()
        self.assertEqual(data["directory"], str(self.directory))
        self.assertEqual(data["engine_id"], IDENTITY["engine_id"])
        self.assertNotIn(token, self.output.getvalue())
        if os.name != "nt":
            self.assertEqual((self.directory / ".env").stat().st_mode & 0o777, 0o600)

    def test_existing_destination_is_preserved(self):
        self.directory.mkdir()
        keep = self.directory / "work"
        keep.write_bytes(b"existing workflow")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(keep.read_bytes(), b"existing workflow")
        self.assertEqual(list(self.directory.iterdir()), [keep])
        self.collisions.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX TIME_WAIT reuse")
    def test_recently_closed_connection_does_not_block_restart(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            address = listener.getsockname()
            with socket.create_connection(address) as client:
                accepted, _ = listener.accept()
                accepted.close()
                self.assertEqual(client.recv(1), b"")
        n8n.free_port(address[1])

    def test_linked_destination_and_parent_are_refused(self):
        real = self.directory.parent / "real"
        real.mkdir()
        self.directory.symlink_to(real, target_is_directory=True)
        for candidate in (self.directory, self.directory / "child"):
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                n8n.safe_directory(candidate)
        self.assertEqual(list(real.iterdir()), [])

    def test_checkout_destination_is_refused(self):
        (self.directory.parent / ".git").write_text("gitdir: elsewhere\n")
        with self.assertRaises(ValueError):
            n8n.safe_directory(self.directory)

    def test_invalid_project_and_port_do_not_create_files(self):
        for project, port in (("../other", self.port), ("-other", self.port), ("Upper", self.port), ("safe-name", 0), ("safe-name", 65536)):
            with self.subTest(project=project, port=port), self.assertRaises(ValueError):
                n8n.prepare(self.directory, project, port)
            self.assertFalse(self.directory.exists())

    def test_occupied_port_is_not_taken_over(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            self.port = listener.getsockname()[1]
            with self.assertRaises(ValueError):
                self.prepare()
            self.assertEqual(listener.getsockname()[1], self.port)
        self.assertFalse(self.directory.exists())

    def test_project_collision_does_not_create_files(self):
        self.collisions.side_effect = ValueError("existing project")
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.directory.exists())

    def test_empty_and_nonempty_overrides_are_refused_without_mutation(self):
        for name in ("DOCKER_HOST", "DOCKER_CONTEXT", "COMPOSE_FILE", "COMPOSE_PROJECT_NAME", "N8N_PORT", "N8N_RUNNERS_AUTH_TOKEN"):
            for value in ("", "unexpected"):
                with self.subTest(name=name, value=value), patch.dict(os.environ, {name: value}, clear=True):
                    with self.assertRaises(ValueError):
                        n8n.overrides()
                    self.assertEqual(os.environ[name], value)

    def test_changed_config_and_token_refuse_lifecycle_before_docker_mutation(self):
        self.prepare()
        for filename in ("compose.yaml", ".env"):
            path = self.directory / filename
            original = path.read_bytes()
            path.write_bytes(original + b"changed\n")
            with self.subTest(filename=filename), patch.object(n8n, "compose") as mutate:
                for action in ("start", "status", "stop"):
                    with self.assertRaises(ValueError):
                        n8n.lifecycle(action, self.directory)
                mutate.assert_not_called()
            path.write_bytes(original)

    def test_replaced_engine_refuses_lifecycle(self):
        self.prepare()
        with patch.object(n8n, "engine", return_value={**IDENTITY, "engine_id": "another-engine"}), patch.object(n8n, "compose") as mutate:
            with self.assertRaises(ValueError):
                n8n.lifecycle("stop", self.directory)
            mutate.assert_not_called()

    def test_linked_configuration_is_refused(self):
        self.prepare()
        config = self.directory / "compose.yaml"
        outside = self.directory.parent / "outside"
        config.rename(outside)
        config.symlink_to(outside)
        with self.assertRaises(ValueError):
            n8n.recorded(self.directory)
        self.assertTrue(outside.is_file())

    def test_starting_valid_running_instance_is_idempotent(self):
        self.prepare()
        running = [{"State": {"Status": "running"}}, {"State": {"Status": "running"}}]
        with patch.object(n8n, "inspect_project", return_value=(running, [{}], [{}])), patch.object(n8n, "compose") as mutate:
            n8n.lifecycle("start", self.directory)
            mutate.assert_not_called()

    def test_start_resumes_valid_stopped_containers(self):
        self.prepare()
        containers = [{"Config": {"Labels": {"com.docker.compose.service": service}}, "State": {"Status": "exited"}} for service in ("n8n", "runners")]
        def resume(data, action):
            if action == "up":
                for container in containers:
                    container["State"]["Status"] = "running"
        with patch.object(n8n, "inspect_project", return_value=(containers, [{}], [{}])), patch.object(n8n, "compose", side_effect=resume):
            n8n.lifecycle("start", self.directory)
            n8n.lifecycle("status", self.directory)
        self.assertEqual([c["State"]["Status"] for c in containers], ["running", "running"])

    def test_start_refuses_unhealthy_containers(self):
        self.prepare()
        containers = [{"State": {"Status": "restarting"}}, {"State": {"Status": "running"}}]
        with patch.object(n8n, "inspect_project", return_value=(containers, [{}], [{}])), patch.object(n8n, "compose") as mutate:
            with self.assertRaises(ValueError):
                n8n.lifecycle("start", self.directory)
            mutate.assert_not_called()

    def test_partial_or_stopped_runtime_does_not_report_running(self):
        self.prepare()
        for containers in ([], [{"State": {"Status": "running"}}], [{"State": {"Status": "running"}}, {"State": {"Status": "exited"}}]):
            with self.subTest(containers=containers), patch.object(n8n, "inspect_project", return_value=(containers, [{}], [{}])):
                with self.assertRaises(ValueError):
                    n8n.lifecycle("status", self.directory)

    def test_stop_requires_retained_data_volume(self):
        self.prepare()
        before = [{"State": {"Status": "running"}}, {"State": {"Status": "running"}}]
        with patch.object(n8n, "inspect_project", side_effect=[(before, [{}], [{}]), ([], [], [])]), patch.object(n8n, "compose"):
            with self.assertRaises(ValueError):
                n8n.lifecycle("stop", self.directory)

    def test_reserved_unlabelled_names_are_refused(self):
        with patch.object(n8n, "resources", return_value=([], [], [])), patch.object(n8n, "names", return_value={"course-test_n8n_data"}):
            with self.assertRaises(ValueError):
                # Call the original function rather than the preparation stub.
                original_collisions(IDENTITY["docker"], "course-test")

    def test_named_volume_is_accepted_but_host_mount_and_privilege_are_refused(self):
        data, token = self.prepare()
        project = data["project"]
        volume = project + "_n8n_data"
        network = project + "_default"
        containers = []
        for service, image in (("n8n", "n8nio/n8n:2.41.5"), ("runners", "ghcr.io/n8n-io/runners:2.41.5")):
            ports = {"5678/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(self.port)}]} if service == "n8n" else {}
            environment = [f"N8N_RUNNERS_AUTH_TOKEN={token}"]
            environment += (["N8N_RUNNERS_MODE=external", "N8N_RUNNERS_BROKER_LISTEN_ADDRESS=0.0.0.0", "N8N_DIAGNOSTICS_ENABLED=false", f"N8N_WEBHOOK_URL=http://localhost:{self.port}/"] if service == "n8n" else ["N8N_RUNNERS_TASK_BROKER_URI=http://n8n:5679"])
            containers.append({
                "Name": f"/{project}-{service}-1",
                "Config": {"Image": image, "Env": environment, "Labels": {"com.docker.compose.project": project, "com.docker.compose.service": service}},
                "HostConfig": {"Privileged": False, "NetworkMode": network, "PortBindings": ports, "Binds": [f"{volume}:/home/node/.n8n:rw"] if service == "n8n" else None},
                "Mounts": [{"Type": "volume", "Name": volume, "Destination": "/home/node/.n8n"}] if service == "n8n" else [],
                "State": {"Status": "running"},
                "NetworkSettings": {"Ports": ports},
            })
        volumes = [{"Name": volume, "Driver": "local", "Labels": {"com.docker.compose.volume": "n8n_data"}}]
        networks = [{"Name": network, "Labels": {"com.docker.compose.network": "default"}}]
        names = {"container": {f"{project}-n8n-1", f"{project}-runners-1"}, "volume": {volume}, "network": {network}}
        with patch.object(n8n, "resources", return_value=(containers, volumes, networks)), patch.object(n8n, "names", side_effect=lambda _, kind: names[kind]):
            observed, _, _ = n8n.inspect_project(data, token)
            self.assertEqual({c["Name"] for c in observed}, {"/" + name for name in names["container"]})
            for index, section, key, value in (
                (0, "Mounts", None, [{"Type": "bind", "Source": "/private", "Destination": "/home/node/.n8n"}]),
                (0, "Config", "Env", containers[0]["Config"]["Env"] + ["N8N_WEBHOOK_URL=http://localhost:1/"]),
                (1, "HostConfig", "Privileged", True),
                (1, "HostConfig", "PortBindings", {"5680/tcp": [{"HostIp": "0.0.0.0", "HostPort": "5680"}]}),
                (1, "Mounts", None, [{"Type": "bind", "Source": "/var/run/docker.sock", "Destination": "/var/run/docker.sock"}]),
            ):
                previous = copy.deepcopy(containers[index])
                if key is None:
                    containers[index][section] = value
                else:
                    containers[index][section][key] = value
                with self.subTest(section=section, key=key), self.assertRaises(ValueError):
                    n8n.inspect_project(data, token)
                containers[index] = previous


original_collisions = n8n.collisions

if __name__ == "__main__":
    unittest.main()
