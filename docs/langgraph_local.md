# LangGraph Local Wrapper

LangGraph/LangChain is an optional open-source graph-agent framework layer over
the local OpenAI-compatible DiffusionGemma endpoint. It gives us a ready-made
agent graph runtime without writing a new orchestration framework from scratch.

Install:

```bash
scripts/install_langgraph_local.sh
```

On this Windows host the working install route is WSL-first. Linux cp314 wheels
are cached in `.wheelhouse/langgraph-wsl-cp314`, and the runnable venv is
`.venv-langgraph-wsl`. A Windows venv can be created, but Windows App Control
blocks native `pydantic_core` DLL loading, so `run_langgraph_local.sh` bridges
Git Bash/PowerShell calls into WSL when that venv is present.

Dry-run the profile:

```bash
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --dry-run
```

Import smoke:

```bash
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --smoke-import
```

Run a small framework experiment:

```bash
scripts/dg_agent.sh langgraph -- --repo /path/to/repo --task "Summarize this repo"
```

Profile:

```text
package: langgraph + langchain + langchain-openai
installed: .venv-langgraph-wsl, Python 3.14, local cp314 wheelhouse
agent factory: langchain.agents.create_agent
fallback: langgraph.prebuilt.create_react_agent
model class: langchain_openai.ChatOpenAI
base_url: http://127.0.0.1:4100/v1
model: diffusiongemma-local
```

Config:

```text
configs/client_profiles/langgraph.dg.json
```

Repo-local launcher after `workspace-init`:

```bash
.dg-agent/bin/langgraph --dry-run
```

This is a framework compatibility route. For reliable code edits, keep using
`scripts/dg_agent.sh agent`, `session`, or `task`, which bound context and keep
verification artifacts.

Smoke:

```bash
scripts/dg_agent.sh smoke --suite langgraph --timeout 180
```
