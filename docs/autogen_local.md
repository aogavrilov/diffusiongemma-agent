# AutoGen Local Wrapper

AutoGen AgentChat is an optional open-source Python framework layer over the
local DiffusionGemma OpenAI-compatible endpoint.

Install or refresh:

```bash
scripts/install_autogen_local.sh
```

Dry-run the local profile:

```bash
scripts/dg_agent.sh autogen -- --repo /path/to/repo --dry-run
```

Smoke the imports and profile:

```bash
scripts/dg_agent.sh autogen -- --repo /path/to/repo --smoke-import
```

Run a small AutoGen AgentChat task:

```bash
scripts/dg_agent.sh autogen -- --repo /path/to/repo --task "Summarize this repo"
```

The wrapper uses:

```text
package: autogen-agentchat + autogen-ext[openai]
model client: autogen_ext.models.openai.OpenAIChatCompletionClient
base_url: http://127.0.0.1:4100/v1
model: diffusiongemma-local
```

Config:

```text
configs/client_profiles/autogen.dg.json
```

Repo-local launcher after `workspace-init`:

```bash
.dg-agent/bin/autogen --dry-run
```

This is a framework compatibility path, not the default reliable coding path.
For actual edits, prefer `scripts/dg_agent.sh agent`, `session`, or `task`.

Verification:

```bash
scripts/dg_agent.sh smoke --suite autogen --timeout 180
```
