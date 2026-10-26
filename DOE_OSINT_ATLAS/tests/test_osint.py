"""
Comprehensive test suite for the multi-layer OSINT enrichment pipeline.

Tests each layer independently with mocked external calls, plus integration
tests that verify the full pipeline data flow.

Run: python -m pytest tests/test_osint.py -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════
# DOMAIN DISCOVERY TESTS
# ═══════════════════════════════════════════════════════════════

class TestDomainDiscovery(unittest.TestCase):

    def test_extract_domain_from_url_basic(self):
        from osint.domain_discovery import extract_domain_from_url
        self.assertEqual(extract_domain_from_url('https://www.lockheedmartin.com/en-us'), 'lockheedmartin.com')
        self.assertEqual(extract_domain_from_url('http://boeing.com'), 'boeing.com')
        self.assertEqual(extract_domain_from_url('https://www.example.org/path?q=1'), 'example.org')

    def test_extract_domain_from_url_edge_cases(self):
        from osint.domain_discovery import extract_domain_from_url
        self.assertIsNone(extract_domain_from_url(''))
        self.assertIsNone(extract_domain_from_url(None))
        self.assertIsNone(extract_domain_from_url('no'))

    def test_generate_domain_guesses(self):
        from osint.domain_discovery import generate_domain_guesses
        guesses = generate_domain_guesses('Lockheed Martin Corp')
        self.assertIn('lockheedmartin.com', guesses)
        self.assertIn('lockheed-martin.com', guesses)

    def test_generate_domain_guesses_strips_suffixes(self):
        from osint.domain_discovery import generate_domain_guesses
        guesses = generate_domain_guesses('Booz Allen Hamilton Inc')
        for g in guesses:
            self.assertNotIn('inc', g.split('.')[0].split('-'))

    def test_generate_domain_guesses_empty(self):
        from osint.domain_discovery import generate_domain_guesses
        self.assertEqual(generate_domain_guesses(''), [])
        self.assertEqual(generate_domain_guesses('LLC'), [])

    def test_generate_domain_guesses_no_duplicates(self):
        from osint.domain_discovery import generate_domain_guesses
        guesses = generate_domain_guesses('Test Company LLC')
        self.assertEqual(len(guesses), len(set(guesses)))

    @patch('osint.domain_discovery.probe_domain')
    def test_discover_domain_from_url(self, mock_probe):
        from osint.domain_discovery import discover_domain
        mock_probe.return_value = True
        result = discover_domain({'name': 'Test', 'url': 'https://test.com', 'dba': ''})
        self.assertEqual(result['domain'], 'test.com')
        self.assertEqual(result['source'], 'csv_url')

    @patch('osint.domain_discovery.probe_domain')
    def test_discover_domain_from_probe(self, mock_probe):
        from osint.domain_discovery import discover_domain
        mock_probe.side_effect = lambda d, **kw: d == 'boeing.com'
        result = discover_domain({'name': 'Boeing Company', 'url': '', 'dba': ''})
        self.assertIsNotNone(result['domain'])
        self.assertEqual(result['source'], 'dns_probe')

    @patch('osint.domain_discovery.probe_domain')
    def test_discover_domain_not_found(self, mock_probe):
        from osint.domain_discovery import discover_domain
        mock_probe.return_value = False
        result = discover_domain({'name': 'XYZZY Fake Corp LLC', 'url': '', 'dba': ''})
        self.assertIsNone(result['domain'])
        self.assertEqual(result['error'], 'no_domain_found')
        self.assertGreater(result['guesses_tried'], 0)


# ═══════════════════════════════════════════════════════════════
# DNS INTELLIGENCE TESTS
# ═══════════════════════════════════════════════════════════════

class TestDNSIntel(unittest.TestCase):

    def _mock_resolver(self, resolve_fn):
        """Create a mock resolver that delegates resolve() to a function."""
        mock_res = MagicMock()
        mock_res.resolve = MagicMock(side_effect=resolve_fn)
        return mock_res

    def _make_answer(self, values, rdtype='A'):
        """Create a mock DNS answer iterable."""
        records = []
        for v in values:
            rdata = MagicMock()
            if rdtype == 'MX':
                rdata.preference = v[0]
                rdata.exchange = MagicMock()
                rdata.exchange.__str__ = MagicMock(return_value=v[1])
            else:
                rdata.__str__ = MagicMock(return_value=v)
            records.append(rdata)
        answer = MagicMock()
        answer.__iter__ = MagicMock(return_value=iter(records))
        return answer

    @patch('osint.dns_intel._make_resolver')
    def test_enrich_dns_google_workspace(self, mock_make):
        from osint.dns_intel import enrich_dns
        import dns.resolver

        def resolve_fn(domain, rdtype):
            if rdtype == 'MX':
                return self._make_answer([(10, 'aspmx.l.google.com.'), (20, 'alt1.aspmx.l.google.com.')], 'MX')
            elif rdtype == 'NS':
                return self._make_answer(['ns1.cloudflare.com.', 'ns2.cloudflare.com.'])
            elif rdtype == 'TXT':
                return self._make_answer(['"v=spf1 include:_spf.google.com ~all"', '"google-site-verification=abc123"'])
            elif rdtype == 'A':
                return self._make_answer(['104.16.1.1'])
            raise dns.resolver.NoAnswer

        mock_make.return_value = self._mock_resolver(resolve_fn)
        result = enrich_dns('example.com')

        self.assertTrue(result['queried'])
        self.assertEqual(result['mail_provider'], 'Google Workspace')
        self.assertEqual(result['dns_provider'], 'Cloudflare')
        self.assertIn('Google Workspace', result['technologies_detected'])
        self.assertIn('Cloudflare', result['technologies_detected'])

    @patch('osint.dns_intel._make_resolver')
    def test_enrich_dns_microsoft(self, mock_make):
        from osint.dns_intel import enrich_dns
        import dns.resolver

        def resolve_fn(domain, rdtype):
            if rdtype == 'MX':
                return self._make_answer([(10, 'example-com.mail.protection.outlook.com.')], 'MX')
            elif rdtype == 'NS':
                return self._make_answer(['ns-1.awsdns-01.com.'])
            elif rdtype == 'TXT':
                return self._make_answer(['"v=spf1 include:spf.protection.outlook.com -all"', '"MS=ms12345"'])
            elif rdtype == 'A':
                return self._make_answer(['52.1.2.3'])
            raise dns.resolver.NoAnswer

        mock_make.return_value = self._mock_resolver(resolve_fn)
        result = enrich_dns('example.com')

        self.assertEqual(result['mail_provider'], 'Microsoft 365')
        self.assertEqual(result['dns_provider'], 'AWS Route53')
        self.assertIn('Microsoft 365', result['technologies_detected'])

    @patch('osint.dns_intel._make_resolver')
    def test_enrich_dns_handles_nxdomain(self, mock_make):
        from osint.dns_intel import enrich_dns
        import dns.resolver
        mock_res = MagicMock()
        mock_res.resolve.side_effect = dns.resolver.NXDOMAIN
        mock_make.return_value = mock_res
        result = enrich_dns('nonexistent.invalid')
        self.assertTrue(result['queried'])
        # All 6 lookups fail -> error should be set
        self.assertIsNotNone(result.get('error'))

    @patch('osint.dns_intel._make_resolver')
    def test_enrich_dns_empty_domain(self, mock_make):
        from osint.dns_intel import enrich_dns
        import dns.resolver
        mock_res = MagicMock()
        mock_res.resolve.side_effect = dns.resolver.NXDOMAIN
        mock_make.return_value = mock_res
        result = enrich_dns('')
        self.assertTrue(result['queried'])
        # Empty domain will fail all lookups
        self.assertIsNotNone(result.get('error'))

    @patch('osint.dns_intel._make_resolver')
    def test_dns_partial_failure(self, mock_make):
        """DNS should return partial results if only some record types fail."""
        from osint.dns_intel import enrich_dns
        import dns.resolver

        def resolve_fn(domain, rdtype):
            if rdtype == 'A':
                return self._make_answer(['1.2.3.4'])
            raise dns.resolver.NoAnswer

        mock_make.return_value = self._mock_resolver(resolve_fn)
        result = enrich_dns('partial.example.com')

        self.assertEqual(result['a_records'], ['1.2.3.4'])
        # Partial failure: not all 6 lookups failed, so error should be None
        self.assertIsNone(result.get('error'))


# ═══════════════════════════════════════════════════════════════
# CT LOG TESTS
# ═══════════════════════════════════════════════════════════════

class TestCTLogs(unittest.TestCase):

    @patch('osint.ct_logs.requests.get')
    def test_enrich_ct_basic(self, mock_get):
        from osint.ct_logs import enrich_ct

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {'name_value': 'www.example.com\nmail.example.com', 'issuer_name': "C=US, O=Let's Encrypt"},
            {'name_value': 'vpn.example.com', 'issuer_name': 'C=US, O=DigiCert Inc'},
            {'name_value': 'jenkins.example.com', 'issuer_name': "C=US, O=Let's Encrypt"},
            {'name_value': '*.example.com', 'issuer_name': "C=US, O=Let's Encrypt"},
            {'name_value': 'sso.example.com', 'issuer_name': 'C=US, O=DigiCert Inc'},
        ]
        mock_get.return_value = mock_response

        result = enrich_ct('example.com')

        self.assertTrue(result['queried'])
        self.assertGreater(result['subdomain_count'], 0)
        self.assertIn('vpn.example.com', result['infrastructure_hints']['vpn'])
        self.assertIn('mail.example.com', result['infrastructure_hints']['email'])
        self.assertIn('jenkins.example.com', result['infrastructure_hints']['dev_ci'])
        self.assertIn('sso.example.com', result['infrastructure_hints']['auth'])
        self.assertNotIn('*.example.com', result['unique_subdomains'])

    @patch('osint.ct_logs.requests.get')
    def test_enrich_ct_no_certs(self, mock_get):
        from osint.ct_logs import enrich_ct
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        result = enrich_ct('nocerts.example.com')
        self.assertEqual(result['subdomain_count'], 0)

    @patch('osint.ct_logs.requests.get')
    def test_enrich_ct_handles_timeout(self, mock_get):
        from osint.ct_logs import enrich_ct
        import requests
        mock_get.side_effect = requests.exceptions.Timeout('timeout')
        result = enrich_ct('timeout.example.com')
        self.assertIsNotNone(result.get('error'))

    @patch('osint.ct_logs.requests.get')
    def test_enrich_ct_rate_limit_retry(self, mock_get):
        from osint.ct_logs import enrich_ct

        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.raise_for_status = MagicMock()
        success.json.return_value = [
            {'name_value': 'www.example.com', 'issuer_name': "C=US, O=Let's Encrypt"},
        ]

        mock_get.side_effect = [rate_limited, success]
        result = enrich_ct('example.com')
        self.assertGreater(result['subdomain_count'], 0)

    def test_enrich_ct_empty_domain(self):
        from osint.ct_logs import enrich_ct
        result = enrich_ct('')
        self.assertIsNotNone(result.get('error'))

    @patch('osint.ct_logs.requests.get')
    def test_ct_handles_malformed_json(self, mock_get):
        from osint.ct_logs import enrich_ct
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError('bad', '', 0)
        mock_get.return_value = mock_response
        result = enrich_ct('example.com')
        self.assertIsNotNone(result.get('error'))


# ═══════════════════════════════════════════════════════════════
# WEB FINGERPRINTING TESTS
# ═══════════════════════════════════════════════════════════════

class TestWebFingerprint(unittest.TestCase):

    def _make_mock_response(self, headers, body='', status=200, url='https://example.com/', cookies=None):
        """Create a properly structured mock HTTP response."""
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.url = url
        mock_resp.headers = headers  # plain dict — module does dict(resp.headers)
        mock_resp.text = body
        # Mock cookies as an iterable of cookie objects with .name
        cookie_list = []
        for name in (cookies or []):
            c = MagicMock()
            c.name = name
            cookie_list.append(c)
        mock_resp.cookies = cookie_list
        return mock_resp

    @patch('osint.web_fingerprint.requests.get')
    def test_enrich_web_wordpress(self, mock_get):
        from osint.web_fingerprint import enrich_web

        headers = {
            'Server': 'Apache/2.4.41',
            'X-Powered-By': 'PHP/7.4',
            'Strict-Transport-Security': 'max-age=31536000',
            'X-Frame-Options': 'SAMEORIGIN',
        }
        body = '<html><head><meta name="generator" content="WordPress 6.2"><link href="/wp-content/themes/flavor/style.css"></head><body></body></html>'

        mock_get.return_value = self._make_mock_response(
            headers, body, cookies=['wordpress_logged_in_abc']
        )
        result = enrich_web('example.com')

        self.assertTrue(result['queried'])
        self.assertIn('WordPress', result['technologies_detected'])
        self.assertTrue(any('Apache' in t for t in result['technologies_detected']))
        self.assertGreater(result['security_score'], 0)

    @patch('osint.web_fingerprint.requests.get')
    def test_enrich_web_cloudflare_react(self, mock_get):
        from osint.web_fingerprint import enrich_web

        headers = {
            'Server': 'cloudflare',
            'cf-ray': '12345-IAD',
            'Content-Security-Policy': "default-src 'self'",
            'X-Content-Type-Options': 'nosniff',
            'Strict-Transport-Security': 'max-age=31536000',
        }
        body = '<html><body><div id="root"></div><script>window.__REACT_DEVTOOLS_GLOBAL_HOOK__</script></body></html>'

        mock_get.return_value = self._make_mock_response(
            headers, body, url='https://app.example.com/'
        )
        result = enrich_web('app.example.com')

        self.assertEqual(result['cdn_detected'], 'Cloudflare')
        # Module may return lowercase 'react'
        self.assertTrue(any('react' in f.lower() for f in result['js_frameworks']))
        self.assertGreater(result['security_score'], 0)

    @patch('osint.web_fingerprint.requests.get')
    def test_enrich_web_handles_connection_error(self, mock_get):
        from osint.web_fingerprint import enrich_web
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError('refused')
        result = enrich_web('unreachable.example.com')
        self.assertIsNotNone(result.get('error'))

    def test_enrich_web_empty_domain(self):
        from osint.web_fingerprint import enrich_web
        result = enrich_web('')
        self.assertIsNotNone(result.get('error'))


# ═══════════════════════════════════════════════════════════════
# ENHANCED SHODAN TESTS
# ═══════════════════════════════════════════════════════════════

class TestEnhancedShodan(unittest.TestCase):

    def _make_api(self, count_result=None, search_result=None, error=None):
        api = MagicMock()
        if error:
            api.count.side_effect = error
            api.search.side_effect = error
        else:
            api.count.return_value = count_result or {'total': 0, 'facets': {}}
            api.search.return_value = search_result or {'matches': []}
        return api

    def test_enrich_shodan_by_org_name(self):
        from osint.enhanced_shodan import enrich_shodan
        api = self._make_api(
            count_result={
                'total': 42,
                'facets': {
                    'port': [{'value': 443, 'count': 30}, {'value': 80, 'count': 12}],
                    'product': [{'value': 'nginx', 'count': 25}],
                    'vuln': [],
                    'domain': [{'value': 'example.com'}],
                    'asn': [{'value': 'AS12345'}],
                }
            },
            search_result={
                'matches': [{
                    'ip_str': '1.2.3.4', 'port': 443, 'product': 'nginx',
                    'version': '1.21', 'hostnames': ['www.example.com'],
                    'os': 'Ubuntu', 'transport': 'tcp',
                }]
            }
        )
        result = enrich_shodan(api, {'name': 'Example Corp LLC', 'url': '', 'dba': ''})
        self.assertEqual(result['total_hosts'], 42)
        self.assertEqual(len(result['top_ports']), 2)
        self.assertIn('org:', result['query_used'])

    def test_enrich_shodan_fallback_to_ssl(self):
        from osint.enhanced_shodan import enrich_shodan

        def count_side_effect(query, facets=None):
            if 'org:' in query:
                return {'total': 0, 'facets': {}}
            elif 'ssl.cert.subject.O:' in query:
                return {
                    'total': 5,
                    'facets': {
                        'port': [{'value': 443, 'count': 5}],
                        'product': [], 'vuln': [], 'domain': [], 'asn': [],
                    }
                }
            return {'total': 0, 'facets': {}}

        api = MagicMock()
        api.count.side_effect = count_side_effect
        api.search.return_value = {'matches': []}

        result = enrich_shodan(api, {'name': 'Small Company LLC', 'url': '', 'dba': ''})
        self.assertEqual(result['total_hosts'], 5)
        self.assertIn('ssl.cert.subject.O:', result['query_used'])

    def test_enrich_shodan_no_results(self):
        from osint.enhanced_shodan import enrich_shodan
        api = self._make_api()
        result = enrich_shodan(api, {'name': 'Ghost Corp', 'url': '', 'dba': ''})
        self.assertEqual(result['total_hosts'], 0)

    def test_enrich_shodan_handles_api_error(self):
        from osint.enhanced_shodan import enrich_shodan
        import shodan
        api = self._make_api(error=shodan.APIError('Access denied'))
        result = enrich_shodan(api, {'name': 'Test', 'url': '', 'dba': ''})
        self.assertIsNotNone(result.get('error'))

    def test_clean_org_name(self):
        from osint.enhanced_shodan import clean_org_name
        self.assertEqual(clean_org_name('Lockheed Martin Corp'), 'Lockheed Martin')
        self.assertEqual(clean_org_name('BOEING COMPANY'), 'BOEING')
        self.assertEqual(clean_org_name('Test LLC'), 'Test')
        self.assertIsNone(clean_org_name(''))
        self.assertIsNone(clean_org_name('LLC'))


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestPipelineIntegration(unittest.TestCase):

    def test_domain_discovery_feeds_dns(self):
        from osint.domain_discovery import discover_domain
        with patch('osint.domain_discovery.probe_domain', return_value=True):
            dd_result = discover_domain({'name': 'Test', 'url': 'https://example.com', 'dba': ''})
        self.assertIsNotNone(dd_result['domain'])
        self.assertIn('.', dd_result['domain'])

    @patch('osint.dns_intel._make_resolver')
    def test_all_layers_return_queried_flag(self, mock_dns_resolver):
        from osint.domain_discovery import discover_domain
        from osint.dns_intel import enrich_dns
        from osint.ct_logs import enrich_ct
        from osint.web_fingerprint import enrich_web
        import dns.resolver
        import requests as req

        with patch('osint.domain_discovery.probe_domain', return_value=False):
            dd = discover_domain({'name': 'Test', 'url': '', 'dba': ''})
        self.assertTrue(dd['queried'])

        mock_res = MagicMock()
        mock_res.resolve.side_effect = dns.resolver.NXDOMAIN
        mock_dns_resolver.return_value = mock_res
        dns_r = enrich_dns('test.com')
        self.assertTrue(dns_r['queried'])

        with patch('osint.ct_logs.requests.get', side_effect=req.exceptions.ConnectionError('mock')):
            ct_r = enrich_ct('test.com')
        self.assertTrue(ct_r['queried'])

        with patch('osint.web_fingerprint.requests.get', side_effect=req.exceptions.ConnectionError('mock')):
            web_r = enrich_web('test.com')
        self.assertTrue(web_r['queried'])

    @patch('osint.dns_intel._make_resolver')
    def test_all_layers_return_error_on_failure(self, mock_dns_resolver):
        from osint.dns_intel import enrich_dns
        from osint.ct_logs import enrich_ct
        from osint.web_fingerprint import enrich_web
        import dns.resolver
        import requests as req

        mock_res = MagicMock()
        mock_res.resolve.side_effect = dns.resolver.NXDOMAIN
        mock_dns_resolver.return_value = mock_res
        self.assertIsNotNone(enrich_dns('fail.com').get('error'))

        with patch('osint.ct_logs.requests.get', side_effect=req.exceptions.ConnectionError('fail')):
            self.assertIsNotNone(enrich_ct('fail.com').get('error'))

        with patch('osint.web_fingerprint.requests.get', side_effect=req.exceptions.ConnectionError('fail')):
            self.assertIsNotNone(enrich_web('fail.com').get('error'))

    @patch('osint.dns_intel._make_resolver')
    def test_osint_data_is_json_serializable(self, mock_dns_resolver):
        from osint.domain_discovery import discover_domain
        from osint.dns_intel import enrich_dns
        from osint.ct_logs import enrich_ct
        from osint.web_fingerprint import enrich_web
        import dns.resolver
        import requests as req

        with patch('osint.domain_discovery.probe_domain', return_value=True):
            dd = discover_domain({'name': 'Test', 'url': 'https://test.com', 'dba': ''})
        json.dumps(dd)

        mock_res = MagicMock()
        mock_res.resolve.side_effect = dns.resolver.NXDOMAIN
        mock_dns_resolver.return_value = mock_res
        dns_r = enrich_dns('test.com')
        json.dumps(dns_r)

        with patch('osint.ct_logs.requests.get', side_effect=req.exceptions.Timeout('mock')):
            ct_r = enrich_ct('test.com')
        json.dumps(ct_r)

        with patch('osint.web_fingerprint.requests.get', side_effect=req.exceptions.Timeout('mock')):
            web_r = enrich_web('test.com')
        json.dumps(web_r)


# ═══════════════════════════════════════════════════════════════
# REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════

class TestRegressions(unittest.TestCase):

    def test_domain_with_trailing_dot(self):
        from osint.domain_discovery import extract_domain_from_url
        result = extract_domain_from_url('https://example.com.')
        self.assertEqual(result, 'example.com')

    def test_unicode_company_name(self):
        from osint.domain_discovery import generate_domain_guesses
        guesses = generate_domain_guesses('Résumé Services LLC')
        self.assertIsInstance(guesses, list)

    def test_very_long_company_name(self):
        from osint.domain_discovery import generate_domain_guesses
        name = 'Very Long Company Name That Goes On And On And On LLC'
        guesses = generate_domain_guesses(name)
        self.assertIsInstance(guesses, list)
        for g in guesses:
            self.assertLess(len(g), 80)


def requests_ci_dict(d):
    """Helper: return a plain dict (tests don't need full CaseInsensitiveDict)."""
    return d


if __name__ == '__main__':
    unittest.main()
