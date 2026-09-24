"""
Test suite for AI-powered contractor research layer.

Tests extract_research_json, build_research_prompt, research_contractor,
needs_ai_research, and apply_domain_cascade.

Run: python -m pytest tests/test_ai_research.py -v
"""

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════
# EXTRACT_RESEARCH_JSON TESTS
# ═══════════════════════════════════════════════════════════════

class TestExtractResearchJson(unittest.TestCase):

    def test_clean_json(self):
        """Parse clean JSON output from LLM."""
        from osint.ai_research import extract_research_json
        raw = '{"company_status": "active", "current_domain": "example.com"}'
        result = extract_research_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_status'], 'active')
        self.assertEqual(result['current_domain'], 'example.com')

    def test_with_think_tags(self):
        """Strip <think>...</think> tags before parsing JSON."""
        from osint.ai_research import extract_research_json
        raw = (
            '<think>Let me analyze this contractor...</think>\n'
            '{"company_status": "acquired", "parent_company": "Jacobs Engineering"}'
        )
        result = extract_research_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_status'], 'acquired')
        self.assertEqual(result['parent_company'], 'Jacobs Engineering')

    def test_markdown_fence(self):
        """Extract JSON from markdown code fences."""
        from osint.ai_research import extract_research_json
        raw = (
            'Here is the analysis:\n'
            '```json\n'
            '{"company_status": "merged", "current_domain": "merged-co.com"}\n'
            '```\n'
            'Hope that helps!'
        )
        result = extract_research_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_status'], 'merged')

    def test_malformed_json(self):
        """Return None for completely malformed output."""
        from osint.ai_research import extract_research_json
        raw = 'This is not JSON at all, just rambling text with no braces.'
        result = extract_research_json(raw)
        self.assertIsNone(result)

    def test_json_surrounded_by_text(self):
        """Extract JSON object embedded within surrounding text."""
        from osint.ai_research import extract_research_json
        raw = (
            'Based on my research, here are the findings:\n\n'
            '{"company_status": "dissolved", "brief": "Company ceased operations in 2020"}\n\n'
            'Let me know if you need more details.'
        )
        result = extract_research_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_status'], 'dissolved')
        self.assertEqual(result['brief'], 'Company ceased operations in 2020')

    def test_json_with_braces_in_string_values(self):
        """JSON with curly braces inside string values should parse correctly."""
        from osint.ai_research import extract_research_json
        raw = '{"company_status": "acquired", "brief": "The company {formerly OSI} was acquired by Emerson."}'
        result = extract_research_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_status'], 'acquired')
        self.assertIn('{formerly OSI}', result['brief'])


# ═══════════════════════════════════════════════════════════════
# BUILD_RESEARCH_PROMPT TESTS
# ═══════════════════════════════════════════════════════════════

class TestBuildResearchPrompt(unittest.TestCase):

    def _sample_contractor(self, **overrides):
        base = {
            'name': 'Acme Energy Solutions LLC',
            'dba': 'Acme Energy',
            'city': 'Houston',
            'state': 'Texas',
            'category': 'Engineering & Technical Services',
            'contract_ids': ['DE-AC02-21CH001', 'DE-AC02-22CH002'],
            'obligation': 5_000_000.0,
            'naics': 'Engineering Services',
            'role': 'prime',
        }
        base.update(overrides)
        return base

    def test_basic_prompt(self):
        """Prompt contains system and user messages with contractor name."""
        from osint.ai_research import build_research_prompt
        contractor = self._sample_contractor()
        messages = build_research_prompt(contractor, "Search context here")
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['role'], 'system')
        self.assertEqual(messages[1]['role'], 'user')
        # Contractor name should appear in user message
        self.assertIn('Acme Energy Solutions LLC', messages[1]['content'])

    def test_includes_existing_domain(self):
        """When contractor has an existing domain, it appears in the prompt."""
        from osint.ai_research import build_research_prompt
        contractor = self._sample_contractor()
        contractor['osint'] = {
            'domain_discovery': {
                'domain': 'acme-energy.com',
                'source': 'dns_probe',
                'confidence': 35,
            }
        }
        messages = build_research_prompt(contractor, "Search context")
        user_content = messages[1]['content']
        self.assertIn('acme-energy.com', user_content)
        self.assertIn('dns_probe', user_content)

    def test_requests_json_output(self):
        """System prompt instructs the LLM to output JSON with required fields."""
        from osint.ai_research import build_research_prompt
        contractor = self._sample_contractor()
        messages = build_research_prompt(contractor, "Search context")
        system_content = messages[0]['content']
        # Must mention JSON output format
        self.assertIn('JSON', system_content)
        # Must mention key fields
        for field in ['company_status', 'current_domain', 'domain_confidence',
                      'parent_company', 'brief', 'sources']:
            self.assertIn(field, system_content)


# ═══════════════════════════════════════════════════════════════
# RESEARCH_CONTRACTOR TESTS
# ═══════════════════════════════════════════════════════════════

