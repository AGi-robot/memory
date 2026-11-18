import time

import pytest

from memory import api, scoring
from memory.conformance import bundled_factories, run_all


# ------------------------------------------------- conformance ------------
@pytest.mark.parametrize('name', sorted(bundled_factories()))
def test_backend_conformance(name):
    assert run_all(name, bundled_factories()[name])


def test_open_memory_dispatch():
    assert isinstance(api.open_memory('/tmp/x/mem.jsonl'), api.MemoryBackend)
    assert isinstance(api.open_memory('/tmp/x/mem.db'), api.MemoryBackend)
    with pytest.raises(ValueError):
        api.open_memory('/tmp/x/mem.weird')


# ----------------------------------------------------- normalize ----------
def test_normalize_fills_defaults():
    entry = api.normalize({'text': 'hello'})
    assert 0 < entry['ts'] <= time.time() + 1
    assert entry['agent'] == 'unknown' and entry['kind'] == 'event'
    assert entry['importance'] == 0.5 and entry['tags'] == []


def test_normalize_clamps_importance_and_rejects_garbage():
    assert api.normalize({'text': 'x', 'importance': 5})['importance'] == 1.0
    assert api.normalize({'text': 'x', 'importance': -2})['importance'] == 0.0
    with pytest.raises(ValueError):
        api.normalize({'kind': 'event', 'text': '  '})
    with pytest.raises(ValueError):
        api.normalize({'kind': 'wat', 'text': 'x'})


# ------------------------------------------------------- scoring ----------
def test_scoring_ranks_relevant_first():
    now = time.time()
    old_match = {'ts': now - 90 * 86400, 'text': 'mug drawing on canvas',
                 'importance': 0.5}
    new_miss = {'ts': now, 'text': 'database migration finished',
                'importance': 0.5}
    new_match = {'ts': now, 'text': 'mug drawing finished for oppaai',
                 'importance': 0.5}
    assert scoring.score(new_match, 'mug drawing') > scoring.score(old_match, 'mug drawing')
    assert scoring.score(old_match, 'mug drawing') > scoring.score(new_miss, 'mug drawing')


def test_terms_drops_stopwords():
    assert scoring.terms('the state of the mug and me') == ['state', 'mug']
