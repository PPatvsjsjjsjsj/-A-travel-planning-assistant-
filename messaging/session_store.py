from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock

from models.trip import TripPlan, TripRequest


@dataclass
class Conversation:
    session_id: str
    messages: list[dict] = field(default_factory=list)
    trip_request: TripRequest | None = None
    plan: TripPlan | None = None
    skills_used: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.messages = self.messages[-30:]
        self.updated_at = datetime.now(timezone.utc).isoformat()


class SessionStore:
    def __init__(self):
        self._sessions: dict[str, Conversation] = {}
        self._lock = RLock()

    def get_or_create(self, session_id: str) -> Conversation:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Conversation(session_id=session_id)
            return self._sessions[session_id]

    def get(self, session_id: str) -> Conversation | None:
        with self._lock:
            return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None
