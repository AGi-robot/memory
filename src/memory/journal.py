"""The default backend: an append-only JSONL journal, human-readable.

One JSON object per line; the file IS the memory (copy it, cat it, git it).
Reads keep an in-memory index rebuilt on open; writes append + flush.
The single writer holds this file; readers may tail it concurrently.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import scoring
from .api import MemoryBackend, normalize


class JournalBackend(MemoryBackend):
    def __init__(self, path, *, autosave=True):
        self.path = Path(path).expanduser()
        self.autosave = autosave
        if self.path.parent and str(self.path.parent):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict] = []
        self._dirty = False
        if self.path.exists():
            with open(self.path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue  # torn last line from a crash: skip

    def append(self, entry):
        stored = normalize(entry)
        self.entries.append(stored)
        self._dirty = True
        if self.autosave:
            self._flush_one(stored)
        return stored

    def search(self, query, *, limit=8):
        ranked = sorted(self.entries,
                        key=lambda e: scoring.score(e, query), reverse=True)
        return ranked[:limit]

    def recent(self, *, limit=20, agent=None):
        pool = [e for e in self.entries if agent is None or e.get('agent') == agent]
        pool.sort(key=lambda e: e.get('ts', 0), reverse=True)
        return pool[:limit]

    def _flush_one(self, entry):
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        self._dirty = False

    def close(self):
        if self._dirty and not self.autosave:
            self.path.write_text(
                ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in self.entries),
                encoding='utf-8')
            self._dirty = False
