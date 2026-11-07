"""PostgreSQL-backed chat history prepared for later semantic indexing."""
from __future__ import annotations

from uuid import UUID, uuid4

import psycopg


class GraceMemory:
    """Keep canonical chat records with stable IDs and conversation boundaries."""

    def __init__(self, database_url: str, max_turns: int = 8) -> None:
        if not database_url:
            raise ValueError("Set AIVA_DATABASE_URL to Grace's PostgreSQL database")
        self.database_url = database_url
        self.max_turns = max(1, max_turns)
        self._initialize()
        self.conversation_id = self._get_default_conversation_id()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("CREATE SCHEMA IF NOT EXISTS grace")
            db.execute(
                "CREATE TABLE IF NOT EXISTS grace.conversations ("
                "id UUID PRIMARY KEY DEFAULT gen_random_uuid(), "
                "title TEXT, is_default BOOLEAN NOT NULL DEFAULT FALSE, "
                "metadata JSONB NOT NULL DEFAULT '{}'::jsonb, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            db.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS conversations_one_default "
                "ON grace.conversations (is_default) WHERE is_default"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS grace.conversation_turns ("
                "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
                "role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), "
                "content TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            # Additive migration: old rows are retained and attached to the default
            # conversation, while new rows carry IDs and metadata for future indexing.
            db.execute(
                "ALTER TABLE grace.conversation_turns "
                "ADD COLUMN IF NOT EXISTS conversation_id UUID "
                "REFERENCES grace.conversations(id)"
            )
            db.execute(
                "ALTER TABLE grace.conversation_turns "
                "ADD COLUMN IF NOT EXISTS exchange_id UUID"
            )
            db.execute(
                "ALTER TABLE grace.conversation_turns "
                "ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS grace.knowledge_documents ("
                "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
                "title TEXT NOT NULL, source TEXT, content_hash TEXT UNIQUE, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS grace.knowledge_chunks ("
                "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, "
                "document_id BIGINT NOT NULL REFERENCES grace.knowledge_documents(id) ON DELETE CASCADE, "
                "chunk_index INTEGER NOT NULL, content TEXT NOT NULL, "
                "UNIQUE(document_id, chunk_index))"
            )
            db.execute(
                "INSERT INTO grace.conversations (title, is_default) "
                "VALUES ('Grace chat', TRUE) ON CONFLICT DO NOTHING"
            )
            db.execute(
                "UPDATE grace.conversation_turns SET conversation_id = ("
                "SELECT id FROM grace.conversations WHERE is_default) "
                "WHERE conversation_id IS NULL"
            )
            db.execute(
                "ALTER TABLE grace.conversation_turns "
                "ALTER COLUMN conversation_id SET NOT NULL"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS conversation_turns_order "
                "ON grace.conversation_turns (conversation_id, id DESC)"
            )

    def _get_default_conversation_id(self) -> UUID:
        with self._connect() as db:
            row = db.execute(
                "SELECT id FROM grace.conversations WHERE is_default"
            ).fetchone()
        if row is None:
            raise RuntimeError("Could not initialize Grace's default conversation")
        return row[0]

    def recent(self, conversation_id: UUID | None = None) -> list[dict[str, str]]:
        conversation_id = conversation_id or self.conversation_id
        with self._connect() as db:
            rows = db.execute(
                "SELECT role, content FROM grace.conversation_turns "
                "WHERE conversation_id = %s ORDER BY id DESC LIMIT %s",
                (conversation_id, self.max_turns * 2),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def add_exchange(
        self,
        user_text: str,
        assistant_text: str,
        conversation_id: UUID | None = None,
    ) -> None:
        conversation_id = conversation_id or self.conversation_id
        exchange_id = uuid4()
        with self._connect() as db:
            db.executemany(
                "INSERT INTO grace.conversation_turns "
                "(conversation_id, exchange_id, role, content) "
                "VALUES (%s, %s, %s, %s)",
                [
                    (conversation_id, exchange_id, "user", user_text),
                    (conversation_id, exchange_id, "assistant", assistant_text),
                ],
            )
