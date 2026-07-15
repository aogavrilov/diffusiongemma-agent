# CrewAI Local Wrapper

CrewAI is an optional open-source multi-agent framework layer over the local
OpenAI-compatible DiffusionGemma endpoint. It gives us a ready-made `Agent`,
`Task`, and `Crew` orchestration model without writing another agent runtime
from scratch.

Install:

```bash
scripts/install_crewai_local.sh
```

Dry-run the profile:

```bash
scripts/dg_agent.sh crewai -- --repo /path/to/repo --dry-run
```

Import smoke:

```bash
scripts/dg_agent.sh crewai -- --repo /path/to/repo --smoke-import
```

Run a small framework experiment:

```bash
scripts/dg_agent.sh crewai -- --repo /path/to/repo --task "Summarize this repo"
```

Profile:

```text
package: crewai
classes: Agent, Task, Crew, LLM
model: openai/diffusiongemma-local
base_url: http://127.0.0.1:4100/v1
process: sequential
```

Config:

```text
configs/client_profiles/crewai.dg.json
```

Repo-local launcher after `workspace-init`:

```bash
.dg-agent/bin/crewai --dry-run
```

This is a framework compatibility route. For reliable code edits, keep using
`scripts/dg_agent.sh agent`, `session`, or `task`, which bound context and keep
verification artifacts.

Smoke:

```bash
scripts/dg_agent.sh smoke --suite crewai --timeout 180
```
