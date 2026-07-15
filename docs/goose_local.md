# Goose Local Agent

Goose is installed as an optional open-source agent shell over the local
DiffusionGemma OpenAI-compatible proxy.

Install or refresh:

```bash
cd /root/diffusiongemma-agent
scripts/install_goose_local.sh
```

Run a bounded non-interactive check:

```bash
scripts/run_goose_local.sh run \
  --no-session \
  --no-profile \
  --max-turns 1 \
  --text "Inspect the current directory and summarize what is here."
```

Or through the unified entrypoint:

```bash
scripts/dg_agent.sh goose -- run \
  --no-profile \
  --max-turns 1 \
  --text "Reply exactly OK."
```

Run Goose with the DG MCP tool server and Serena semantic/LSP MCP mounted as
stdio extensions:

```bash
scripts/dg_agent.sh goose-mcp -- info -v
scripts/dg_agent.sh goose-mcp -- run \
  --no-session \
  --no-profile \
  --max-turns 1 \
  --text "Use available tools only if needed; reply OK."
```

Expose the same Goose + DG MCP profile through ACP:

```bash
scripts/dg_agent.sh goose-acp
scripts/dg_agent.sh goose-serve -- --host 127.0.0.1 --port 3294
```

The MCP profile is copied from:

```text
configs/client_profiles/goose-mcp.dg.yaml
```

The profile exposes two MCP extensions:

- `dg_agent`: reliable local workflow tools for repo context, sessions, tasks, and verification.
- `serena`: upstream semantic/LSP tools for symbols, references, diagnostics, renames, and safe symbol edits.

`scripts/run_goose_mcp_local.sh` uses an isolated Goose HOME at
`.tools/goose-dg-mcp-home` by default, so it does not mutate the user-global
`~/.config/goose/config.yaml`.

The launcher sets:

- `GOOSE_PROVIDER=openai`
- `GOOSE_MODEL=diffusiongemma-26b-a4b-it-iq4xs-aider-local`
- `OPENAI_HOST=http://127.0.0.1:8090`
- `OPENAI_API_KEY=dummy`

## Status

This is experimental. Goose provides a stronger ready-made UX than a custom
wrapper, including sessions, MCP/extensions, review, and TUI commands. The
current local DiffusionGemma profile is still weak at native tool-calling, so
Goose should be treated as a shell/agent experiment, not the primary reliable
edit path.

For reliable repository edits, use:

```bash
scripts/dg_agent.sh session --repo /repo --task "..." --file path --auto-test --rollback-on-failure
scripts/dg_agent.sh task --repo /repo --plan plan.json --rollback-on-failure
```

## Smoke

```bash
scripts/dg_agent.sh smoke --suite goose --timeout 180
scripts/dg_agent.sh smoke --suite goose-mcp --timeout 180
scripts/dg_agent.sh smoke --suite goose-acp --timeout 180
```

The smoke checks that Goose is installed, the local proxy is healthy, streaming
OpenAI-compatible responses work, and the Goose CLI can load its local profile.
It deliberately does not run a full agent loop because this model can still
stall in Goose title-generation/tool-calling flows.
