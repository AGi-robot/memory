import json
from unittest.mock import patch
import pytest
from memory.journal import JournalBackend


@pytest.mark.parametrize('tail', ['{"text": "torn', json.dumps({'text': 'previous', 'ts': 1})])
def test_append_after_unterminated_record_survives_reopen(tmp_path, tail):
    path = tmp_path / 'memory.jsonl'
    path.write_text(tail)
    store = JournalBackend(path)
    store.append({'text': 'new memory'})
    store.close()
    reopened = JournalBackend(path)
    assert any(e['text'] == 'new memory' for e in reopened.entries)
    if tail.endswith('}'):
        assert any(e['text'] == 'previous' for e in reopened.entries)


def test_failed_write_is_not_visible_as_committed_memory(tmp_path):
    store = JournalBackend(tmp_path / 'memory.jsonl')
    with patch.object(store, '_flush_one', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            store.append({'text': 'not saved'})
    assert store.entries == []
