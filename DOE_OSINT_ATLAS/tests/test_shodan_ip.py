"""
Tests for per-IP Shodan enrichment module.

Run: python -m pytest tests/test_shodan_ip.py -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osint.shodan_ip import (
    screen_ip_internetdb,
    screen_ips_internetdb,
    enrich_ip_shodan,
    collect_onprem_ips,
    enrich_contractor_ips,
    _compute_aggregate,
)


# ═══════════════════════════════════════════════════════════════
# InternetDB SCREENING TESTS
# ═══════════════════════════════════════════════════════════════

class TestInternetDBScreening(unittest.TestCase):

    def _mock_client(self, status_code, json_data=None):
        """Create a mock httpx client."""
        client = MagicMock()
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data or {}
        client.get.return_value = response
        return client

    def test_screen_ip_with_open_ports(self):
        client = self._mock_client(200, {
            "ip": "1.2.3.4",
            "ports": [80, 443, 22],
            "hostnames": ["server.example.com"],
            "cpes": ["cpe:/a:apache:http_server:2.4"],
            "vulns": ["CVE-2021-44228"],
            "tags": [],
        })
        result = screen_ip_internetdb("1.2.3.4", client=client)
        self.assertIsNotNone(result)
        self.assertEqual(result["ip"], "1.2.3.4")
        self.assertEqual(result["ports"], [80, 443, 22])
        self.assertEqual(result["vulns"], ["CVE-2021-44228"])

    def test_screen_ip_not_found(self):
        client = self._mock_client(404)
        result = screen_ip_internetdb("10.0.0.1", client=client)
        self.assertIsNone(result)

    def test_screen_ip_no_ports(self):
        client = self._mock_client(200, {
            "ip": "1.2.3.4",
            "ports": [],
            "hostnames": [],
            "cpes": [],
            "vulns": [],
            "tags": [],
        })
        result = screen_ip_internetdb("1.2.3.4", client=client)
        self.assertIsNotNone(result)
        self.assertEqual(result["ports"], [])

    def test_screen_ip_server_error(self):
        client = self._mock_client(500)
        result = screen_ip_internetdb("1.2.3.4", client=client)
        self.assertIsNone(result)

    def test_screen_bulk_filters_portless(self):
        """screen_ips_internetdb only returns IPs with open ports."""
        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            ip = url.split("/")[-1]
            if ip == "1.1.1.1":
                resp.status_code = 200
                resp.json.return_value = {"ports": [80, 443], "hostnames": [], "cpes": [], "vulns": [], "tags": []}
            elif ip == "2.2.2.2":
                resp.status_code = 200
                resp.json.return_value = {"ports": [], "hostnames": [], "cpes": [], "vulns": [], "tags": []}
            else:
                resp.status_code = 404
            return resp

        client = MagicMock()
        client.get = mock_get

        results = screen_ips_internetdb(
            ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
            client=client,
            delay=0,
        )

        self.assertEqual(len(results), 1)
        self.assertIn("1.1.1.1", results)
        self.assertNotIn("2.2.2.2", results)  # No ports
        self.assertNotIn("3.3.3.3", results)  # 404


# ═══════════════════════════════════════════════════════════════
# SHODAN PER-IP ENRICHMENT TESTS
# ═══════════════════════════════════════════════════════════════

class TestShodanIPEnrichment(unittest.TestCase):

    def _make_host_response(self):
        """Create a realistic Shodan host response."""
        return {
            "ip_str": "63.246.25.84",
            "ip": 1073552724,
            "hostnames": ["mail.example.com"],
            "domains": ["example.com"],
            "ports": [80, 443, 22],
            "org": "Example Corp",
            "isp": "Comcast",
            "asn": "AS7922",
            "os": "Ubuntu",
            "city": "Denver",
            "country_code": "US",
            "last_update": "2026-03-30T12:00:00",
            "vulns": ["CVE-2021-44228", "CVE-2024-1234"],
            "data": [
                {
                    "port": 443,
                    "transport": "tcp",
                    "product": "Apache",
                    "version": "2.4.41",
                    "os": "Ubuntu",
                    "_shodan": {"module": "https"},
                    "http": {
                        "title": "Example Corp Portal",
                        "server": "Apache/2.4.41",
                        "status": 200,
                    },
                    "ssl": {
                        "cert": {
                            "subject": {"CN": "example.com"},
                            "issuer": {"O": "Let's Encrypt"},
                            "expires": "2026-06-15T00:00:00",
                            "expired": False,
                            "extensions": [],
                        }
                    },
                },
                {
                    "port": 22,
                    "transport": "tcp",
                    "product": "OpenSSH",
                    "version": "7.6p1",
                    "os": "Ubuntu",
                    "_shodan": {"module": "ssh"},
                },
                {
                    "port": 80,
                    "transport": "tcp",
                    "product": "Apache",
                    "version": "2.4.41",
                    "_shodan": {"module": "http"},
                    "http": {
                        "title": "Redirect",
                        "server": "Apache/2.4.41",
                        "status": 301,
                    },
                },
            ],
        }

    def test_enrich_ip_basic(self):
        api = MagicMock()
        api.host.return_value = self._make_host_response()

        result = enrich_ip_shodan(api, "63.246.25.84")

        self.assertIsNotNone(result)
        self.assertEqual(result["ip"], "63.246.25.84")
        self.assertEqual(result["org"], "Example Corp")
        self.assertEqual(result["os"], "Ubuntu")
        self.assertEqual(len(result["services"]), 3)
        self.assertEqual(result["vulns"], ["CVE-2021-44228", "CVE-2024-1234"])

    def test_enrich_ip_extracts_ssl(self):
        api = MagicMock()
        api.host.return_value = self._make_host_response()

        result = enrich_ip_shodan(api, "63.246.25.84")

        https_svc = next(s for s in result["services"] if s["port"] == 443)
        self.assertEqual(https_svc["ssl_subject"], "example.com")
        self.assertEqual(https_svc["ssl_issuer"], "Let's Encrypt")
        self.assertFalse(https_svc["ssl_expired"])

    def test_enrich_ip_extracts_http(self):
        api = MagicMock()
        api.host.return_value = self._make_host_response()

        result = enrich_ip_shodan(api, "63.246.25.84")

        https_svc = next(s for s in result["services"] if s["port"] == 443)
        self.assertEqual(https_svc["http_title"], "Example Corp Portal")
        self.assertEqual(https_svc["http_server"], "Apache/2.4.41")

    def test_enrich_ip_not_found(self):
        import shodan as shodan_lib
        api = MagicMock()
        api.host.side_effect = shodan_lib.APIError("No information available for that IP.")

        result = enrich_ip_shodan(api, "192.168.1.1")
        self.assertIsNone(result)

    def test_enrich_ip_api_error(self):
        import shodan as shodan_lib
        api = MagicMock()
        api.host.side_effect = shodan_lib.APIError("Access denied")

        result = enrich_ip_shodan(api, "1.2.3.4")
        self.assertIsNone(result)


# ═══════════════════════════════════════════════════════════════
# CONTRACTOR-LEVEL ENRICHMENT TESTS
# ═══════════════════════════════════════════════════════════════

class TestContractorEnrichment(unittest.TestCase):

    def test_collect_onprem_ips(self):
        contractor = {
            "osint": {
                "onprem_network": {
                    "queried": True,
                    "on_prem_ips": ["1.1.1.1", "2.2.2.2", "1.1.1.1"],  # duplicate
                }
            }
        }
        ips = collect_onprem_ips(contractor)
        self.assertEqual(len(ips), 2)  # Deduped
        self.assertIn("1.1.1.1", ips)
        self.assertIn("2.2.2.2", ips)

    def test_collect_onprem_ips_no_data(self):
        self.assertEqual(collect_onprem_ips({}), [])
        self.assertEqual(collect_onprem_ips({"osint": {}}), [])
        self.assertEqual(collect_onprem_ips({"osint": {"onprem_network": {}}}), [])

    @patch("osint.shodan_ip.screen_ip_internetdb")
    @patch("osint.shodan_ip.enrich_ip_shodan")
    def test_enrich_contractor_full_flow(self, mock_shodan, mock_idb):
        """Test the full contractor enrichment pipeline."""
        # InternetDB says 1.1.1.1 has ports, 2.2.2.2 does not
        def idb_side_effect(ip, **kwargs):
            if ip == "1.1.1.1":
                return {"ip": "1.1.1.1", "ports": [80, 443], "hostnames": [], "cpes": [], "vulns": [], "tags": []}
            return None

        mock_idb.side_effect = idb_side_effect

        # Shodan returns data for 1.1.1.1
        mock_shodan.return_value = {
            "ip": "1.1.1.1",
            "hostnames": ["www.example.com"],
            "domains": ["example.com"],
            "org": "Example",
            "isp": "ISP",
            "asn": "AS1234",
            "os": "Linux",
            "ports": [80, 443],
            "vulns": ["CVE-2021-44228"],
            "city": "Denver",
            "country_code": "US",
            "last_update": "2026-03-30",
            "services": [
                {"port": 80, "transport": "tcp", "product": "nginx", "version": "1.18", "os": "Linux", "module": "http"},
                {"port": 443, "transport": "tcp", "product": "nginx", "version": "1.18", "os": "Linux", "module": "https"},
            ],
        }

        contractor = {
            "name": "Test Corp",
            "osint": {
                "onprem_network": {
                    "queried": True,
                    "on_prem_ips": ["1.1.1.1", "2.2.2.2"],
                }
            }
        }

        api = MagicMock()
        result = enrich_contractor_ips(api, contractor, delay=0)

        self.assertTrue(result["queried"])
        self.assertEqual(result["on_prem_ips_total"], 2)
        self.assertEqual(result["ips_with_ports"], 1)
        self.assertEqual(result["ips_enriched"], 1)
        self.assertEqual(len(result["hosts"]), 1)
        self.assertEqual(result["hosts"][0]["ip"], "1.1.1.1")
        self.assertIsInstance(result["aggregate"], dict)

    @patch("osint.shodan_ip.screen_ip_internetdb")
    def test_enrich_contractor_no_ips(self, mock_idb):
        """Contractor with no on-prem IPs returns empty result."""
        contractor = {"name": "Empty Corp", "osint": {}}
        api = MagicMock()

        result = enrich_contractor_ips(api, contractor, delay=0)

        self.assertTrue(result["queried"])
        self.assertEqual(result["on_prem_ips_total"], 0)
        self.assertEqual(result["hosts"], [])
        mock_idb.assert_not_called()

    @patch("osint.shodan_ip.screen_ip_internetdb")
    @patch("osint.shodan_ip.enrich_ip_shodan")
    def test_ip_cache_prevents_duplicate_queries(self, mock_shodan, mock_idb):
        """IP cache prevents re-querying the same IP across contractors."""
        mock_idb.return_value = {"ip": "1.1.1.1", "ports": [80], "hostnames": [], "cpes": [], "vulns": [], "tags": []}
        mock_shodan.return_value = {"ip": "1.1.1.1", "ports": [80], "services": [], "vulns": [], "hostnames": [], "domains": [], "org": "", "isp": "", "asn": "", "os": None, "city": "", "country_code": "", "last_update": ""}

        shared_cache = {}
        idb_cache = {}

        c1 = {"osint": {"onprem_network": {"queried": True, "on_prem_ips": ["1.1.1.1"]}}}
        c2 = {"osint": {"onprem_network": {"queried": True, "on_prem_ips": ["1.1.1.1"]}}}

        api = MagicMock()
        enrich_contractor_ips(api, c1, ip_cache=shared_cache, internetdb_cache=idb_cache, delay=0)
        enrich_contractor_ips(api, c2, ip_cache=shared_cache, internetdb_cache=idb_cache, delay=0)

        # Shodan should only be called once despite two contractors having the same IP
        mock_shodan.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# AGGREGATE COMPUTATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestAggregation(unittest.TestCase):

    def test_empty_hosts(self):
        agg = _compute_aggregate([])
        self.assertEqual(agg["total_services"], 0)
        self.assertEqual(agg["total_vulns"], 0)

    def test_critical_port_detection(self):
        hosts = [{
            "ip": "1.1.1.1",
            "ports": [3389, 443],
            "vulns": [],
            "os": "Windows Server 2019",
            "services": [
                {"port": 3389, "product": "Microsoft Terminal Services", "transport": "tcp"},
                {"port": 443, "product": "IIS", "transport": "tcp"},
            ],
        }]
        agg = _compute_aggregate(hosts)
        self.assertEqual(len(agg["critical_findings"]), 1)
        self.assertEqual(agg["critical_findings"][0]["service"], "RDP")
        self.assertEqual(agg["critical_findings"][0]["port"], 3389)

    def test_ssl_expiry_detection(self):
        hosts = [{
            "ip": "1.1.1.1",
            "ports": [443],
            "vulns": [],
            "services": [{
                "port": 443,
                "product": "nginx",
                "ssl_expired": True,
                "ssl_subject": "example.com",
                "ssl_expires": "2025-01-01",
            }],
        }]
        agg = _compute_aggregate(hosts)
        self.assertEqual(len(agg["ssl_issues"]), 1)
        self.assertEqual(agg["ssl_issues"][0]["issue"], "expired")

    def test_vuln_deduplication(self):
        hosts = [
            {"ip": "1.1.1.1", "ports": [80], "vulns": ["CVE-2021-44228", "CVE-2024-1234"], "services": []},
            {"ip": "2.2.2.2", "ports": [80], "vulns": ["CVE-2021-44228", "CVE-2024-5678"], "services": []},
        ]
        agg = _compute_aggregate(hosts)
        self.assertEqual(agg["total_vulns"], 3)  # Deduped: 44228, 1234, 5678

    def test_os_collection(self):
        hosts = [
            {"ip": "1.1.1.1", "ports": [], "vulns": [], "os": "Ubuntu", "services": []},
            {"ip": "2.2.2.2", "ports": [], "vulns": [], "os": "Windows Server 2019", "services": []},
            {"ip": "3.3.3.3", "ports": [], "vulns": [], "os": "Ubuntu", "services": []},
        ]
        agg = _compute_aggregate(hosts)
        self.assertEqual(len(agg["os_list"]), 2)  # Deduped


if __name__ == "__main__":
    unittest.main()
