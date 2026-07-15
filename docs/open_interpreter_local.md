# Open Interpreter Local Profile

Open Interpreter is configured as an optional OSS shell/code-execution agent
over the local OpenAI-compatible DiffusionGemma endpoint.

```bash
scripts/install_open_interpreter_local.sh
scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run
scripts/dg_agent.sh open-interpreter -- --repo /repo --smoke-import
scripts/dg_agent.sh open-interpreter -- --repo /repo --task "Inspect this repo"
```

The profile uses:

```text
api_base: http://127.0.0.1:4100/v1
api_key: dummy
model: openai/diffusiongemma-local
context_window: 768
max_tokens: 256
auto_run: false
safe_mode: ask
```

Keep real repository edits on `scripts/dg_agent.sh agent/session/task`. Use
Open Interpreter for short interactive experiments where its upstream
code-execution shell is useful.
