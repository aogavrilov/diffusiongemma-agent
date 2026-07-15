# Stack Watchdog

`scripts/run_stack_watchdog.sh` is the recovery layer for the local
DiffusionGemma agent stack.

It checks:

- backend health: `http://127.0.0.1:4100/healthz`
- safe agent gateway: `http://127.0.0.1:8090/healthz`
- OpenAI-compatible model list: `http://127.0.0.1:4100/v1/models`

Common commands:

```bash
scripts/dg_agent.sh status
scripts/dg_agent.sh up --wait-timeout 180
scripts/dg_agent.sh watchdog -- status --json
scripts/dg_agent.sh watchdog -- ensure --restart
scripts/dg_agent.sh watchdog -- watch --interval 30 --restart
```

The watchdog starts the proxy through the repo-local WSL gateway runner. It
starts the backend only when `DG_BACKEND_START_CMD`, `DG_BACKEND_START_SCRIPT`,
or a repo-local `scripts/start_agent_fast_service_windows.ps1` is available.
That avoids guessing the heavyweight model launch command.
