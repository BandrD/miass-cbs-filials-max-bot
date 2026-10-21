from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Storage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.feedback_dir = root / "feedback"
        for p in (self.root, self.feedback_dir):
            p.mkdir(parents=True, exist_ok=True)
        self.db_path = root / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    note TEXT
                )
                """
            )
            conn.commit()

    def save_feedback(self, chat_id: int, text: str) -> Path:
        ts = datetime.now(timezone.utc)
        payload = {"chat_id": chat_id, "created_at": ts.isoformat(), "text": text}
        path = self.feedback_dir / f"{chat_id}_{ts.strftime('%Y%m%dT%H%M%S%f')}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO feedback (chat_id, created_at, text) VALUES (?, ?, ?)",
                (chat_id, ts.isoformat(), text),
            )
            conn.commit()
        return path

    def log_token_usage(
        self,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        note: str = "",
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO token_usage (created_at, prompt_tokens, completion_tokens, total_tokens, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    note,
                ),
            )
            conn.commit()
        logger.info("token_usage total=%s note=%s", total_tokens, note)
