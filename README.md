# Mind

The shared memory framework for the AGi agents — **Grace** (PC, AIVA, ROS2)
and **Aiko** (Jetson, non-ROS alike).

## Design

- **One contract**: `memory.api` defines the `Entry` shape and the
  `MemoryBackend` interface (append / search / recent / close).
- **Pluggable backends**: journal (append-only JSONL, default), sqlite;
  vector stores arrive later behind the same interface.
- **Conformance suite**: `memory.conformance.run_all(name, factory)` — every
  backend, bundled or future (ROS2-wrapped server, vector DB), must pass it.
- **Single writer**: one process owns a store; concurrency is the server
  layer's job. The journal file is safe for concurrent *readers*.
- **Explainable ranking**: recency half-life + importance + word overlap
  (`memory.scoring`) — the debuggable baseline before embeddings.

## Usage

```python
from memory import open_memory

mem = open_memory('~/AGi/memory/grace.jsonl')   # or grace.db
mem.append({'agent': 'grace', 'kind': 'dialogue',
            'text': 'OppaAI asked me to draw a mug',
            'tags': ['drawing'], 'importance': 0.7})
mem.search('mug drawing')
mem.recent(agent='grace', limit=20)
```

## Install

```bash
pip install -e ~/AGi/mind            # into the agent's venv
```

No third-party dependencies; stdlib only.


## Conversation history

`memory.conversation.ConversationStore` saves each user/assistant exchange
together and returns the latest exchanges for a given conversation, oldest
first. The recall window does not delete older exchanges.

```python
from memory.conversation import ConversationStore

store = ConversationStore("~/AGi/mind/grace.sqlite3", max_turns=8)
store.add_exchange("Hello Grace", "Hi!")
recent = store.recent()
```

The store uses the `conversations` and `conversation_turns` tables from
AIVA's SQLite database. Existing history can be opened in place. AIVA owns
the configured database path and uses its adapter to handle Canvas studies.