class TestResearchContractor(unittest.TestCase):

    def _sample_contractor(self):
        return {
            'name': 'Westinghouse Electric Company',
            'dba': '',
            'city': 'Cranberry Township',
            'state': 'Pennsylvania',
            'category': 'Nuclear Energy',
            'contract_ids': ['DE-AC05-00OR22725'],
            'obligation': 12_000_000.0,
            'naics': 'Nuclear Electric Power Generation',
            'role': 'prime',
        }

    def _make_search_results(self, results_per_query=2):
        """Create mock Brave search results."""
        return [
            {'title': f'Result {i}', 'url': f'https://example{i}.com/page', 'description': f'Description {i}'}
            for i in range(results_per_query)
        ]

    def _llm_json_response(self, **overrides):
        """Build a valid LLM JSON response."""
        base = {
            'company_status': 'active',
            'company_status_detail': 'Operating as subsidiary of Brookfield Business Partners',
            'current_domain': 'westinghousenuclear.com',
            'domain_confidence': 85,
            'parent_company': 'Brookfield Business Partners',
            'acquisition_year': 2018,
            'brief': 'Westinghouse Electric Company is a nuclear technology company.',
            'sources': [
                {'title': 'Westinghouse Nuclear', 'url': 'https://westinghousenuclear.com'}
            ],
        }
        base.update(overrides)
        return json.dumps(base)

    @patch('osint.ai_research.probe_domain', return_value=True)
    def test_successful_research(self, mock_probe):
        """Full pipeline: search -> LLM -> extract -> validate."""
        llm = MagicMock()
        llm.is_available.return_value = True
        llm.chat = AsyncMock(return_value=self._llm_json_response())

        brave = MagicMock()
        brave.is_available.return_value = True
        brave.search = AsyncMock(return_value=self._make_search_results())

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            return await research_contractor(contractor, llm, brave)

        result = asyncio.run(run())

        self.assertTrue(result['queried'])
        self.assertEqual(result['company_status'], 'active')
        self.assertEqual(result['current_domain'], 'westinghousenuclear.com')
        self.assertTrue(result['domain_validated'])
        self.assertEqual(result['parent_company'], 'Brookfield Business Partners')
        self.assertEqual(result['acquisition_year'], 2018)
        self.assertIsNone(result['error'])
        self.assertGreater(result['search_queries_used'], 0)
        self.assertGreater(result['raw_search_results'], 0)

    @patch('osint.ai_research.probe_domain', return_value=False)
    def test_domain_validation_failure(self, mock_probe):
        """Domain from LLM doesn't resolve -> domain_validated=False."""
        llm = MagicMock()
        llm.is_available.return_value = True
        llm.chat = AsyncMock(return_value=self._llm_json_response())

        brave = MagicMock()
        brave.is_available.return_value = True
        brave.search = AsyncMock(return_value=self._make_search_results())

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            return await research_contractor(contractor, llm, brave)

        result = asyncio.run(run())

        self.assertTrue(result['queried'])
        self.assertFalse(result['domain_validated'])
        # Domain should still be present but flagged as unvalidated
        self.assertEqual(result['current_domain'], 'westinghousenuclear.com')

    def test_llm_unavailable(self):
        """When the LLM is unavailable, return error result."""
        llm = MagicMock()
        llm.is_available.return_value = False

        brave = MagicMock()
        brave.is_available.return_value = True
        brave.search = AsyncMock(return_value=self._make_search_results())

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            return await research_contractor(contractor, llm, brave)

        result = asyncio.run(run())

        self.assertTrue(result['queried'])
        self.assertIn('llm', result['error'].lower())

    @patch('osint.ai_research.probe_domain', return_value=True)
    def test_brave_unavailable_still_synthesizes(self, mock_probe):
        """When Brave is unavailable, LLM still runs with contractor record only."""
        llm = MagicMock()
        llm.is_available.return_value = True
        llm.chat = AsyncMock(return_value=self._llm_json_response(
            domain_confidence=30,
            brief='Based on contractor record only.',
        ))

        brave = MagicMock()
        brave.is_available.return_value = False

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            return await research_contractor(contractor, llm, brave)

        result = asyncio.run(run())

        self.assertTrue(result['queried'])
        self.assertIsNone(result['error'])
        self.assertEqual(result['search_queries_used'], 0)
        # LLM should still have been called
        llm.chat.assert_called_once()

    @patch('osint.ai_research.probe_domain', return_value=True)
    def test_malformed_llm_json(self, mock_probe):
        """When LLM returns unparseable output, error is set but result still returned."""
        llm = MagicMock()
        llm.is_available.return_value = True
        llm.chat = AsyncMock(return_value="I can't find any information about this company.")

        brave = MagicMock()
        brave.is_available.return_value = True
        brave.search = AsyncMock(return_value=self._make_search_results())

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            return await research_contractor(contractor, llm, brave)

        result = asyncio.run(run())

        self.assertTrue(result['queried'])
        self.assertIsNotNone(result['error'])
        self.assertIn('parse', result['error'].lower())

    def test_search_queries_include_acquisition(self):
        """Brave search queries should include name+acquisition/merger query."""
        llm = MagicMock()
        llm.is_available.return_value = True
        llm.chat = AsyncMock(return_value=self._llm_json_response())

        brave = MagicMock()
        brave.is_available.return_value = True
        brave.search = AsyncMock(return_value=self._make_search_results())

        contractor = self._sample_contractor()

        async def run():
            from osint.ai_research import research_contractor
            with patch('osint.ai_research.probe_domain', return_value=True):
                return await research_contractor(contractor, llm, brave)

        asyncio.run(run())

        # Check that at least one search query mentions acquisition or merger
        all_queries = [call.args[0] for call in brave.search.call_args_list]
        has_acquisition_query = any(
            'acqui' in q.lower() or 'merger' in q.lower() or 'merge' in q.lower()
            for q in all_queries
        )
        self.assertTrue(has_acquisition_query,
                        f"No acquisition/merger query found in: {all_queries}")


