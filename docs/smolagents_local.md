# smolagents Local Wrapper

Hugging Face smolagents is an optional open-source framework layer over the
local OpenAI-compatible DiffusionGemma endpoint. It gives us a ready-made
`CodeAgent` loop without writing a new agent framework from scratch.

Install:

```bash
scripts/install_smolagents_local.sh
```

Dry-run the profile:

```bash
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --dry-run
```

Import smoke:

```bash
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --smoke-import
```

Run a small framework experiment:

```bash
scripts/dg_agent.sh smolagents -- --repo /path/to/repo --task "Summarize this repo"
```

Profile:

```text
package: smolagents[toolkit] + openai
agent: smolagents.CodeAgent
model class: smolagents.OpenAIModel
base_url: http://127.0.0.1:4100/v1
model: diffusiongemma-local
max_steps: 2
```

Config:

```text
configs/client_profiles/smolagents.dg.json
```

Repo-local launcher after `workspace-init`:

```bash
.dg-agent/bin/smolagents --dry-run
```

This is a framework compatibility route. For reliable code edits, keep using
`scripts/dg_agent.sh agent`, `session`, or `task`, which bound context and keep
verification artifacts.

Smoke:

```bash
scripts/dg_agent.sh smoke --suite smolagents --timeout 180
```
