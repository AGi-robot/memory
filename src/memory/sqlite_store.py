"""SQLite backend: queryable, transactional, same contract as the journal."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import scoring
from .api import MemoryBackend, normalize

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    agent TEXT NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    importance REAL NOT NULL DEFAULT 0.5,
    meta TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_entries_ts ON entries(ts DESC);
'''


class SqliteBackend(MemoryBackend):
    def __init__(self, path, *, timeout=5.0):
        self.path = Path(path).expanduser()
        if str(self.path) != ':memory:':
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), timeout=timeout)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def append(self, entry):
        stored = normalize(entry)
        self.conn.execute(
            'INSERT INTO entries (ts, agent, kind, text, tags, importance, meta)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?)',
            (stored['ts'], stored['agent'], stored['kind'], stored['text'],
             json_dumps(stored['tags']), stored['importance'],
             json_dumps(stored['meta'])))
        self.conn.commit()
        return stored

    def search(self, query, *, limit=8):
        # broad LIKE prefilter, exact ranking in python (portable, no FTS5 dep)
        words = scoring.terms(query)
        rows = []
        if words:
            clause = ' OR '.join('text LIKE ?' for _ in words)
            params = [f'%{w}%' for w in words]
            rows = self.conn.execute(
                f'SELECT * FROM entries WHERE {clause}', params).fetchall()
        if not rows:
            rows = self.conn.execute(
                'SELECT * FROM entries ORDER BY ts DESC LIMIT 200').fetchall()
        entries = [self._row(row) for row in rows]
        entries.sort(key=lambda e: scoring.score(e, query), reverse=True)
        return entries[:limit]

    def recent(self, *, limit=20, agent=None):
        if agent is None:
            rows = self.conn.execute(
                'SELECT * FROM entries ORDER BY ts DESC LIMIT ?', (limit,)).fetchall()
        else:
            rows = self.conn.execute(
                'SELECT * FROM entries WHERE agent = ? ORDER BY ts DESC LIMIT ?',
                (agent, limit)).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row):
        entry = {'ts': row['ts'], 'agent': row['agent'], 'kind': row['kind'],
                 'text': row['text'], 'tags': json_loads(row['tags']),
                 'importance': row['importance'], 'meta': json_loads(row['meta'])}
        return entry

    def close(self):
        self.conn.close()


def json_dumps(value):
    import json
    return json.dumps(value, ensure_ascii=False)


def json_loads(value):
    import json
    return json.loads(value)