# ═══════════════════════════════════════════════════════════════
# NEEDS_AI_RESEARCH TESTS
# ═══════════════════════════════════════════════════════════════

class TestNeedsAiResearch(unittest.TestCase):

    def test_skip_brave_search_domain(self):
        """Contractor with brave_search domain at good confidence should be skipped."""
        from osint.ai_research import needs_ai_research
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': 'example.com',
                    'source': 'brave_search',
                    'confidence': 80,
                    'queried': True,
                },
                'ai_research': {'queried': True},
            }
        }
        self.assertFalse(needs_ai_research(contractor))

    def test_include_dns_probe(self):
        """Contractor with dns_probe source should be flagged for research."""
        from osint.ai_research import needs_ai_research
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': 'example.com',
                    'source': 'dns_probe',
                    'confidence': 40,
                    'queried': True,
                },
            }
        }
        self.assertTrue(needs_ai_research(contractor))

    def test_include_no_domain(self):
        """Contractor with no domain should be flagged for research."""
        from osint.ai_research import needs_ai_research
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': None,
                    'source': None,
                    'queried': True,
                },
            }
        }
        self.assertTrue(needs_ai_research(contractor))

    def test_include_low_confidence(self):
        """Contractor with low confidence (<50%) should be flagged for research."""
        from osint.ai_research import needs_ai_research
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': 'maybe-example.com',
                    'source': 'brave_search',
                    'confidence': 35,
                    'queried': True,
                },
            }
        }
        self.assertTrue(needs_ai_research(contractor))

    def test_skip_already_researched(self):
        """Contractor already researched via AI should be skipped."""
        from osint.ai_research import needs_ai_research
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': None,
                    'source': None,
                    'queried': True,
                },
                'ai_research': {
                    'queried': True,
                    'company_status': 'dissolved',
                },
            }
        }
        self.assertFalse(needs_ai_research(contractor))


# ═══════════════════════════════════════════════════════════════
# APPLY_DOMAIN_CASCADE TESTS
# ═══════════════════════════════════════════════════════════════

class TestApplyDomainCascade(unittest.TestCase):

    def test_cascade_on_upgrade(self):
        """When domain changes, downstream layers should be invalidated."""
        from osint.ai_research import apply_domain_cascade
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': 'old-domain.com',
                    'source': 'dns_probe',
                    'confidence': 30,
                    'queried': True,
                },
                'domain_verify': {
                    'queried': True,
                    'verified': True,
                },
                'dns': {
                    'queried': True,
                    'records': {'A': ['1.2.3.4']},
                },
                'ct': {
                    'queried': True,
                    'certs': [],
                },
                'web': {
                    'queried': True,
                    'technologies': [],
                },
            }
        }

        changed = apply_domain_cascade(contractor, 'new-domain.com', 'ai_research')

        self.assertTrue(changed)
        # domain_discovery should be updated
        self.assertEqual(contractor['osint']['domain_discovery']['domain'], 'new-domain.com')
        self.assertEqual(contractor['osint']['domain_discovery']['source'], 'ai_research')
        # Downstream layers should be invalidated
        self.assertFalse(contractor['osint']['domain_verify']['queried'])
        self.assertFalse(contractor['osint']['dns']['queried'])
        self.assertFalse(contractor['osint']['ct']['queried'])
        self.assertFalse(contractor['osint']['web']['queried'])

    def test_no_cascade_when_unchanged(self):
        """When domain is the same, no cascade should happen."""
        from osint.ai_research import apply_domain_cascade
        contractor = {
            'osint': {
                'domain_discovery': {
                    'domain': 'same-domain.com',
                    'source': 'brave_search',
                    'confidence': 80,
                    'queried': True,
                },
                'domain_verify': {
                    'queried': True,
                    'verified': True,
                },
                'dns': {
                    'queried': True,
                    'records': {'A': ['1.2.3.4']},
                },
            }
        }

        changed = apply_domain_cascade(contractor, 'same-domain.com', 'ai_research')

        self.assertFalse(changed)
        # Downstream layers should NOT be invalidated
        self.assertTrue(contractor['osint']['domain_verify']['queried'])
        self.assertTrue(contractor['osint']['dns']['queried'])


if __name__ == '__main__':
    unittest.main()
