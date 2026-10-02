"""
Tests for backend/jev.py using fake client (no live HTTP).

Covers required cases:
- score maps top (2) to 10, bottom (0) to 0
- judge failure -> judged False, score None
- research parent noul=0.4 sets review, keeps parent
- kill-chain ip_unsupported on non-allowlist IP
- severity disagreement sets jev_risk_disagreement, does not change risk_level
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.jev import (
    score_contracts,
    verify_research,
    verify_kill_chain,
)


class FakeScoreAnswer:
    def __init__(self, score):
        self.score = score


class FakeNoulAnswer:
    def __init__(self, noul):
        self.noul = noul


class FakeResponse:
    def __init__(self, scores=None, nouls=None):
        self.scores = scores or {}
        self.nouls = nouls or {}


class FakeClient:
    """Fake TypeSafe client for tests. Returns pre-set response or raises."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.closed = False

    async def system_one(self, state=None, questions=None):
        if self.error:
            raise self.error
        return self.response

    async def aclose(self):
        self.closed = True


def test_score_top_to_10_bottom_to_0():
    """Top criterion (2) maps to 10, bottom (0) to 0."""
    async def run():
        # batch with two rows
        batch = [
            {"key": "K1", "description": "exact match work", "recipient": "R", "obligation": 1, "fiscal_year": 2024},
            {"key": "K2", "description": "unrelated", "recipient": "R", "obligation": 1, "fiscal_year": 2024},
        ]
        # simulate scores: first gets 2.0 (top), second 0.0
        fake_resp = FakeResponse(scores={
            "0": FakeScoreAnswer(2.0),
            "1": FakeScoreAnswer(0.0),
        })
        client = FakeClient(response=fake_resp)
        results = await score_contracts("find the exact obligation", batch, client=client)
        assert len(results) == 2
        assert results[0]["score"] == 10.0
        assert results[0]["judged"] is True
        assert results[1]["score"] == 0.0
        assert results[1]["judged"] is True
        # preserve fields
        assert results[0]["key"] == "K1"
        assert results[0]["recipient"] == "R"
    asyncio.run(run())


def test_judge_failure_yields_unjudged():
    """When judge returns None (e.g. exception), every row has judged=False, score=None."""
    async def run():
        batch = [
            {"key": "K1", "description": "foo", "recipient": "R", "obligation": 1, "fiscal_year": 2024},
        ]
        client = FakeClient(error=RuntimeError("boom"))
        results = await score_contracts("q", batch, client=client)
        assert len(results) == 1
        assert results[0]["score"] is None
        assert results[0]["judged"] is False
        assert results[0]["reason"] == "unjudged"
    asyncio.run(run())


def test_research_parent_noul_0_4_sets_review_keeps_parent():
    """noul=0.4 <0.65 sets review=True, does not clear parent_company."""
    async def run():
        result = {
            "parent_company": "Acme Corp",
            "current_domain": None,
        }
        search_context = "some snippet mentioning parent"
        fake_resp = FakeResponse(nouls={
            "parent_supported": FakeNoulAnswer(0.4),
        })
        client = FakeClient(response=fake_resp)
        out = await verify_research(result, search_context, client=client)
        assert out["parent_company"] == "Acme Corp"  # kept
        assert out["jev"]["parent_supported"] == 0.4
        assert out["jev"]["review"] is True
    asyncio.run(run())


def test_kill_chain_ip_unsupported_flags():
    """Step with IP 203.0.113.5 not in allowlist sets ip_unsupported and jev_ip_flag."""
    async def run():
        chain = {
            "risk_level": "high",
            "steps": [
                {"step": 1, "description": "Connect to 203.0.113.5", "evidence": "", "impact": ""},
            ],
        }
        intel = {
            "onprem_ips": ["198.51.100.10"],
            "all_services": [],
            "hosting_context": [],
        }
        # even if judge fails, IP check runs
        client = FakeClient(error=RuntimeError("no jev"))
        out = await verify_kill_chain(chain, intel, client=client)
        assert out["steps"][0]["ip_unsupported"] is True
        assert out["jev_ip_flag"] is True
        assert out["jev"] == {"unavailable": True}
    asyncio.run(run())


def test_severity_disagreement_sets_flag_no_change_risk():
    """Disagreement sets jev_risk_disagreement, jev_risk_level, leaves original risk_level."""
    async def run():
        chain = {
            "risk_level": "high",
            "steps": [],
        }
        intel = {
            "services_count": 5,
            "vulns_count": 2,
            "onprem_count": 1,
            "ssl_issues_count": 0,
            "all_vulns": ["CVE-123"],
        }
        # jev returns score that maps to "low" (nearest to 0)
        fake_resp = FakeResponse(scores={"severity": FakeScoreAnswer(0.1)})
        client = FakeClient(response=fake_resp)
        out = await verify_kill_chain(chain, intel, client=client)
        assert out["risk_level"] == "high"  # unchanged
        assert out["jev_risk_disagreement"] is True
        assert out["jev_risk_level"] == "low"
        assert out["jev"]["level"] == "low"
    asyncio.run(run())


if __name__ == "__main__":
    # simple runner for manual
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            print(f"running {name}")
            fn()
    print("all done")