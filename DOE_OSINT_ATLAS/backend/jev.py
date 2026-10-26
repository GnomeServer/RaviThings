"""Server-side Jev judge for contract scoring and post-generation checks.

Never print, log, or attach API key values to exceptions.
"""
from __future__ import annotations

import json
import os
import re

from typesafe_sdk import AsyncTypeSafeClient, Noul, Score

_ENDPOINT_ROOT = "https://api.typesafe.ai"
_MODEL = "jev-latest"
_CONFIG_RELATIVE = os.path.join("Library", "Application Support", "OSINT Atlas", "config.json")

CONTRACT_CRITERIA = [
    "Unrelated to the question",
    "Same topic, different work",
    "This obligation is the work the question asks about",
]
RISK_CRITERIA = ["low", "medium", "high", "critical"]
_REVIEW_BELOW = 0.65
_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_STEP_TEXT_FIELDS = ("description", "evidence", "impact")


def _trim_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        text = text[1:-1].strip()
    return text


def _nonempty(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = _trim_quotes(value)
    return text or None


def resolve_jev_key() -> str | None:
    """Resolve a Jev key without logging it.

    Order: non-empty ``JEV_API_KEY``, then ``jev_api_key`` in the Atlas
    config JSON (``HOME`` is honored), then ``JEV_API_KEY`` in a ``.env``
    found by walking parents of this file.
    """
    try:
        env_key = _nonempty(os.environ["JEV_API_KEY"])
    except KeyError:
        env_key = None
    if env_key:
        return env_key

    config_key = _key_from_atlas_config()
    if config_key:
        return config_key
    return _key_from_dotenv()


def _key_from_atlas_config() -> str | None:
    home = os.environ.get("HOME") or os.path.expanduser("~")
    path = os.path.join(home, _CONFIG_RELATIVE)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return _nonempty(data.get("jev_api_key"))


def _key_from_dotenv() -> str | None:
    directory = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_path = os.path.join(directory, ".env")
        if os.path.isfile(env_path):
            key = _read_env_key(env_path)
            if key:
                return key
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent


def _read_env_key(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except (OSError, UnicodeError):
        return None
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("export "):
            text = text[len("export "):].strip()
        if "=" not in text:
            continue
        name, value = text.split("=", 1)
        if name.strip() != "JEV_API_KEY":
            continue
        return _nonempty(value)
    return None


def live_allowed() -> bool:
    """Block live Jev calls from the existing test suite unless opted in."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return os.environ.get("JEV_LIVE") == "1"
    return True


async def judge(state, questions, *, client=None):
    """Return the SDK response, or None when the call cannot be made.

    A caller-owned client is used as-is and is not closed. A client created
    here is closed. Missing key, disallowed live calls, and any exception
    return None. Exception text is not re-raised, because it may contain a key.
    """
    created = None
    if client is None:
        if not live_allowed():
            return None
        api_key = resolve_jev_key()
        if not api_key:
            return None
        try:
            created = AsyncTypeSafeClient(
                api_key=api_key,
                model=_MODEL,
                base_url=_ENDPOINT_ROOT,
            )
        except Exception:
            return None
        client = created
    try:
        return await client.system_one(state=state, questions=questions)
    except Exception:
        return None
    finally:
        if created is not None and hasattr(created, "aclose"):
            try:
                await created.aclose()
            except Exception:
                pass


def _unjudged(row: dict) -> dict:
    return {**row, "score": None, "judged": False, "reason": "unjudged"}


async def score_contracts(query: str, batch: list[dict], *, client=None) -> list[dict]:
    """Score each contract with its own Jev Score question.

    Maps the 0..2 rubric position onto 0..10. A failed judge leaves every
    row unjudged with ``score: None`` — never 0.
    """
    if not batch:
        return []

    contracts = []
    questions = {}
    for index, row in enumerate(batch):
        description = row.get("description") or ""
        if not isinstance(description, str):
            description = str(description)
        contracts.append({
            "id": row.get("key"),
            "description": description[:500],
        })
        questions[str(index)] = Score(
            instructions=(
                f"The question is whether contracts[{index}].description "
                "is the work asked in query."
            ),
            criteria=list(CONTRACT_CRITERIA),
        )

    try:
        response = await judge(
            {"query": query, "contracts": contracts},
            questions,
            client=client,
        )
    except Exception:
        response = None
    if response is None:
        return [_unjudged(row) for row in batch]

    scored = []
    for index, row in enumerate(batch):
        try:
            value = response.scores[str(index)].score
            mapped = round(float(value) / 2 * 10, 1)
        except Exception:
            scored.append(_unjudged(row))
            continue
        scored.append({**row, "score": mapped, "judged": True, "reason": ""})
    return scored


def _present_text(value) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


async def verify_research(result: dict, search_context: str, *, client=None) -> dict:
    """Add ``result['jev']`` from snippet nouls. Does not clear fields."""
    if not isinstance(result, dict):
        return result

    questions = {}
    state = {"snippets": search_context}
    parent = _present_text(result.get("parent_company"))
    domain = _present_text(result.get("current_domain"))
    if parent:
        state["parent_company"] = parent
        questions["parent_supported"] = Noul(
            instructions=(
                "Do the snippets state that `parent_company` is the parent or acquirer?"
            )
        )
    if domain:
        state["current_domain"] = domain
        questions["domain_supported"] = Noul(
            instructions=(
                "Do the snippets identify `current_domain` as an official domain?"
            )
        )
    if not questions:
        result["jev"] = {}
        return result

    try:
        response = await judge(state, questions, client=client)
    except Exception:
        response = None
    if response is None:
        result["jev"] = {"unavailable": True}
        return result

    jev = {}
    review = False
    try:
        if "parent_supported" in questions:
            noul = float(response.nouls["parent_supported"].noul)
            jev["parent_supported"] = noul
            if noul < _REVIEW_BELOW:
                review = True
        if "domain_supported" in questions:
            noul = float(response.nouls["domain_supported"].noul)
            jev["domain_supported"] = noul
            if noul < _REVIEW_BELOW:
                review = True
    except Exception:
        result["jev"] = {"unavailable": True}
        return result
    if review:
        jev["review"] = True
    result["jev"] = jev
    return result


def _allowlist_ips(intel: dict) -> set[str]:
    if not isinstance(intel, dict):
        return set()
    found: set[str] = set()

    onprem = intel.get("onprem_ips") or []
    if isinstance(onprem, str):
        onprem = [onprem]
    if isinstance(onprem, (list, tuple)):
        for item in onprem:
            text = str(item) if item is not None else ""
            found.update(_IPV4.findall(text))

    services = intel.get("all_services") or []
    if isinstance(services, list):
        for service in services:
            if not isinstance(service, dict):
                continue
            ip = service.get("ip")
            if isinstance(ip, str) and ip.strip():
                found.add(ip.strip())
                found.update(_IPV4.findall(ip))

    hosting = intel.get("hosting_context") or []
    if isinstance(hosting, str):
        hosting = [hosting]
    if isinstance(hosting, (list, tuple)):
        for entry in hosting:
            found.update(_IPV4.findall(str(entry)))
    return found


def _apply_ip_flags(chain: dict, allow: set[str]) -> None:
    steps = chain.get("steps") or []
    if not isinstance(steps, list):
        return
    flagged = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        text = " ".join(str(step.get(field) or "") for field in _STEP_TEXT_FIELDS)
        unsupported = [ip for ip in _IPV4.findall(text) if ip not in allow]
        if unsupported:
            step["ip_unsupported"] = True
            flagged = True
    if flagged:
        chain["jev_ip_flag"] = True


def _compact_intel(intel: dict) -> dict:
    """Counts and CVE ids only. No narrative rewrite."""
    if not isinstance(intel, dict):
        intel = {}
    cves = intel.get("all_vulns") or []
    if isinstance(cves, str):
        cve_ids = [cves] if cves else []
    else:
        cve_ids = [item for item in cves if isinstance(item, str) and item]
    return {
        "services_count": intel.get("services_count", 0),
        "vulns_count": intel.get("vulns_count", 0),
        "onprem_count": intel.get("onprem_count", 0),
        "ssl_issues_count": intel.get("ssl_issues_count", 0),
        "cve_ids": cve_ids,
    }


def _nearest_level(score: float) -> str:
    index = min(range(len(RISK_CRITERIA)), key=lambda i: (abs(float(score) - i), i))
    return RISK_CRITERIA[index]


async def verify_kill_chain(chain: dict, intel: dict, *, client=None) -> dict:
    """Flag unsupported IPs, then compare a Jev severity score to risk_level.

    Does not overwrite ``risk_level`` or rewrite steps. A failed judge still
    keeps the deterministic IP flag and sets ``jev`` unavailable.
    """
    if not isinstance(chain, dict):
        return chain

    _apply_ip_flags(chain, _allowlist_ips(intel if isinstance(intel, dict) else {}))
    questions = {
        "severity": Score(
            instructions=(
                "Rate the exposure severity using only the counts and CVE ids."
            ),
            criteria=list(RISK_CRITERIA),
        )
    }
    try:
        response = await judge(_compact_intel(intel), questions, client=client)
    except Exception:
        response = None
    if response is None:
        chain["jev"] = {"unavailable": True}
        return chain

    try:
        score = response.scores["severity"].score
        judged_level = _nearest_level(score)
    except Exception:
        chain["jev"] = {"unavailable": True}
        return chain

    chain["jev"] = {"severity": score, "level": judged_level}
    current = str(chain.get("risk_level") or "").strip().lower()
    if current != judged_level:
        chain["jev_risk_disagreement"] = True
        chain["jev_risk_level"] = judged_level
    return chain
