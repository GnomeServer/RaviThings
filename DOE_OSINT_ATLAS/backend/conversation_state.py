"""Server-side conversation state for the OSINT Atlas command console.

Replaces the stateless 'frontend sends history every turn' pattern with a
session-keyed in-memory store. Provides rolling conversation summaries and
entity tracking on top of the per-session verbatim transcript.

Bounds:
- max_sessions: cap on total sessions (default 200, evict oldest when exceeded)
- ttl_seconds: idle timeout (default 3600, evict on get_or_create)

For a single-process Railway dyno this is fine. If we ever scale horizontally,
swap to redis or per-row sqlite.
"""
import json
import pathlib
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.history_budget import _est_tokens

if TYPE_CHECKING:
    from backend.glm_client import GLMClient


@dataclass
class ConversationState:
    session_id: str
    verbatim_turns: list[dict] = field(default_factory=list)
    rolling_summary: str = ""           # filled by Task 7
    entity_tracker: list[str] = field(default_factory=list)  # filled by Task 7
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    turn_count: int = 0


class ConversationStore:
    def __init__(self, max_sessions: int = 200, ttl_seconds: float = 3600.0):
        self._sessions: dict[str, ConversationState] = {}
        self._max = max_sessions
        self._ttl = ttl_seconds

    def evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, st in self._sessions.items()
            if now - st.last_used_at > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]

    def _evict_oldest_if_full(self) -> None:
        while len(self._sessions) >= self._max:
            oldest_sid = min(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].last_used_at,
            )
            del self._sessions[oldest_sid]

    def get_or_create(self, session_id: str) -> ConversationState:
        self.evict_expired()
        if session_id not in self._sessions:
            self._evict_oldest_if_full()
            self._sessions[session_id] = ConversationState(session_id=session_id)
        else:
            self._sessions[session_id].last_used_at = time.time()
        return self._sessions[session_id]

    def append_turn(self, session_id: str, role: str, content: str) -> None:
        state = self.get_or_create(session_id)
        state.verbatim_turns.append({"role": role, "content": content})
        state.turn_count += 1
        state.last_used_at = time.time()

    # ── Rolling summary + entity tracker (Task 7) ──────────────────────────
    async def maybe_summarize(
        self,
        session_id: str,
        llm: "GLMClient",
        target_tokens: int = 8000,
    ) -> bool:
        """If verbatim history exceeds target_tokens, regenerate the rolling
        summary and trim the oldest verbatim turns.

        Returns True if a summary was regenerated, False otherwise.
        """
        state = self.get_or_create(session_id)
        total = sum(_est_tokens(m) for m in state.verbatim_turns)
        if total <= target_tokens:
            return False
        if hasattr(llm, "is_available") and not llm.is_available():
            return False

        # Summarize the OLDEST 70% of turns; keep the newest 30% verbatim
        cutoff = max(1, int(len(state.verbatim_turns) * 0.7))
        to_summarize = state.verbatim_turns[:cutoff]
        to_keep = state.verbatim_turns[cutoff:]

        transcript = "\n".join(
            f"{m.get('role', '?').upper()}: {m.get('content', '')[:1000]}"
            for m in to_summarize
        )
        if state.rolling_summary:
            transcript = (
                f"PRIOR SUMMARY:\n{state.rolling_summary}\n\nNEW TURNS:\n{transcript}"
            )

        try:
            messages = [
                {"role": "system", "content": _SUMMARIZE_PROMPT},
                {"role": "user", "content": transcript},
            ]
            summary = await llm.chat(messages, max_tokens=300)
            state.rolling_summary = summary.strip()
            state.verbatim_turns = to_keep
            return True
        except Exception as e:
            print(f"[conversation_state] summary regeneration failed: {e}")
            return False

    def update_entities(
        self, session_id: str, role: str, content: str, names: list[str]
    ) -> None:
        """Find contractor names in `content` and push them onto the tracker.

        Preserves "most recent last" ordering and deduplicates — a re-mentioned
        name moves to the tail. Cap is 10 most recent.
        """
        state = self.get_or_create(session_id)
        found = _extract_entities(content, names)
        for name in found:
            if name in state.entity_tracker:
                state.entity_tracker.remove(name)
            state.entity_tracker.append(name)
        # Cap at 10 most recent
        state.entity_tracker = state.entity_tracker[-10:]


# ── Module-level helpers: contractor name extraction ─────────────────────

_CONTRACTOR_NAMES_CACHE: list[str] | None = None


def _load_contractor_names(json_path: pathlib.Path | str | None = None) -> list[str]:
    """Load contractor names from contractors.json (cached after first call).

    First call is slow (~50-100ms to parse 43MB JSON), subsequent calls return
    the module-level cache instantly. On any failure the cache is set to an
    empty list so we degrade gracefully.
    """
    global _CONTRACTOR_NAMES_CACHE
    if _CONTRACTOR_NAMES_CACHE is not None:
        return _CONTRACTOR_NAMES_CACHE
    if json_path is None:
        json_path = (
            pathlib.Path(__file__).parent.parent
            / "frontend"
            / "static"
            / "contractors.json"
        )
    try:
        with open(json_path) as f:
            data = json.load(f)
        names = [
            c.get("name", "")
            for c in data.get("contractors", [])
            if c.get("name")
        ]
        # Longest first so multi-word names win over first-word fallbacks
        _CONTRACTOR_NAMES_CACHE = sorted(set(names), key=len, reverse=True)
        return _CONTRACTOR_NAMES_CACHE
    except Exception:
        _CONTRACTOR_NAMES_CACHE = []
        return _CONTRACTOR_NAMES_CACHE


def _extract_entities(text: str, names: list[str]) -> list[str]:
    """Find contractor names mentioned in `text`. Case-insensitive substring match.

    Uses substring not full token match because contractors are often referenced
    by a partial name (e.g. 'Honeywell' for 'HONEYWELL FEDERAL MFG & TECH').
    Matches either the full name OR the first word (if len > 4).
    """
    text_lower = text.lower()
    # Longest first so multi-word names win when both match
    sorted_names = sorted(names, key=len, reverse=True)
    found: list[str] = []
    for name in sorted_names:
        if not name:
            continue
        if name.lower() in text_lower:
            if name not in found:
                found.append(name)
            continue
        parts = name.split()
        first_word = parts[0] if parts else ""
        if len(first_word) > 4 and first_word.lower() in text_lower:
            if name not in found:
                found.append(name)
    return found


_SUMMARIZE_PROMPT = """\
You are summarizing a chat conversation between a user and an OSINT analyst about \
DOE contractors. Distill the conversation into a 150-word "PRIOR DISCUSSION SUMMARY" \
that captures: which contractors were discussed, what specific topics or angles the \
user cared about, and any decisions or conclusions reached. Be specific — name \
contractors by name, mention concrete topics. Do NOT add commentary, do NOT speculate \
about unmentioned details, do NOT exceed 150 words.\
"""
