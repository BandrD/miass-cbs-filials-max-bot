from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DialogState(str, Enum):
    IDLE = "idle"
    FAQ = "faq"
    BRANCHES = "branches"
    WAIT_FEEDBACK = "wait_feedback"
    WAIT_BOOK = "wait_book"
    FREE_CHAT = "free_chat"


@dataclass
class UserSession:
    state: DialogState = DialogState.IDLE
    extra: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._data: dict[int, UserSession] = {}

    def get(self, chat_id: int) -> UserSession:
        if chat_id not in self._data:
            self._data[chat_id] = UserSession()
        return self._data[chat_id]

    def set_state(self, chat_id: int, state: DialogState) -> UserSession:
        session = self.get(chat_id)
        session.state = state
        return session

    def reset(self, chat_id: int) -> None:
        self._data[chat_id] = UserSession()
