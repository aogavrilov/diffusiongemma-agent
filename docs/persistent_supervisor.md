# Persistent Local Supervisor

The local coding route keeps DiffusionGemma away from native tool selection. A
controller performs bounded repository retrieval, delegates edits to the known
Aider/session path, verifies each attempt, and records artifacts outside the
target repository.

```bash
scripts/dg_agent.sh autonomous -- --repo /repo --task "Fix src/x.py and run pytest -q" --file src/x.py
```

Each run writes `state.json`, `SUMMARY.md`, retrieval results, checkpoints, and
session reports under `runlogs/dg-autonomous-supervisor/`. The BM25 document
cache is persistent under `runlogs/dg-retrieval-index/`, so a later task in the
same repository does not rebuild the source index. A clean Git worktree is
required by default. On a failed attempt the controller may reverse only the
tracked patch produced by that attempt; it refuses to remove untracked files.

For complex multi-file work, use a separate stronger planner through an
OpenAI-compatible endpoint. It is advisory only: it is sent the task and
retrieved paths, cannot invoke tools, and cannot write files.

```bash
export DG_PLANNER_URL=http://planner-host/v1
export DG_PLANNER_MODEL=your-strong-coding-model
export DG_PLANNER_API_KEY=dummy
scripts/dg_agent.sh autonomous -- --repo /repo --task "..."
```

Do not host that planner alongside the 16 GiB full-GPU DiffusionGemma model.
Use another machine or a remote endpoint. Without a configured planner the
controller remains retrieval-first and deterministic.
