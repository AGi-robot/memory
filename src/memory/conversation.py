"""SQLite-backed conversation history for Grace's short-term context."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4


class GraceMemory:
    """Persist recent user and assistant turns in a local SQLite database."""

    def __init__(self, database_path: str, max_turns: int = 8) -> None:
        self.database_path = Path(database_path).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_turns = max(1, max_turns)
        self.conversation_id = "default"
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.database_path, timeout=10)
        try:
            db.execute("PRAGMA foreign_keys = ON")
            with db:
                yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS conversations ("
                "id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS conversation_turns ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "conversation_id TEXT NOT NULL REFERENCES conversations(id), "
                "exchange_id TEXT NOT NULL, "
                "role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), "
                "content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS conversation_turns_order "
                "ON conversation_turns (conversation_id, id DESC)"
            )
            db.execute(
                "INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)",
                (self.conversation_id, "Grace chat"),
            )

    def recent(self, conversation_id: str | None = None) -> list[dict[str, str]]:
        active_conversation = conversation_id or self.conversation_id
        with self._connect() as db:
            rows = db.execute(
                "SELECT role, content FROM conversation_turns "
                "WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (active_conversation, self.max_turns * 2),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def add_exchange(
        self,
        user_text: str,
        assistant_text: str,
        conversation_id: str | None = None,
    ) -> None:
        active_conversation = conversation_id or self.conversation_id
        exchange_id = str(uuid4())
        title = (
            "Grace chat"
            if active_conversation == self.conversation_id
            else f"Conversation {active_conversation}"
        )
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO conversations (id, title) VALUES (?, ?)",
                (active_conversation, title),
            )
            db.executemany(
                "INSERT INTO conversation_turns "
                "(conversation_id, exchange_id, role, content) VALUES (?, ?, ?, ?)",
                [
                    (active_conversation, exchange_id, "user", user_text),
                    (active_conversation, exchange_id, "assistant", assistant_text),
                ],
            )
