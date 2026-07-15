#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_CMD="python3"
if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
  PY_CMD="python"
fi
TMP_REPO="$(mktemp -d /tmp/dg-workspace-init-smoke.XXXXXX)"

cleanup() {
  echo "DG workspace init smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
cat > hello.py <<'PY'
def greet(name):
    return f"hello {name}"
PY
git add hello.py
git commit -qm "initial"

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >.dg-workspace-init.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-init.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
statuses = {str(Path(item["path"]).relative_to(Path(data["workspace_dir"]))).replace("\\", "/"): item["status"] for item in data["files"]}
for name in [
    "client-pack.json",
    "AGENT_HUB.md",
    "agent-hub.json",
    "COMMANDS.md",
    "command-kit.json",
    "env.sh",
    "README.md",
    "aider.dg-fast.conf.yml",
    "aider.dg-model-settings.yml",
    "aider.dg-model-metadata.json",
    "continue.config.yaml",
    "opencode.dg.json",
    "opencode.dg-mcp.json",
    "openhands.dg.toml",
    "openhands.env",
    "qwen-code.mcp.json",
    "autogen.dg.json",
    "smolagents.dg.json",
    "langgraph.dg.json",
    "crewai.dg.json",
    "open-interpreter.dg.json",
    "llamaindex.dg.json",
    "haystack.dg.json",
    "swe-agent.dg.yaml",
    "mini-swe-agent.dg.yaml",
    "mcp-server.json",
    "mcp-client-snippets.json",
    "claude-code.mcp.json",
    "claude-desktop-mcp.json",
    "cursor.mcp.json",
    "vscode.mcp.json",
    "agent-instructions.md",
    "AGENTS.dg.md",
    "CLAUDE.dg.md",
    "copilot-instructions.dg.md",
    "diffusiongemma.instructions.md",
    "cursor-rules.dg.mdc",
    "goose-mcp.dg.yaml",
    "litellm-local-model-registry.json",
    "commands/dg-report.md",
    "commands/dg-smoke.md",
    "commands/dg-context.md",
    "commands/dg-plan-task.md",
    "commands/dg-agent.md",
    "commands/dg-verify.md",
    "commands/dg-mcp-handoff.md",
    "commands/dg-codex.md",
    "claude-skill/SKILL.md",
    "CODEX.md",
    "codex.config.toml",
    "codex.env",
    "IDE_CLIENTS.md",
    "ide-client-snippets.json",
    "openai-compatible.local.json",
    "openai.env",
    "kilo-code.config.json",
    "bin/run",
    "bin/agent",
    "bin/autonomous",
    "bin/context",
    "bin/rag",
    "bin/repo-pack",
    "bin/repo-map",
    "bin/ast-grep",
    "bin/code-outline",
    "bin/client-init",
    "bin/client-smoke",
    "bin/client-report",
    "bin/agent-commands",
    "bin/codex-profile",
    "bin/agent-bridge",
    "bin/hub",
    "bin/plan",
    "bin/edit",
    "bin/task",
    "bin/verify",
    "bin/status",
    "bin/doctor",
    "bin/up",
    "bin/down",
    "bin/preflight",
    "bin/capabilities",
    "bin/sessions",
    "bin/supervisor",
    "bin/web",
    "bin/aider",
    "bin/opencode",
    "bin/opencode-agent",
    "bin/opencode-mcp",
    "bin/opencode-acp",
    "bin/goose",
    "bin/goose-mcp",
    "bin/goose-acp",
    "bin/goose-serve",
    "bin/openhands",
    "bin/openhands-mcp",
    "bin/qwen-code",
    "bin/autogen",
    "bin/smolagents",
    "bin/langgraph",
    "bin/crewai",
    "bin/open-interpreter",
    "bin/llamaindex",
    "bin/haystack",
    "bin/swe-agent",
    "bin/mini-swe-agent",
    "bin/mini-swe-run",
    "bin/mini-swe-runs",
    "bin/mcp",
    "bin/mcp-http",
    "bin/serena-mcp",
    "bin/mcp-client-config",
    "bin/agent-rules",
]:
    assert statuses[name] == "written", statuses
PY

test -s .dg-agent/client-pack.json
test -s .dg-agent/AGENT_HUB.md
test -s .dg-agent/agent-hub.json
test -s .dg-agent/env.sh
test -s .dg-agent/README.md
test -s .dg-agent/aider.dg-fast.conf.yml
test -s .dg-agent/aider.dg-model-settings.yml
test -s .dg-agent/aider.dg-model-metadata.json
test -s .dg-agent/continue.config.yaml
test -s .dg-agent/opencode.dg.json
test -s .dg-agent/opencode.dg-agent.json
test -s .dg-agent/opencode.dg-mcp.json
test -s .dg-agent/openhands.dg.toml
test -s .dg-agent/openhands.env
test -s .dg-agent/qwen-code.mcp.json
test -s .dg-agent/autogen.dg.json
test -s .dg-agent/smolagents.dg.json
test -s .dg-agent/langgraph.dg.json
test -s .dg-agent/crewai.dg.json
test -s .dg-agent/open-interpreter.dg.json
test -s .dg-agent/llamaindex.dg.json
test -s .dg-agent/haystack.dg.json
test -s .dg-agent/swe-agent.dg.yaml
test -s .dg-agent/mini-swe-agent.dg.yaml
test -s .dg-agent/mcp-server.json
test -s .dg-agent/mcp-client-snippets.json
test -s .dg-agent/claude-code.mcp.json
test -s .dg-agent/claude-desktop-mcp.json
test -s .dg-agent/cursor.mcp.json
test -s .dg-agent/vscode.mcp.json
test -s .dg-agent/agent-instructions.md
test -s .dg-agent/AGENTS.dg.md
test -s .dg-agent/CLAUDE.dg.md
test -s .dg-agent/copilot-instructions.dg.md
test -s .dg-agent/diffusiongemma.instructions.md
test -s .dg-agent/cursor-rules.dg.mdc
test -s .dg-agent/goose-mcp.dg.yaml
test -s .dg-agent/litellm-local-model-registry.json
test -s .dg-agent/CODEX.md
test -s .dg-agent/codex.config.toml
test -s .dg-agent/codex.env
test -s .dg-agent/IDE_CLIENTS.md
test -s .dg-agent/ide-client-snippets.json
test -s .dg-agent/openai-compatible.local.json
test -s .dg-agent/openai.env
test -s .dg-agent/kilo-code.config.json
"$PY_CMD" -m json.tool .dg-agent/client-pack.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/agent-hub.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/ide-client-snippets.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/openai-compatible.local.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/kilo-code.config.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/aider.dg-model-metadata.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/opencode.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/opencode.dg-agent.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/opencode.dg-mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/qwen-code.mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/autogen.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/smolagents.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/langgraph.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/crewai.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/open-interpreter.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/llamaindex.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/haystack.dg.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/mcp-server.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/mcp-client-snippets.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/claude-code.mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/claude-desktop-mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/cursor.mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/vscode.mcp.json >/dev/null
"$PY_CMD" -m json.tool .dg-agent/litellm-local-model-registry.json >/dev/null
grep -F "OPENAI_BASE_URL=http://127.0.0.1:4100/v1" .dg-agent/env.sh
grep -F "AIDER_OPENAI_API_BASE=http://127.0.0.1:8090/v1" .dg-agent/env.sh
grep -F "LLM_MODEL=litellm_proxy/diffusiongemma-local" .dg-agent/env.sh
grep -F "SWE_AGENT_MODEL=openai/diffusiongemma-local" .dg-agent/env.sh
grep -F "QWEN_CODE_MCP_CONFIG=" .dg-agent/env.sh
grep -F "qwen-code.mcp.json" .dg-agent/env.sh
grep -F "QWEN_CODE_COMMAND=scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "AUTOGEN_CONFIG=" .dg-agent/env.sh
grep -F "autogen.dg.json" .dg-agent/env.sh
grep -F "AUTOGEN_COMMAND=scripts/dg_agent.sh autogen -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "AUTOGEN_MODEL=diffusiongemma-local" .dg-agent/env.sh
grep -F "SMOLAGENTS_CONFIG=" .dg-agent/env.sh
grep -F "smolagents.dg.json" .dg-agent/env.sh
grep -F "SMOLAGENTS_COMMAND=scripts/dg_agent.sh smolagents -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "SMOLAGENTS_MODEL=diffusiongemma-local" .dg-agent/env.sh
grep -F "LANGGRAPH_CONFIG=" .dg-agent/env.sh
grep -F "langgraph.dg.json" .dg-agent/env.sh
grep -F "LANGGRAPH_COMMAND=scripts/dg_agent.sh langgraph -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "LANGGRAPH_MODEL=diffusiongemma-local" .dg-agent/env.sh
grep -F "CREWAI_CONFIG=" .dg-agent/env.sh
grep -F "crewai.dg.json" .dg-agent/env.sh
grep -F "CREWAI_COMMAND=scripts/dg_agent.sh crewai -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "CREWAI_MODEL=openai/diffusiongemma-local" .dg-agent/env.sh
grep -F "OPEN_INTERPRETER_CONFIG=" .dg-agent/env.sh
grep -F "open-interpreter.dg.json" .dg-agent/env.sh
grep -F "OPEN_INTERPRETER_COMMAND=scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "OPEN_INTERPRETER_MODEL=openai/diffusiongemma-local" .dg-agent/env.sh
grep -F "LLAMAINDEX_CONFIG=" .dg-agent/env.sh
grep -F "llamaindex.dg.json" .dg-agent/env.sh
grep -F "LLAMAINDEX_COMMAND=scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "LLAMAINDEX_MODEL=diffusiongemma-local" .dg-agent/env.sh
grep -F "HAYSTACK_CONFIG=" .dg-agent/env.sh
grep -F "haystack.dg.json" .dg-agent/env.sh
grep -F "HAYSTACK_COMMAND=scripts/dg_agent.sh haystack -- --repo /repo --dry-run" .dg-agent/env.sh
grep -F "HAYSTACK_MODEL=diffusiongemma-local" .dg-agent/env.sh
grep -F "DG_MCP_CONFIG=" .dg-agent/env.sh
grep -F "mcp-server.json" .dg-agent/env.sh
grep -F "DG_MCP_CLIENT_SNIPPETS=" .dg-agent/env.sh
grep -F "mcp-client-snippets.json" .dg-agent/env.sh
grep -F "DG_AGENT_BRIDGE_COMMAND=scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp" .dg-agent/env.sh
grep -F "DG_WORKSPACE_AGENT_HUB=.dg-agent/AGENT_HUB.md" .dg-agent/env.sh
grep -F "DG_CLIENT_SMOKE_COMMAND=scripts/dg_agent.sh client-smoke --repo /repo --client cursor" .dg-agent/env.sh
grep -F "DG_CLIENT_REPORT_COMMAND=scripts/dg_agent.sh client-report --repo /repo --client cursor" .dg-agent/env.sh
grep -F "DG_CODEX_PROFILE_COMMAND=scripts/dg_agent.sh codex-profile --repo /repo --target all" .dg-agent/env.sh
grep -F "DG_CODEX_CONFIG_TEMPLATE=.dg-agent/codex.config.toml" .dg-agent/env.sh
grep -F "DG_AGENT_COMMANDS_COMMAND=scripts/dg_agent.sh agent-commands --repo /repo --target all" .dg-agent/env.sh
grep -F "DG_IDE_CLIENTS_HANDOFF=.dg-agent/IDE_CLIENTS.md" .dg-agent/env.sh
grep -F "DG_IDE_CLIENT_SNIPPETS=.dg-agent/ide-client-snippets.json" .dg-agent/env.sh
grep -F "DG_SAFE_AGENT_BASE_URL=http://127.0.0.1:8090/v1" .dg-agent/env.sh
grep -F "DG_SAFE_AGENT_MODEL=diffusiongemma-26b-a4b-it-iq4xs-aider-local" .dg-agent/env.sh
grep -F "DG_REPO_MAP_COMMAND=scripts/dg_agent.sh repo-map" .dg-agent/env.sh
grep -F "DG_AST_GREP_COMMAND=scripts/run_ast_grep.sh" .dg-agent/env.sh
grep -F "DG_CODE_OUTLINE_COMMAND=scripts/dg_agent.sh code-outline" .dg-agent/env.sh
grep -F "DG_SERENA_MCP_COMMAND=scripts/run_serena_mcp.sh" .dg-agent/env.sh
grep -F "GOOSE_MCP_CONFIG=" .dg-agent/env.sh
grep -F "goose-mcp.dg.yaml" .dg-agent/env.sh
grep -F "scripts/dg_agent.sh agent" .dg-agent/README.md
grep -F "aider.dg-fast.conf.yml" .dg-agent/README.md
grep -F ".dg-agent/bin/agent" .dg-agent/README.md
grep -F ".dg-agent/bin/rag" .dg-agent/README.md
grep -F ".dg-agent/bin/repo-pack" .dg-agent/README.md
grep -F ".dg-agent/bin/repo-map" .dg-agent/README.md
grep -F ".dg-agent/bin/ast-grep" .dg-agent/README.md
grep -F ".dg-agent/bin/code-outline" .dg-agent/README.md
grep -F ".dg-agent/bin/client-init --client cursor" .dg-agent/README.md
grep -F ".dg-agent/bin/client-smoke --client cursor" .dg-agent/README.md
grep -F ".dg-agent/bin/client-report --client cursor --live" .dg-agent/README.md
grep -F ".dg-agent/bin/agent-commands --target all" .dg-agent/README.md
grep -F ".dg-agent/bin/codex-profile --target all" .dg-agent/README.md
grep -F ".dg-agent/bin/agent-bridge --server opencode-acp" .dg-agent/README.md
grep -F ".dg-agent/bin/hub" .dg-agent/README.md
grep -F ".dg-agent/bin/opencode-mcp --help" .dg-agent/README.md
grep -F "opencode.dg-agent.json" .dg-agent/README.md
grep -F ".dg-agent/bin/opencode-acp --help" .dg-agent/README.md
grep -F ".dg-agent/bin/capabilities" .dg-agent/README.md
grep -F ".dg-agent/bin/mcp --list-tools" .dg-agent/README.md
grep -F ".dg-agent/bin/mcp-http --help-local" .dg-agent/README.md
grep -F ".dg-agent/bin/serena-mcp --help-local" .dg-agent/README.md
grep -F ".dg-agent/bin/mcp-client-config --client cursor" .dg-agent/README.md
grep -F ".dg-agent/bin/mcp-client-config --client cursor --with-serena" .dg-agent/README.md
grep -F ".dg-agent/bin/mcp-client-config --client cursor --with-oss-stack" .dg-agent/README.md
grep -F ".dg-agent/bin/agent-rules --target all" .dg-agent/README.md
grep -F ".dg-agent/bin/goose-mcp --help-local" .dg-agent/README.md
grep -F ".dg-agent/bin/goose-acp --help" .dg-agent/README.md
grep -F ".dg-agent/bin/goose-serve --help" .dg-agent/README.md
grep -F ".dg-agent/bin/openhands-mcp --reset" .dg-agent/README.md
grep -F ".dg-agent/bin/qwen-code --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/autogen --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/smolagents --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/langgraph --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/crewai --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/open-interpreter --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/llamaindex --dry-run" .dg-agent/README.md
grep -F ".dg-agent/bin/haystack --dry-run" .dg-agent/README.md
grep -F "provider: openai" .dg-agent/continue.config.yaml
grep -F "openai-api-base: http://127.0.0.1:8090/v1" .dg-agent/aider.dg-fast.conf.yml
grep -F "model-settings-file: .dg-agent/aider.dg-model-settings.yml" .dg-agent/aider.dg-fast.conf.yml
grep -F "map-tokens: 0" .dg-agent/aider.dg-fast.conf.yml
grep -F "max_tokens: 256" .dg-agent/aider.dg-model-settings.yml
grep -F 'model = "litellm_proxy/diffusiongemma-local"' .dg-agent/openhands.dg.toml
grep -F "name: openai/diffusiongemma-local" .dg-agent/swe-agent.dg.yaml
grep -F "model_name: openai/diffusiongemma-local" .dg-agent/mini-swe-agent.dg.yaml
grep -F '"diffusiongemma-local-agent"' .dg-agent/mcp-client-snippets.json
grep -F '"repomix"' .dg-agent/mcp-client-snippets.json
grep -F "/root/diffusiongemma-agent/scripts/run_repomix_mcp.sh" .dg-agent/mcp-client-snippets.json
grep -F '"serena"' .dg-agent/mcp-client-snippets.json
grep -F "/root/diffusiongemma-agent/scripts/run_serena_mcp.sh" .dg-agent/mcp-client-snippets.json
grep -F '"diffusiongemma-local-agent"' .dg-agent/qwen-code.mcp.json
grep -F '"repomix"' .dg-agent/qwen-code.mcp.json
grep -F '"serena"' .dg-agent/qwen-code.mcp.json
grep -F 'OpenAIChatCompletionClient' .dg-agent/autogen.dg.json
grep -F '"diffusiongemma-local"' .dg-agent/autogen.dg.json
grep -F 'smolagents.CodeAgent' .dg-agent/smolagents.dg.json
grep -F '"diffusiongemma-local"' .dg-agent/smolagents.dg.json
grep -F 'langchain_openai.ChatOpenAI' .dg-agent/langgraph.dg.json
grep -F '"diffusiongemma-local"' .dg-agent/langgraph.dg.json
grep -F 'crewai.Crew' .dg-agent/crewai.dg.json
grep -F '"openai/diffusiongemma-local"' .dg-agent/crewai.dg.json
grep -F 'interpreter.interpreter' .dg-agent/open-interpreter.dg.json
grep -F '"auto_run": false' .dg-agent/open-interpreter.dg.json
grep -F 'llama_index.llms.openai_like.OpenAILike' .dg-agent/llamaindex.dg.json
grep -F 'llama_index.core.agent.workflow.AgentWorkflow' .dg-agent/llamaindex.dg.json
grep -F 'llama_index.core.agent.workflow.ReActAgent' .dg-agent/llamaindex.dg.json
grep -F '"is_function_calling_model": false' .dg-agent/llamaindex.dg.json
grep -F 'haystack.components.retrievers.in_memory.InMemoryBM25Retriever' .dg-agent/haystack.dg.json
grep -F 'haystack.components.generators.chat.OpenAIChatGenerator' .dg-agent/haystack.dg.json
grep -F '"mcpServers"' .dg-agent/claude-code.mcp.json
grep -F '"mcpServers"' .dg-agent/cursor.mcp.json
grep -F '"servers"' .dg-agent/vscode.mcp.json
grep -F "/root/diffusiongemma-agent/scripts/run_mcp_server.sh" .dg-agent/mcp-client-snippets.json
grep -F "dg_task_note" .dg-agent/agent-instructions.md
grep -F "alwaysApply: true" .dg-agent/cursor-rules.dg.mdc
grep -F 'applyTo: "**"' .dg-agent/diffusiongemma.instructions.md
grep -F "dg_agent:" .dg-agent/goose-mcp.dg.yaml
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_mcp_server.sh" .dg-agent/goose-mcp.dg.yaml
grep -F "serena:" .dg-agent/goose-mcp.dg.yaml
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_serena_mcp.sh" .dg-agent/goose-mcp.dg.yaml
grep -F "DG Local Agent Hub" .dg-agent/AGENT_HUB.md
grep -F "Default MCP bundle" .dg-agent/AGENT_HUB.md
grep -F "agent-bridge --server opencode-acp" .dg-agent/AGENT_HUB.md
grep -F '"recommended_routes"' .dg-agent/agent-hub.json
grep -F '"safe_code_edit"' .dg-agent/agent-hub.json
grep -F "DG Agent Command Kit" .dg-agent/COMMANDS.md
grep -F "dg_client_report" .dg-agent/command-kit.json
grep -F "DG Local Agent Skill" .dg-agent/claude-skill/SKILL.md
grep -F "DG Codex CLI Profile" .dg-agent/CODEX.md
grep -F "DiffusionGemma Local Safe Agent Proxy" .dg-agent/codex.config.toml
grep -F "DG IDE Client Profiles" .dg-agent/IDE_CLIENTS.md
grep -F "safe_agent_proxy" .dg-agent/ide-client-snippets.json
grep -F "DiffusionGemma Local Safe Agent Proxy" .dg-agent/kilo-code.config.json

for script in run agent context rag repo-pack repo-map ast-grep code-outline client-init client-smoke client-report agent-commands codex-profile agent-bridge hub plan edit task verify status doctor up down preflight capabilities sessions supervisor web aider opencode opencode-agent opencode-mcp opencode-acp goose goose-mcp goose-acp goose-serve openhands openhands-mcp qwen-code autogen smolagents langgraph crewai open-interpreter llamaindex haystack swe-agent mini-swe-agent mini-swe-run mini-swe-runs mcp mcp-http serena-mcp mcp-client-config agent-rules; do
  test -x ".dg-agent/bin/$script"
  bash -n ".dg-agent/bin/$script"
done

.dg-agent/bin/run --help >.dg-workspace-run-help.txt
grep -F -- "--start" .dg-workspace-run-help.txt
.dg-agent/bin/agent --help >.dg-workspace-agent-help.txt
grep -F -- "--task TASK" .dg-workspace-agent-help.txt
.dg-agent/bin/context --help >.dg-workspace-context-help.txt
grep -F -- "--max-files MAX_FILES" .dg-workspace-context-help.txt
.dg-agent/bin/rag --help >.dg-workspace-rag-help.txt
grep -F -- "--print-context" .dg-workspace-rag-help.txt
.dg-agent/bin/repo-pack --help >.dg-workspace-repo-pack-help.txt
grep -F -- "--token-budget" .dg-workspace-repo-pack-help.txt
.dg-agent/bin/repo-map --help >.dg-workspace-repo-map-help.txt
grep -F -- "--map-tokens" .dg-workspace-repo-map-help.txt
.dg-agent/bin/ast-grep --help >.dg-workspace-ast-grep-help.txt
grep -F -- "--pattern" .dg-workspace-ast-grep-help.txt
.dg-agent/bin/code-outline --help >.dg-workspace-code-outline-help.txt
grep -F -- "--items" .dg-workspace-code-outline-help.txt
.dg-agent/bin/client-init --help >.dg-workspace-client-init-help.txt
grep -F -- "--client" .dg-workspace-client-init-help.txt
grep -F -- "--no-oss-stack" .dg-workspace-client-init-help.txt
.dg-agent/bin/client-smoke --help >.dg-workspace-client-smoke-help.txt
grep -F -- "--live" .dg-workspace-client-smoke-help.txt
grep -F -- "--no-init" .dg-workspace-client-smoke-help.txt
.dg-agent/bin/client-report --help >.dg-workspace-client-report-help.txt
grep -F -- "--no-write" .dg-workspace-client-report-help.txt
grep -F -- "--live" .dg-workspace-client-report-help.txt
.dg-agent/bin/agent-commands --help >.dg-workspace-agent-commands-help.txt
grep -F -- "--target" .dg-workspace-agent-commands-help.txt
grep -F -- "--print-template" .dg-workspace-agent-commands-help.txt
.dg-agent/bin/codex-profile --help >.dg-workspace-codex-profile-help.txt
grep -F -- "--target" .dg-workspace-codex-profile-help.txt
grep -F -- "--print-template" .dg-workspace-codex-profile-help.txt
.dg-agent/bin/agent-bridge --help >.dg-workspace-agent-bridge-help.txt
grep -F -- "--server" .dg-workspace-agent-bridge-help.txt
grep -F -- "--start" .dg-workspace-agent-bridge-help.txt
.dg-agent/bin/hub >.dg-workspace-hub.md
grep -F "DG Local Agent Hub" .dg-workspace-hub.md
.dg-agent/bin/hub --json >.dg-workspace-hub.json
"$PY_CMD" -m json.tool .dg-workspace-hub.json >/dev/null
grep -F '"acp_agent_server"' .dg-workspace-hub.json
.dg-agent/bin/plan --help >.dg-workspace-plan-help.txt
grep -F -- "--auto-test" .dg-workspace-plan-help.txt
.dg-agent/bin/edit --help >.dg-workspace-edit-help.txt
grep -F -- "--rollback-on-failure" .dg-workspace-edit-help.txt
.dg-agent/bin/task --help >.dg-workspace-task-help.txt
grep -F -- "--plan PLAN" .dg-workspace-task-help.txt
.dg-agent/bin/verify --help >.dg-workspace-verify-help.txt
grep -F -- "--test-cmd TEST_CMD" .dg-workspace-verify-help.txt
.dg-agent/bin/preflight --help >.dg-workspace-preflight-help.txt
grep -F -- "--allow-dirty" .dg-workspace-preflight-help.txt
.dg-agent/bin/capabilities --help >.dg-workspace-capabilities-help.txt
grep -F -- "--latest" .dg-workspace-capabilities-help.txt
.dg-agent/bin/sessions --help >.dg-workspace-sessions-help.txt
grep -F "list" .dg-workspace-sessions-help.txt
.dg-agent/bin/supervisor --help >.dg-workspace-supervisor-help.txt
grep -F "Supervisor around rg" .dg-workspace-supervisor-help.txt
if [[ -x "$DG_ROOT/scripts/run_agentapi_aider.sh" ]]; then
  .dg-agent/bin/web --help >.dg-workspace-web-help.txt
  grep -F "AgentAPI" .dg-workspace-web-help.txt
else
  echo "SKIP workspace web launcher: AgentAPI runner is not installed"
fi
.dg-agent/bin/aider --help >.dg-workspace-aider-help.txt
grep -F -- "--model MODEL" .dg-workspace-aider-help.txt
.dg-agent/bin/opencode-mcp --help >.dg-workspace-opencode-mcp-help.txt 2>&1
grep -F "opencode" .dg-workspace-opencode-mcp-help.txt
.dg-agent/bin/opencode-acp --help >.dg-workspace-opencode-acp-help.txt 2>&1
grep -F "start ACP" .dg-workspace-opencode-acp-help.txt
if [[ "${DG_WORKSPACE_SMOKE_OPTIONAL:-0}" == "1" ]]; then
.dg-agent/bin/goose-mcp --help-local >.dg-workspace-goose-mcp-help.txt
grep -F "DiffusionGemma MCP" .dg-workspace-goose-mcp-help.txt
.dg-agent/bin/goose-acp --help >.dg-workspace-goose-acp-help.txt
grep -F "ACP agent server on stdio" .dg-workspace-goose-acp-help.txt
.dg-agent/bin/goose-serve --help >.dg-workspace-goose-serve-help.txt
grep -F "ACP server over HTTP and WebSocket" .dg-workspace-goose-serve-help.txt
.dg-agent/bin/openhands --help-local >.dg-workspace-openhands-help.txt
grep -F "OpenHands" .dg-workspace-openhands-help.txt
.dg-agent/bin/openhands-mcp --help-local >.dg-workspace-openhands-mcp-help.txt
grep -F "diffusiongemma-local-agent" .dg-workspace-openhands-mcp-help.txt
grep -F "serena" .dg-workspace-openhands-mcp-help.txt
.dg-agent/bin/qwen-code --help-local >.dg-workspace-qwen-code-help.txt
grep -F "qwen-code.mcp.json" .dg-workspace-qwen-code-help.txt
grep -F "Qwen Code" .dg-workspace-qwen-code-help.txt
.dg-agent/bin/autogen --help-local >.dg-workspace-autogen-help.txt
grep -F "AutoGen AgentChat" .dg-workspace-autogen-help.txt
.dg-agent/bin/smolagents --help-local >.dg-workspace-smolagents-help.txt
grep -F "smolagents CodeAgent" .dg-workspace-smolagents-help.txt
.dg-agent/bin/langgraph --help-local >.dg-workspace-langgraph-help.txt
grep -F "LangGraph/LangChain" .dg-workspace-langgraph-help.txt
.dg-agent/bin/crewai --help-local >.dg-workspace-crewai-help.txt
grep -F "CrewAI" .dg-workspace-crewai-help.txt
.dg-agent/bin/open-interpreter --help-local >.dg-workspace-open-interpreter-help.txt
grep -F "Open Interpreter" .dg-workspace-open-interpreter-help.txt
.dg-agent/bin/llamaindex --help-local >.dg-workspace-llamaindex-help.txt
grep -F "LlamaIndex" .dg-workspace-llamaindex-help.txt
.dg-agent/bin/haystack --help-local >.dg-workspace-haystack-help.txt
grep -F "Haystack BM25 RAG" .dg-workspace-haystack-help.txt
.dg-agent/bin/swe-agent --help-local >.dg-workspace-swe-agent-help.txt
grep -F "SWE-agent" .dg-workspace-swe-agent-help.txt
.dg-agent/bin/mini-swe-agent --help-local >.dg-workspace-mini-swe-agent-help.txt
grep -F "mini-swe-agent" .dg-workspace-mini-swe-agent-help.txt
.dg-agent/bin/mini-swe-run --help >.dg-workspace-mini-swe-run-help.txt
grep -F -- "--output OUTPUT" .dg-workspace-mini-swe-run-help.txt
.dg-agent/bin/mini-swe-runs --help >.dg-workspace-mini-swe-runs-help.txt
grep -F "List recent mini-SWE runs" .dg-workspace-mini-swe-runs-help.txt
else
  echo "SKIP optional workspace wrappers; run their dedicated smoke suites after installation"
fi
.dg-agent/bin/mcp --list-tools >.dg-workspace-mcp-tools.json
"$PY_CMD" -m json.tool .dg-workspace-mcp-tools.json >/dev/null
grep -F '"dg_session"' .dg-workspace-mcp-tools.json
grep -F '"dg_repo_map"' .dg-workspace-mcp-tools.json
grep -F '"dg_ast_grep"' .dg-workspace-mcp-tools.json
grep -F '"dg_code_outline"' .dg-workspace-mcp-tools.json
.dg-agent/bin/mcp-http --help-local >.dg-workspace-mcp-http-help.txt
grep -F "streamable HTTP" .dg-workspace-mcp-http-help.txt
.dg-agent/bin/serena-mcp --help-local >.dg-workspace-serena-mcp-help.txt
grep -F "Run upstream Serena as an MCP server" .dg-workspace-serena-mcp-help.txt
.dg-agent/bin/mcp-client-config --help >.dg-workspace-mcp-client-config-help.txt
grep -F -- "--client" .dg-workspace-mcp-client-config-help.txt
grep -F -- "--with-repomix" .dg-workspace-mcp-client-config-help.txt
grep -F -- "--with-serena" .dg-workspace-mcp-client-config-help.txt
grep -F -- "--with-oss-stack" .dg-workspace-mcp-client-config-help.txt
grep -F -- "--print-template" .dg-workspace-mcp-client-config-help.txt
.dg-agent/bin/agent-rules --help >.dg-workspace-agent-rules-help.txt
grep -F -- "--target" .dg-workspace-agent-rules-help.txt
grep -F -- "--print-template" .dg-workspace-agent-rules-help.txt
.dg-agent/bin/agent-rules --target all --json >.dg-workspace-agent-rules-install.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-agent-rules-install.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
statuses = {Path(item["path"]).as_posix(): item["status"] for item in data["files"]}
assert any(path.endswith("AGENTS.md") and status == "written" for path, status in statuses.items()), statuses
assert any(path.endswith("CLAUDE.md") and status == "written" for path, status in statuses.items()), statuses
assert any(path.endswith(".github/copilot-instructions.md") and status == "written" for path, status in statuses.items()), statuses
assert any(path.endswith(".github/instructions/diffusiongemma.instructions.md") and status == "written" for path, status in statuses.items()), statuses
assert any(path.endswith(".cursor/rules/diffusiongemma-local-agent.mdc") and status == "written" for path, status in statuses.items()), statuses
PY
grep -F "BEGIN DG LOCAL AGENT INSTRUCTIONS" AGENTS.md
grep -F "dg_session" CLAUDE.md
grep -F "dg_task_note" .github/copilot-instructions.md
grep -F 'applyTo: "**"' .github/instructions/diffusiongemma.instructions.md
grep -F "alwaysApply: true" .cursor/rules/diffusiongemma-local-agent.mdc
.dg-agent/bin/agent-rules --target all --json >.dg-workspace-agent-rules-second.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-agent-rules-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert all(item["status"] == "unchanged" for item in data["files"]), data["files"]
PY
.dg-agent/bin/mcp-client-config --client cursor --json >.dg-workspace-cursor-mcp-install.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-cursor-mcp-install.json").read_text(encoding="utf-8"))
assert data["status"] == "written", data
assert data["client"] == "cursor", data
assert data["path"].replace("\\", "/").endswith(".cursor/mcp.json"), data
PY
"$PY_CMD" -m json.tool .cursor/mcp.json >/dev/null
grep -F '"mcpServers"' .cursor/mcp.json
grep -F '"diffusiongemma-local-agent"' .cursor/mcp.json
.dg-agent/bin/mcp-client-config --client cursor --json >.dg-workspace-cursor-mcp-second.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-cursor-mcp-second.json").read_text(encoding="utf-8"))
assert data["status"] == "unchanged", data
PY
.dg-agent/bin/mcp-client-config --client cursor --with-repomix --force --json >.dg-workspace-mcp-client-config-repomix.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

report = json.loads(Path(".dg-workspace-mcp-client-config-repomix.json").read_text(encoding="utf-8"))
assert report["status"] == "updated", report
assert report["servers"] == ["diffusiongemma-local-agent", "repomix"], report
config = json.loads(Path(".cursor/mcp.json").read_text(encoding="utf-8"))
servers = config["mcpServers"]
assert "diffusiongemma-local-agent" in servers, servers
assert servers["repomix"]["command"].replace("\\", "/").endswith("scripts/run_repomix_mcp.sh"), servers
assert servers["repomix"]["args"] == [], servers
PY
.dg-agent/bin/mcp-client-config --client cursor --with-oss-stack --force --json >.dg-workspace-mcp-client-config-oss-stack.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

report = json.loads(Path(".dg-workspace-mcp-client-config-oss-stack.json").read_text(encoding="utf-8"))
assert report["status"] == "updated", report
assert report["servers"] == ["diffusiongemma-local-agent", "repomix", "serena"], report
config = json.loads(Path(".cursor/mcp.json").read_text(encoding="utf-8"))
servers = config["mcpServers"]
assert servers["repomix"]["command"].replace("\\", "/").endswith("scripts/run_repomix_mcp.sh"), servers
assert servers["serena"]["command"].replace("\\", "/").endswith("scripts/run_serena_mcp.sh"), servers
assert servers["serena"]["args"] == [], servers
PY
mkdir -p .vscode
cat > .vscode/mcp.json <<'JSON'
{
  "servers": {
    "existing-server": {
      "type": "stdio",
      "command": "echo",
      "args": ["ok"]
    }
  }
}
JSON
.dg-agent/bin/mcp-client-config --client vscode --json >.dg-workspace-vscode-mcp-install.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-vscode-mcp-install.json").read_text(encoding="utf-8"))
assert data["status"] == "updated", data
cfg = json.loads(Path(".vscode/mcp.json").read_text(encoding="utf-8"))
assert "existing-server" in cfg["servers"], cfg
assert cfg["servers"]["diffusiongemma-local-agent"]["type"] == "stdio", cfg
PY

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >.dg-workspace-init-second.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-init-second.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert all(item["status"] == "unchanged" for item in data["files"]), data["files"]
PY

printf '\n# local edit\n' >> .dg-agent/README.md
if "$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >.dg-workspace-init-blocked.json; then
  echo "workspace-init should block changed files without --force" >&2
  exit 1
fi
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-init-blocked.json").read_text(encoding="utf-8"))
assert data["status"] == "blocked", data
assert any(item["status"] == "blocked" and item["path"].endswith("README.md") for item in data["files"]), data["files"]
PY

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --force --json >.dg-workspace-init-force.json
"$PY_CMD" - <<'PY'
import json
from pathlib import Path

data = json.loads(Path(".dg-workspace-init-force.json").read_text(encoding="utf-8"))
assert data["status"] == "success", data
assert any(item["status"] == "updated" and item["path"].endswith("README.md") for item in data["files"]), data["files"]
PY

echo "DG workspace init smoke passed."
