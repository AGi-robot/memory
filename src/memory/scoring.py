"""Why a memory surfaces: recency, importance, and word overlap.

Deliberately simple and explainable - the debuggable baseline before any
vector store. score(entry, terms) in [0, 1]; backends sort by it.
"""
from __future__ import annotations

import heapq
import math
import time

# Weights: relevance dominates, then importance, then recency.
W_MATCH, W_IMPORTANCE, W_RECENCY = 0.6, 0.25, 0.15
RECENCY_HALF_LIFE_DAYS = 21.0

_STOPWORDS = {'a', 'an', 'the', 'of', 'and', 'or', 'to', 'in', 'on', 'is',
              'was', 'it', 'for', 'with', 'at', 'by', 'my', 'me', 'you'}


def terms(query):
    return [w for w in ''.join(c if c.isalnum() else ' ' for c in query.lower()).split()
            if w and w not in _STOPWORDS]


def match_score(entry_text, query_terms):
    """Fraction of query terms present in the entry text."""
    if not query_terms:
        return 0.0
    words = set(''.join(c if c.isalnum() else ' ' for c in entry_text.lower()).split())
    hits = sum(1 for t in query_terms if t in words)
    return hits / len(query_terms)


def recency_score(ts, now=None):
    """Exponential decay with a 21-day half life."""
    now = now if now is not None else time.time()
    age_days = max(0.0, now - float(ts)) / 86400.0
    return math.exp2(-age_days / RECENCY_HALF_LIFE_DAYS)


def score(entry, query, *, now=None):
    query_terms = terms(query) if query else []
    return _score(entry, query_terms, now)


def _score(entry, query_terms, now):
    return (W_MATCH * match_score(entry.get('text', ''), query_terms)
            + W_IMPORTANCE * float(entry.get('importance', 0.5))
            + W_RECENCY * recency_score(entry.get('ts', 0), now))



def rank(entries, query, limit):
    """Rank all entries consistently, keeping only the best limit in memory."""
    query_terms = terms(query) if query else []
    now = time.time()
    return heapq.nlargest(limit, entries, key=lambda entry: _score(entry, query_terms, now))
