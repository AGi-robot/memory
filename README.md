# Memory

Memory is the shared memory component for AGi agents, including **Grace** (hosted
by AIVA) and **Aiko**. It owns reusable memory APIs and storage; AIVA remains
the runtime that connects Grace's chat, ROS topics, and user interface.

## Current scope

Memory currently provides two distinct pieces:

- A general memory API with journal and SQLite backends for structured entries.
- `memory.conversation.ConversationStore`, a SQLite store for paired user and
  assistant turns. AIVA uses this store for Grace's chat history and adds its
  own Canvas-specific study and context behavior in `GraceMemory`.

Conversation history is persistent. `recent()` returns only the configured
number of latest exchanges for active context; it does not delete older turns
or perform semantic retrieval. The conversation store reuses the
`conversations` and `conversation_turns` tables used by AIVA, so existing
databases can be opened in place. Memory owns the shared storage implementation;
the host application chooses the database path and its application-specific
policies.

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

mem = open_memory('~/.agi/profile/grace.jsonl')   # or grace.db
mem.append({'agent': 'grace', 'kind': 'dialogue',
            'text': 'OppaAI asked me to draw a mug',
            'tags': ['drawing'], 'importance': 0.7})
mem.search('mug drawing')
mem.recent(agent='grace', limit=20)
```

## ROS 2 package

The reusable Python library lives in `src/memory/`. The repository root also contains the `agi_memory` ament_python package
metadata, so colcon can discover and install the library in the AIVA workspace.
`agi_memory` does not start a ROS node: AIVA imports `memory.conversation`
directly into its `aiva_chat` node and uses a local SQLite database. A separate
ROS memory service would only be useful if multiple processes needed to share
one store over ROS.

In the AGi checkout, AIVA links this package into `AIVA/shell/src/agi_memory`;
colcon builds it with the other workspace packages.

## Install

```bash
pip install -e ~/AGi/AIVA/mind/memory  # into the agent's venv
```

No third-party dependencies; stdlib only.


## Conversation history

`memory.conversation.ConversationStore` saves each user/assistant exchange
together and returns the latest exchanges for a given conversation, oldest
first. The recall window does not delete older exchanges.

```python
from memory.conversation import ConversationStore

store = ConversationStore("~/.agi/profile/grace_memory.sqlite3", max_turns=8)
store.add_exchange("Hello Grace", "Hi!")
recent = store.recent()
```

Install Memory into the Python environment that runs the application. AIVA's
`requirements.txt` installs the package from this repository. For local
development, install the checkout with `pip install -e .` from the Memory repository root.

The API deliberately returns simple role/content dictionaries suitable for a
chat completion request. It does not call a language model, choose tools, or
decide which memories are relevant. Those behaviors belong to the application
or future Memory components.
