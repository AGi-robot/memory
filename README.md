# AGi memory

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
pip install -e ~/AGi/memory            # into the agent's venv
```

No third-party dependencies; stdlib only.
