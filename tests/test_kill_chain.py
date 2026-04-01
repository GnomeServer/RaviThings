"""
Tests for the Kill Chain Generator module.

Run: python -m pytest tests/test_kill_chain.py -v
"""

import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.kill_chain import (
    assemble_contractor_intel,
    build_kill_chain_prompt,
    generate_kill_chain,
    TECHNIQUE_MAP,
)


class TestAssembleContractorIntel(unittest.TestCase):
    """Tests for assembling contractor intelligence from OSINT data."""

    def _make_contractor(self, **overrides):
        """Build a test contractor with OSINT data."""
        c = {
            "name": "Test Corp",
            "city": "Denver",
            "state": "CO",
            "category": "IT & Cyber",
            "obligation": 5000000,
            "osint": {
                "dns": {"dmarc_policy": "not_set", "mail_provider": "On-premise"},
                "ct": {
                    "subdomains": ["mail.test.com", "vpn.test.com", "dev.test.com"],
                    "infrastructure_hints": {
                        "vpn": ["vpn.test.com"],
                        "auth": ["sso.test.com"],
                    },
                },
                "web": {"security_score": 30},
                "domain_verify": {"domain": "test.com"},
                "nvd_cvss": {"max_score": 9.8, "scores": {
                    "CVE-2021-44228": {"score": 10.0, "severity": "critical"},
                }},
                "onprem_network": {
                    "queried": True,
                    "on_prem_count": 6,
                    "on_prem_ips": ["1.1.1.1", "2.2.2.2"],
                },
                "service_risk": {"max_danger": "critical"},
                "shodan_ip": {
                    "queried": True,
                    "hosts": [{
                        "ip": "1.1.1.1",
                        "ports": [22, 443, 3389],
                        "vulns": ["CVE-2021-44228", "CVE-2023-44487"],
                        "os": "Ubuntu",
                        "services": [
                            {"port": 22, "transport": "tcp", "product": "OpenSSH", "version": "7.6"},
                            {"port": 443, "transport": "tcp", "product": "nginx", "version": "1.20",
                             "ssl_expired": True, "ssl_subject": "test.com"},
                            {"port": 3389, "transport": "tcp", "product": "Microsoft Terminal Services"},
                        ],
                    }],
                    "aggregate": {"critical_findings": [{"port": 3389, "service": "RDP"}]},
                },
            },
        }
        for k, v in overrides.items():
            c[k] = v
        return c

    def test_assembles_basic_info(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        self.assertEqual(intel["name"], "Test Corp")
        self.assertEqual(intel["city"], "Denver")
        self.assertEqual(intel["domain"], "test.com")

    def test_detects_exposed_rdp(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        rdp_vectors = [v for v in intel["vectors"] if v.get("port") == 3389]
        self.assertTrue(len(rdp_vectors) > 0)
        self.assertEqual(rdp_vectors[0]["tactic"], "Initial Access")

    def test_detects_no_dmarc(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        dmarc_vectors = [v for v in intel["vectors"] if "DMARC" in v.get("detail", "") or "DMARC" in v.get("evidence", "")]
        self.assertTrue(len(dmarc_vectors) > 0)

    def test_detects_expired_ssl(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        ssl_vectors = [v for v in intel["vectors"] if "expired" in v.get("detail", "").lower() or "expired" in v.get("evidence", "").lower()]
        self.assertTrue(len(ssl_vectors) > 0)

    def test_detects_cves(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        cve_vectors = [v for v in intel["vectors"] if v["technique"] == "T1212"]
        self.assertTrue(len(cve_vectors) > 0)
        self.assertIn("CVE", cve_vectors[0].get("evidence", ""))

    def test_detects_onprem_network(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        onprem_vectors = [v for v in intel["vectors"] if v["tactic"] == "Lateral Movement"]
        self.assertTrue(len(onprem_vectors) > 0)

    def test_detects_ct_subdomains(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        ct_vectors = [v for v in intel["vectors"] if "CT logs" in v.get("evidence", "")]
        self.assertTrue(len(ct_vectors) > 0)

    def test_empty_contractor(self):
        c = {"name": "Empty Corp", "city": "", "state": "", "obligation": 0}
        intel = assemble_contractor_intel(c)
        self.assertEqual(intel["name"], "Empty Corp")
        # May still detect "no DMARC" since dmarc defaults to empty
        self.assertEqual(intel["services_count"], 0)
        self.assertEqual(intel["vulns_count"], 0)

    def test_services_capped(self):
        """Intel should cap services to avoid oversized prompts."""
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        self.assertLessEqual(len(intel["all_services"]), 20)

    def test_vulns_capped(self):
        c = self._make_contractor()
        intel = assemble_contractor_intel(c)
        self.assertLessEqual(len(intel["all_vulns"]), 20)


class TestBuildKillChainPrompt(unittest.TestCase):
    """Tests for prompt construction."""

    def test_prompt_has_system_and_user(self):
        intel = {
            "name": "Test", "city": "DC", "state": "VA",
            "category": "IT", "domain": "test.com",
            "obligation": 1000000, "dmarc": "none",
            "web_score": 50, "onprem_count": 3,
            "services_count": 5, "vulns_count": 2,
            "ssl_issues_count": 0, "os_list": ["Linux"],
            "vectors": [], "all_services": [], "all_vulns": [],
        }
        messages = build_kill_chain_prompt(intel)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

    def test_prompt_includes_contractor_name(self):
        intel = {
            "name": "Acme Corp", "city": "DC", "state": "VA",
            "category": "IT", "domain": "acme.com",
            "obligation": 0, "dmarc": "reject",
            "web_score": 90, "onprem_count": 0,
            "services_count": 0, "vulns_count": 0,
            "ssl_issues_count": 0, "os_list": [],
            "vectors": [], "all_services": [], "all_vulns": [],
        }
        messages = build_kill_chain_prompt(intel)
        self.assertIn("Acme Corp", messages[1]["content"])

    def test_prompt_includes_vectors(self):
        intel = {
            "name": "Test", "city": "", "state": "",
            "category": "", "domain": "",
            "obligation": 0, "dmarc": "",
            "web_score": 100, "onprem_count": 0,
            "services_count": 0, "vulns_count": 0,
            "ssl_issues_count": 0, "os_list": [],
            "vectors": [{"tactic": "Initial Access", "technique": "T1190",
                         "name": "Exploit", "port": 3389, "product": "RDP", "ip": "1.1.1.1"}],
            "all_services": [], "all_vulns": [],
        }
        messages = build_kill_chain_prompt(intel)
        self.assertIn("T1190", messages[1]["content"])
        self.assertIn("3389", messages[1]["content"])


class TestGenerateKillChain(unittest.TestCase):
    """Tests for kill chain generation with mocked LLM."""

    def test_structured_output_success(self):
        import asyncio

        expected = {
            "summary": "Test kill chain",
            "risk_level": "high",
            "steps": [{"step": 1, "tactic": "Initial Access", "technique_id": "T1190",
                        "technique_name": "Exploit", "description": "Test",
                        "evidence": "Port 443", "impact": "Foothold"}],
            "remediation": [{"priority": 1, "action": "Patch", "impact": "Reduces risk"}],
        }

        client = MagicMock()
        client.chat_structured = AsyncMock(return_value=expected)

        intel = {
            "name": "Test", "city": "", "state": "",
            "category": "", "domain": "",
            "obligation": 0, "dmarc": "",
            "web_score": 100, "onprem_count": 0,
            "services_count": 0, "vulns_count": 0,
            "ssl_issues_count": 0, "os_list": [],
            "vectors": [], "all_services": [], "all_vulns": [],
        }

        result = asyncio.run(generate_kill_chain(client, intel))
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["technique_id"], "T1190")

    def test_fallback_to_regular_chat(self):
        import asyncio

        expected = {
            "summary": "Fallback chain",
            "risk_level": "medium",
            "steps": [{"step": 1, "tactic": "IA", "technique_id": "T1566",
                        "technique_name": "Phishing", "description": "Email",
                        "evidence": "DMARC", "impact": "Access"}],
            "remediation": [],
        }

        client = MagicMock()
        client.chat_structured = AsyncMock(side_effect=Exception("structured not supported"))
        client.chat = AsyncMock(return_value=json.dumps(expected))

        intel = {
            "name": "Test", "city": "", "state": "",
            "category": "", "domain": "",
            "obligation": 0, "dmarc": "",
            "web_score": 100, "onprem_count": 0,
            "services_count": 0, "vulns_count": 0,
            "ssl_issues_count": 0, "os_list": [],
            "vectors": [], "all_services": [], "all_vulns": [],
        }

        result = asyncio.run(generate_kill_chain(client, intel))
        self.assertEqual(result["risk_level"], "medium")

    def test_handles_total_failure(self):
        import asyncio

        client = MagicMock()
        client.chat_structured = AsyncMock(side_effect=Exception("API down"))
        client.chat = AsyncMock(side_effect=Exception("also down"))

        intel = {
            "name": "Test", "city": "", "state": "",
            "category": "", "domain": "",
            "obligation": 0, "dmarc": "",
            "web_score": 100, "onprem_count": 0,
            "services_count": 0, "vulns_count": 0,
            "ssl_issues_count": 0, "os_list": [],
            "vectors": [], "all_services": [], "all_vulns": [],
        }

        result = asyncio.run(generate_kill_chain(client, intel))
        self.assertIn("error", result)
        self.assertEqual(result["steps"], [])


class TestTechniqueMap(unittest.TestCase):
    """Test MITRE ATT&CK mapping completeness."""

    def test_all_entries_have_required_fields(self):
        for key, entry in TECHNIQUE_MAP.items():
            self.assertIn("tactic", entry, f"{key} missing tactic")
            self.assertIn("technique", entry, f"{key} missing technique")
            self.assertIn("name", entry, f"{key} missing name")
            self.assertIn("detail", entry, f"{key} missing detail")

    def test_technique_ids_valid_format(self):
        for key, entry in TECHNIQUE_MAP.items():
            tid = entry["technique"]
            self.assertTrue(tid.startswith("T"), f"{key}: {tid} doesn't start with T")


if __name__ == "__main__":
    unittest.main()
