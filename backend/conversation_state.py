"""Server-side conversation state for the OSINT Atlas command console.

Replaces the stateless 'frontend sends history every turn' pattern with a
session-keyed in-memory store. Foundation for rolling summaries (Task 7) and
entity tracking (Task 7).

Bounds:
- max_sessions: cap on total sessions (default 200, evict oldest when exceeded)
- ttl_seconds: idle timeout (default 3600, evict on get_or_create)

For a single-process Railway dyno this is fine. If we ever scale horizontally,
swap to redis or per-row sqlite.
"""
import time
from dataclasses import dataclass, field


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
