#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_CMD="python3"
if [[ "${OS:-}" == "Windows_NT" ]] && command -v python >/dev/null 2>&1; then
  PY_CMD="python"
fi

pack_json="$("$DG_ROOT/scripts/dg_agent.sh" client-pack --json)"
JSON_OUT="$pack_json" "$PY_CMD" - <<'PY'
import json
import os

data = json.loads(os.environ["JSON_OUT"])
assert data["endpoints"]["litellm"]["base_url"] == "http://127.0.0.1:4100/v1", data
assert data["endpoints"]["litellm"]["model"] == "diffusiongemma-local", data
assert data["endpoints"]["aider_proxy"]["base_url"] == "http://127.0.0.1:8090/v1", data
profiles = data["profiles"]
def slash(value):
    return str(value).replace("\\", "/")

for key in ["local_agent", "openai_sdk", "openai_tool_loop", "agent_gateway", "codex_cli", "aider", "rag", "repomix", "repo_map", "ast_grep", "code_outline", "serena_mcp", "opencode", "opencode_agent", "opencode_mcp", "opencode_acp", "goose", "goose_mcp", "goose_acp", "goose_serve", "agent_bridge", "agent_hub", "client_smoke", "client_report", "agent_commands", "continue", "cline", "roo_code", "kilo_code", "ide_clients", "openhands", "openhands_mcp", "qwen_code", "autogen", "smolagents", "langgraph", "crewai", "open_interpreter", "llamaindex", "haystack", "swe_agent", "mini_swe_agent", "mcp", "mcp_http", "mcp_clients", "client_init", "agent_rules"]:
    assert key in profiles, key
assert profiles["local_agent"]["command"] == "scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode auto", profiles["local_agent"]
assert profiles["local_agent"]["read_route"] == "openai_tool_loop_read_only", profiles["local_agent"]
assert profiles["local_agent"]["edit_route"] == "session", profiles["local_agent"]
assert profiles["local_agent"]["artifact_commands"]["list_runs"] == "scripts/dg_agent.sh agent-runs list", profiles["local_agent"]
assert profiles["local_agent"]["artifact_commands"]["latest_transcript"].endswith("agent-runs artifact transcript --latest"), profiles["local_agent"]
assert profiles["openai_tool_loop"]["command"].startswith("scripts/dg_agent.sh tool-loop"), profiles["openai_tool_loop"]
assert profiles["openai_tool_loop"]["tool_runtime_url"] == "http://127.0.0.1:8090/v1/agent/tool", profiles["openai_tool_loop"]
assert "dg_context" in profiles["openai_tool_loop"]["tools"], profiles["openai_tool_loop"]
assert "dg_agent" in profiles["openai_tool_loop"]["tools"], profiles["openai_tool_loop"]
assert "dg_agent_run_artifact" in profiles["openai_tool_loop"]["tools"], profiles["openai_tool_loop"]
assert {"dg_repo_status", "dg_git_diff", "dg_list_files", "dg_read_file", "dg_search"} <= set(profiles["openai_tool_loop"]["tools"]), profiles["openai_tool_loop"]
assert {"dg_repo_pack", "dg_repo_map", "dg_ast_grep", "dg_code_outline"} <= set(profiles["openai_tool_loop"]["tools"]), profiles["openai_tool_loop"]
assert profiles["agent_gateway"]["base_url"] == "http://127.0.0.1:8090/v1", profiles["agent_gateway"]
assert profiles["agent_gateway"]["model"] == "diffusiongemma-26b-a4b-it-iq4xs-aider-local", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["model_card"] == "http://127.0.0.1:8090/v1/model_card", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["capabilities"] == "http://127.0.0.1:8090/v1/capabilities", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["session_api"] == "http://127.0.0.1:8090/v1/agent/session", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["tool_runtime"] == "http://127.0.0.1:8090/v1/agent/tool", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["context"] == "http://127.0.0.1:8090/v1/agent/context", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["rag_context"] == "http://127.0.0.1:8090/v1/agent/rag", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["sessions"] == "http://127.0.0.1:8090/v1/agent/sessions", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["latest_session"] == "http://127.0.0.1:8090/v1/agent/sessions/latest", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["latest_session_diff"] == "http://127.0.0.1:8090/v1/agent/sessions/latest/diff", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["agent_runs"] == "http://127.0.0.1:8090/v1/agent/runs", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["latest_agent_run"] == "http://127.0.0.1:8090/v1/agent/runs/latest", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["tool_manifest"] == "http://127.0.0.1:8090/v1/agent/tool_manifest", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["actions"] == "http://127.0.0.1:8090/v1/agent/actions", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["well_known_agent"] == "http://127.0.0.1:8090/.well-known/agent.json", profiles["agent_gateway"]
assert profiles["agent_gateway"]["discovery"]["openapi"] == "http://127.0.0.1:8090/openapi.json", profiles["agent_gateway"]
assert "tool_call_delegation" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_session_action_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_tool_runtime_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_repo_inspection_tools" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_session_artifact_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_agent_run_artifact_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_context_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "http_rag_context_api" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "openai_tool_schema_manifest" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "openai_dg_tool_schemas" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert "well_known_agent_manifest" in profiles["agent_gateway"]["supports"], profiles["agent_gateway"]
assert profiles["goose"]["env"]["GOOSE_PROVIDER"] == "openai", profiles["goose"]
assert profiles["goose_mcp"]["extension"] == "dg_agent", profiles["goose_mcp"]
assert profiles["goose_mcp"]["extensions"] == ["dg_agent", "serena"], profiles["goose_mcp"]
assert profiles["goose_mcp"]["config"].endswith("goose-mcp.dg.yaml"), profiles["goose_mcp"]
assert "dg_task_note" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_task_notes" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_search" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_read_file" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_rag_context" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_rag_answer" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_repo_pack" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_repo_map" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_ast_grep" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_code_outline" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_preflight" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_plan" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_task" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert "dg_session" in profiles["goose_mcp"]["tools"], profiles["goose_mcp"]
assert profiles["goose_acp"]["transport"] == "stdio", profiles["goose_acp"]
assert profiles["goose_acp"]["base_profile"] == "goose_mcp", profiles["goose_acp"]
assert profiles["goose_serve"]["transport"] == "http-websocket", profiles["goose_serve"]
assert profiles["goose_serve"]["default_url"] == "http://127.0.0.1:3294", profiles["goose_serve"]
assert profiles["agent_bridge"]["command"] == "scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp", profiles["agent_bridge"]
assert profiles["agent_bridge"]["default_server"] == "opencode-acp", profiles["agent_bridge"]
assert profiles["agent_bridge"]["servers"]["opencode-acp"]["default_url"] == "http://127.0.0.1:3295", profiles["agent_bridge"]
assert profiles["agent_bridge"]["servers"]["goose-serve"]["default_url"] == "http://127.0.0.1:3294", profiles["agent_bridge"]
assert profiles["agent_bridge"]["servers"]["goose-acp"]["transport"] == "stdio", profiles["agent_bridge"]
assert profiles["agent_bridge"]["workspace_launcher"] == ".dg-agent/bin/agent-bridge --server opencode-acp", profiles["agent_bridge"]
assert profiles["agent_hub"]["files"] == [".dg-agent/AGENT_HUB.md", ".dg-agent/agent-hub.json"], profiles["agent_hub"]
assert profiles["agent_hub"]["launcher"] == ".dg-agent/bin/hub", profiles["agent_hub"]
assert profiles["agent_hub"]["recommended_first_read"] == ".dg-agent/AGENT_HUB.md", profiles["agent_hub"]
assert profiles["codex_cli"]["installer"] == "scripts/dg_agent.sh codex-profile --repo /repo --target all", profiles["codex_cli"]
assert profiles["codex_cli"]["workspace_launcher"] == ".dg-agent/bin/codex-profile --target all", profiles["codex_cli"]
assert profiles["codex_cli"]["base_url"] == "http://127.0.0.1:8090/v1", profiles["codex_cli"]
assert profiles["codex_cli"]["model"] == "diffusiongemma-26b-a4b-it-iq4xs-aider-local", profiles["codex_cli"]
assert profiles["codex_cli"]["wire_api"] == "chat", profiles["codex_cli"]
assert ".dg-agent/CODEX.md" in profiles["codex_cli"]["workspace_files"], profiles["codex_cli"]
assert ".dg-agent/codex.config.toml" in profiles["codex_cli"]["workspace_files"], profiles["codex_cli"]
assert ".codex/config.toml" in profiles["codex_cli"]["project_files"], profiles["codex_cli"]
assert profiles["client_smoke"]["command"] == "scripts/dg_agent.sh client-smoke --repo /repo --client cursor", profiles["client_smoke"]
assert profiles["client_smoke"]["live_command"].endswith("--live"), profiles["client_smoke"]
assert "mcp_client_config" in profiles["client_smoke"]["checks"], profiles["client_smoke"]
assert profiles["client_smoke"]["workspace_launcher"] == ".dg-agent/bin/client-smoke --client cursor", profiles["client_smoke"]
assert profiles["client_report"]["command"] == "scripts/dg_agent.sh client-report --repo /repo --client cursor", profiles["client_report"]
assert profiles["client_report"]["live_command"].endswith("--live"), profiles["client_report"]
assert profiles["client_report"]["outputs"] == [".dg-agent/CLIENT_HANDOFF.md", ".dg-agent/client-handoff.json"], profiles["client_report"]
assert profiles["client_report"]["workspace_launcher"] == ".dg-agent/bin/client-report --client cursor", profiles["client_report"]
assert profiles["agent_commands"]["installer"] == "scripts/dg_agent.sh agent-commands --repo /repo --target all", profiles["agent_commands"]
assert ".dg-agent/COMMANDS.md" in profiles["agent_commands"]["workspace_files"], profiles["agent_commands"]
assert ".dg-agent/commands/dg-smoke.md" in profiles["agent_commands"]["workspace_files"], profiles["agent_commands"]
assert ".dg-agent/commands/dg-agent.md" in profiles["agent_commands"]["workspace_files"], profiles["agent_commands"]
assert ".claude/skills/dg-local-agent/SKILL.md" in profiles["agent_commands"]["project_files"], profiles["agent_commands"]
assert profiles["ide_clients"]["chat_endpoint"]["base_url"] == "http://127.0.0.1:4100/v1", profiles["ide_clients"]
assert profiles["ide_clients"]["safe_agent_endpoint"]["base_url"] == "http://127.0.0.1:8090/v1", profiles["ide_clients"]
assert profiles["ide_clients"]["safe_agent_endpoint"]["model"] == "diffusiongemma-26b-a4b-it-iq4xs-aider-local", profiles["ide_clients"]
assert ".dg-agent/IDE_CLIENTS.md" in profiles["ide_clients"]["workspace_files"], profiles["ide_clients"]
assert ".dg-agent/ide-client-snippets.json" in profiles["ide_clients"]["workspace_files"], profiles["ide_clients"]
assert ".dg-agent/kilo-code.config.json" in profiles["ide_clients"]["workspace_files"], profiles["ide_clients"]
assert slash(profiles["aider"]["config"]).endswith("configs/aider.dg-fast.conf.yml"), profiles["aider"]
assert slash(profiles["aider"]["workspace_config_template"]).endswith("configs/client_profiles/aider.dg-workspace.conf.yml"), profiles["aider"]
assert profiles["aider"]["workspace_config"] == ".dg-agent/aider.dg-fast.conf.yml", profiles["aider"]
assert slash(profiles["aider"]["model_settings"]).endswith("configs/aider.dg-model-settings.yml"), profiles["aider"]
assert slash(profiles["aider"]["model_metadata"]).endswith("configs/aider.dg-model-metadata.json"), profiles["aider"]
assert profiles["aider"]["env"]["DG_AIDER_EDIT_FORMAT"] == "whole", profiles["aider"]
assert profiles["rag"]["command"] == "scripts/dg_agent.sh rag --repo /repo --task \"...\" --print-context", profiles["rag"]
assert "dg_rag_context" in profiles["rag"]["mcp_tools"], profiles["rag"]
assert profiles["repomix"]["package"] == "repomix", profiles["repomix"]
assert profiles["repomix"]["native_mcp_command"] == "scripts/run_repomix_mcp.sh", profiles["repomix"]
assert "dg_repo_pack" in profiles["repomix"]["mcp_tools"], profiles["repomix"]
assert profiles["repo_map"]["package"] == "aider-chat", profiles["repo_map"]
assert profiles["repo_map"]["native_command"] == "scripts/run_aider_local.sh --repo /repo --show-repo-map", profiles["repo_map"]
assert "dg_repo_map" in profiles["repo_map"]["mcp_tools"], profiles["repo_map"]
assert profiles["ast_grep"]["package"] == "@ast-grep/cli", profiles["ast_grep"]
assert profiles["ast_grep"]["native_command"] == "scripts/run_ast_grep.sh", profiles["ast_grep"]
assert "dg_ast_grep" in profiles["ast_grep"]["mcp_tools"], profiles["ast_grep"]
assert profiles["code_outline"]["package"] == "@ast-grep/cli", profiles["code_outline"]
assert profiles["code_outline"]["native_command"] == "scripts/run_ast_grep.sh outline", profiles["code_outline"]
assert "dg_code_outline" in profiles["code_outline"]["mcp_tools"], profiles["code_outline"]
assert profiles["serena_mcp"]["package"] == "serena-agent", profiles["serena_mcp"]
assert profiles["serena_mcp"]["native_command"] == "scripts/run_serena_mcp.sh", profiles["serena_mcp"]
assert profiles["serena_mcp"]["server_name"] == "serena", profiles["serena_mcp"]
assert profiles["serena_mcp"]["transport"] == "stdio", profiles["serena_mcp"]
assert "find_symbol" in profiles["serena_mcp"]["tools"], profiles["serena_mcp"]
assert "get_diagnostics_for_file" in profiles["serena_mcp"]["tools"], profiles["serena_mcp"]
assert profiles["opencode_mcp"]["config"].endswith("opencode.dg-mcp.json"), profiles["opencode_mcp"]
assert profiles["opencode_agent"]["config"].endswith("opencode.dg-agent.json"), profiles["opencode_agent"]
assert profiles["opencode_agent"]["tools"] == ["bash"], profiles["opencode_agent"]
assert profiles["opencode_agent"]["timeout_env"].endswith("450000"), profiles["opencode_agent"]
assert profiles["opencode_mcp"]["mcp_servers"] == ["dg_agent", "repomix"], profiles["opencode_mcp"]
assert profiles["opencode_acp"]["base_profile"] == "opencode_mcp", profiles["opencode_acp"]
assert profiles["opencode_acp"]["transport"] == "acp-http", profiles["opencode_acp"]
assert profiles["opencode_acp"]["default_url"] == "http://127.0.0.1:3295", profiles["opencode_acp"]
assert profiles["openhands"]["model"] == "litellm_proxy/diffusiongemma-local", profiles["openhands"]
assert profiles["openhands"]["base_url"] == "http://127.0.0.1:4100", profiles["openhands"]
assert profiles["openhands_mcp"]["command"] == "scripts/dg_agent.sh openhands-mcp -- --repo /repo --reset", profiles["openhands_mcp"]
assert profiles["openhands_mcp"]["workspace_launcher"] == ".dg-agent/bin/openhands-mcp --reset", profiles["openhands_mcp"]
assert profiles["openhands_mcp"]["servers"] == ["diffusiongemma-local-agent", "repomix", "serena"], profiles["openhands_mcp"]
assert profiles["openhands_mcp"]["persistence_dir"] == ".dg-agent/openhands-persistence", profiles["openhands_mcp"]
assert profiles["qwen_code"]["command"] == "scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run", profiles["qwen_code"]
assert profiles["qwen_code"]["workspace_launcher"] == ".dg-agent/bin/qwen-code --dry-run", profiles["qwen_code"]
assert profiles["qwen_code"]["config"].endswith("qwen-code.mcp.json"), profiles["qwen_code"]
assert profiles["qwen_code"]["workspace_config"] == ".dg-agent/qwen-code.mcp.json", profiles["qwen_code"]
assert profiles["qwen_code"]["auth_type"] == "openai", profiles["qwen_code"]
assert profiles["qwen_code"]["mcp_servers"] == ["diffusiongemma-local-agent", "repomix", "serena"], profiles["qwen_code"]
assert profiles["autogen"]["command"] == "scripts/dg_agent.sh autogen -- --repo /repo --dry-run", profiles["autogen"]
assert profiles["autogen"]["workspace_launcher"] == ".dg-agent/bin/autogen --dry-run", profiles["autogen"]
assert profiles["autogen"]["config"].endswith("autogen.dg.json"), profiles["autogen"]
assert profiles["autogen"]["workspace_config"] == ".dg-agent/autogen.dg.json", profiles["autogen"]
assert profiles["autogen"]["model_client"].endswith("OpenAIChatCompletionClient"), profiles["autogen"]
assert profiles["autogen"]["model"] == "diffusiongemma-local", profiles["autogen"]
assert profiles["autogen"]["model_info"]["function_calling"] is False, profiles["autogen"]
assert profiles["smolagents"]["command"] == "scripts/dg_agent.sh smolagents -- --repo /repo --dry-run", profiles["smolagents"]
assert profiles["smolagents"]["workspace_launcher"] == ".dg-agent/bin/smolagents --dry-run", profiles["smolagents"]
assert profiles["smolagents"]["config"].endswith("smolagents.dg.json"), profiles["smolagents"]
assert profiles["smolagents"]["workspace_config"] == ".dg-agent/smolagents.dg.json", profiles["smolagents"]
assert profiles["smolagents"]["agent"].endswith("CodeAgent"), profiles["smolagents"]
assert profiles["smolagents"]["model_class"].endswith("OpenAIModel"), profiles["smolagents"]
assert profiles["smolagents"]["model"] == "diffusiongemma-local", profiles["smolagents"]
assert profiles["smolagents"]["max_steps"] == 2, profiles["smolagents"]
assert profiles["langgraph"]["command"] == "scripts/dg_agent.sh langgraph -- --repo /repo --dry-run", profiles["langgraph"]
assert profiles["langgraph"]["workspace_launcher"] == ".dg-agent/bin/langgraph --dry-run", profiles["langgraph"]
assert profiles["langgraph"]["config"].endswith("langgraph.dg.json"), profiles["langgraph"]
assert profiles["langgraph"]["workspace_config"] == ".dg-agent/langgraph.dg.json", profiles["langgraph"]
assert profiles["langgraph"]["model_class"].endswith("ChatOpenAI"), profiles["langgraph"]
assert profiles["langgraph"]["agent_factory"].endswith("create_agent"), profiles["langgraph"]
assert profiles["langgraph"]["fallback_agent_factory"].endswith("create_react_agent"), profiles["langgraph"]
assert profiles["langgraph"]["model"] == "diffusiongemma-local", profiles["langgraph"]
assert profiles["crewai"]["command"] == "scripts/dg_agent.sh crewai -- --repo /repo --dry-run", profiles["crewai"]
assert profiles["crewai"]["workspace_launcher"] == ".dg-agent/bin/crewai --dry-run", profiles["crewai"]
assert profiles["crewai"]["config"].endswith("crewai.dg.json"), profiles["crewai"]
assert profiles["crewai"]["workspace_config"] == ".dg-agent/crewai.dg.json", profiles["crewai"]
assert profiles["crewai"]["classes"]["crew"] == "crewai.Crew", profiles["crewai"]
assert profiles["crewai"]["classes"]["llm"] == "crewai.LLM", profiles["crewai"]
assert profiles["crewai"]["model"] == "openai/diffusiongemma-local", profiles["crewai"]
assert profiles["crewai"]["process"] == "sequential", profiles["crewai"]
assert profiles["open_interpreter"]["command"] == "scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run", profiles["open_interpreter"]
assert profiles["open_interpreter"]["workspace_launcher"] == ".dg-agent/bin/open-interpreter --dry-run", profiles["open_interpreter"]
assert profiles["open_interpreter"]["config"].endswith("open-interpreter.dg.json"), profiles["open_interpreter"]
assert profiles["open_interpreter"]["workspace_config"] == ".dg-agent/open-interpreter.dg.json", profiles["open_interpreter"]
assert profiles["open_interpreter"]["agent"] == "interpreter.interpreter", profiles["open_interpreter"]
assert profiles["open_interpreter"]["model"] == "openai/diffusiongemma-local", profiles["open_interpreter"]
assert profiles["open_interpreter"]["auto_run"] is False, profiles["open_interpreter"]
assert profiles["open_interpreter"]["safe_mode"] == "ask", profiles["open_interpreter"]
assert profiles["llamaindex"]["command"] == "scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run", profiles["llamaindex"]
assert profiles["llamaindex"]["workspace_launcher"] == ".dg-agent/bin/llamaindex --dry-run", profiles["llamaindex"]
assert profiles["llamaindex"]["config"].endswith("llamaindex.dg.json"), profiles["llamaindex"]
assert profiles["llamaindex"]["workspace_config"] == ".dg-agent/llamaindex.dg.json", profiles["llamaindex"]
assert profiles["llamaindex"]["llm_class"] == "llama_index.llms.openai_like.OpenAILike", profiles["llamaindex"]
assert profiles["llamaindex"]["agent_workflow_class"] == "llama_index.core.agent.workflow.AgentWorkflow", profiles["llamaindex"]
assert profiles["llamaindex"]["agent_class"] == "llama_index.core.agent.workflow.ReActAgent", profiles["llamaindex"]
assert profiles["llamaindex"]["function_agent_class"] == "llama_index.core.agent.workflow.FunctionAgent", profiles["llamaindex"]
assert profiles["llamaindex"]["model"] == "diffusiongemma-local", profiles["llamaindex"]
assert profiles["llamaindex"]["is_function_calling_model"] is False, profiles["llamaindex"]
assert profiles["llamaindex"]["tools"] == ["list_files", "read_file", "search_repo"], profiles["llamaindex"]
assert profiles["haystack"]["command"] == "scripts/dg_agent.sh haystack -- --repo /repo --dry-run", profiles["haystack"]
assert profiles["haystack"]["workspace_launcher"] == ".dg-agent/bin/haystack --dry-run", profiles["haystack"]
assert profiles["haystack"]["config"].endswith("haystack.dg.json"), profiles["haystack"]
assert profiles["haystack"]["workspace_config"] == ".dg-agent/haystack.dg.json", profiles["haystack"]
assert profiles["haystack"]["document_store"] == "haystack.document_stores.in_memory.InMemoryDocumentStore", profiles["haystack"]
assert profiles["haystack"]["retriever"] == "haystack.components.retrievers.in_memory.InMemoryBM25Retriever", profiles["haystack"]
assert profiles["haystack"]["generator"] == "haystack.components.generators.chat.OpenAIChatGenerator", profiles["haystack"]
assert profiles["haystack"]["model"] == "diffusiongemma-local", profiles["haystack"]
assert profiles["haystack"]["top_k"] == 4, profiles["haystack"]
assert profiles["haystack"]["max_tokens"] == 256, profiles["haystack"]
assert profiles["swe_agent"]["model"] == "openai/diffusiongemma-local", profiles["swe_agent"]
assert profiles["mini_swe_agent"]["cost_tracking"] == "ignore_errors", profiles["mini_swe_agent"]
assert profiles["mcp"]["transport"] == "stdio", profiles["mcp"]
assert profiles["mcp"]["sdk"] == "modelcontextprotocol/python-sdk", profiles["mcp"]
assert profiles["mcp"]["legacy_fallback"].endswith("mcp --legacy"), profiles["mcp"]
assert "dg_task_note" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_task_notes" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_repo_status" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_list_files" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_search" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_read_file" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_git_diff" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_rag_context" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_rag_answer" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_repo_pack" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_repo_map" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_ast_grep" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_code_outline" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_preflight" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_plan" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_task" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_session" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_sessions" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_agent_runs" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_agent_run_artifact" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_client_smoke" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg_client_report" in profiles["mcp"]["tools"], profiles["mcp"]
assert "dg://client-pack" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://notes" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://notes/latest" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://sessions/latest" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://agent-runs/latest" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://agent-runs/latest/transcript" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://capabilities/latest" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://client-handoff" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://client-handoff/markdown" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://agent-hub" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://agent-hub/markdown" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://command-kit" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://command-kit/markdown" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://ide-clients" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://ide-clients/markdown" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://codex-profile" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg://codex-profile/config" in profiles["mcp"]["resources"], profiles["mcp"]
assert "dg_agent_session" in profiles["mcp"]["prompts"], profiles["mcp"]
assert "dg_agent_continue_latest" in profiles["mcp"]["prompts"], profiles["mcp"]
assert profiles["mcp_http"]["base_profile"] == "mcp", profiles["mcp_http"]
assert profiles["mcp_http"]["transport"] == "streamable-http", profiles["mcp_http"]
assert profiles["mcp_http"]["url"] == "http://127.0.0.1:8765/mcp", profiles["mcp_http"]
assert "dg_session" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_repo_map" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_ast_grep" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_code_outline" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_agent_runs" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_agent_run_artifact" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert "dg_client_report" in profiles["mcp_http"]["tools"], profiles["mcp_http"]
assert profiles["mcp_clients"]["server_name"] == "diffusiongemma-local-agent", profiles["mcp_clients"]
assert slash(profiles["mcp_clients"]["server_command"]).endswith("scripts/run_mcp_server.sh"), profiles["mcp_clients"]
assert slash(profiles["mcp_clients"]["optional_servers"]["repomix"]["command"]).endswith("scripts/run_repomix_mcp.sh"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["optional_servers"]["repomix"]["args"] == [], profiles["mcp_clients"]
assert slash(profiles["mcp_clients"]["optional_servers"]["serena"]["command"]).endswith("scripts/run_serena_mcp.sh"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["optional_servers"]["serena"]["args"] == [], profiles["mcp_clients"]
assert slash(profiles["mcp_clients"]["snippets"]).endswith("mcp-client-snippets.json"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["installer"] == "scripts/dg_agent.sh mcp-client-config --repo /repo --client cursor", profiles["mcp_clients"]
assert profiles["mcp_clients"]["installer_with_repomix"].endswith("--with-repomix"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["installer_with_serena"].endswith("--with-serena"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["installer_with_all_optional"].endswith("--with-repomix --with-serena"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["installer_with_oss_stack"].endswith("--with-oss-stack"), profiles["mcp_clients"]
assert profiles["mcp_clients"]["one_shot_installer"] == "scripts/dg_agent.sh client-init --repo /repo --client cursor", profiles["mcp_clients"]
assert profiles["mcp_clients"]["recommended_bundle"]["servers"] == ["diffusiongemma-local-agent", "repomix", "serena"], profiles["mcp_clients"]
for key in ["claude_code", "claude_desktop", "cursor", "vscode"]:
    assert key in profiles["mcp_clients"]["configs"], key
assert profiles["mcp_clients"]["targets"]["cursor"] == ".cursor/mcp.json", profiles["mcp_clients"]
assert profiles["mcp_clients"]["targets"]["vscode"] == ".vscode/mcp.json", profiles["mcp_clients"]
assert profiles["client_init"]["command"] == "scripts/dg_agent.sh client-init --repo /repo --client cursor", profiles["client_init"]
assert profiles["client_init"]["default_bundle"] == "dg-repomix-serena", profiles["client_init"]
assert profiles["client_init"]["steps"] == ["workspace-init", "mcp-client-config --with-oss-stack", "agent-rules --target all", "agent-commands --target all"], profiles["client_init"]
assert profiles["client_init"]["clients"] == ["claude-code", "claude-desktop", "cursor", "vscode"], profiles["client_init"]
assert profiles["client_init"]["workspace_launcher"] == ".dg-agent/bin/client-init --client cursor", profiles["client_init"]
assert profiles["agent_rules"]["installer"] == "scripts/dg_agent.sh agent-rules --repo /repo --target all", profiles["agent_rules"]
assert profiles["agent_rules"]["targets"]["cursor"] == ".cursor/rules/diffusiongemma-local-agent.mdc", profiles["agent_rules"]
assert profiles["agent_rules"]["targets"]["vscode"] == ".github/instructions/diffusiongemma.instructions.md", profiles["agent_rules"]
assert profiles["agent_rules"]["templates"]["generic"].endswith("agent-instructions.md"), profiles["agent_rules"]
for key in ["aider", "aider_workspace", "aider_model_settings", "aider_model_metadata", "openhands", "openhands_env", "qwen_code_mcp", "autogen", "smolagents", "langgraph", "crewai", "open_interpreter", "llamaindex", "haystack", "swe_agent", "mini_swe_agent", "mcp", "mcp_client_snippets", "claude_code_mcp", "claude_desktop_mcp", "cursor_mcp", "vscode_mcp", "goose_mcp", "agent_instructions", "agents_rules", "claude_rules", "copilot_rules", "vscode_instructions", "cursor_rules", "codex_handoff", "codex_config_template", "codex_env", "agent_commands", "agent_command_kit", "claude_skill_template", "openai_compatible", "openai_env", "ide_clients", "ide_client_snippets", "kilo_code_config", "litellm_model_registry"]:
    assert key in data["repo_local_files"], key
PY

env_out="$("$DG_ROOT/scripts/dg_agent.sh" client-pack --env)"
grep_env_path() {
  grep -F "$1=" <<<"$env_out" | grep -F "$2"
}
grep -F "OPENAI_BASE_URL=http://127.0.0.1:4100/v1" <<<"$env_out"
grep -F "OPENAI_MODEL=diffusiongemma-local" <<<"$env_out"
grep -F "AIDER_OPENAI_API_BASE=http://127.0.0.1:8090/v1" <<<"$env_out"
grep -F "DG_AIDER_EDIT_FORMAT=whole" <<<"$env_out"
grep -F "GOOSE_PROVIDER=openai" <<<"$env_out"
grep -F "LLM_MODEL=litellm_proxy/diffusiongemma-local" <<<"$env_out"
grep -F "SWE_AGENT_MODEL=openai/diffusiongemma-local" <<<"$env_out"
grep_env_path "QWEN_CODE_MCP_CONFIG" "qwen-code.mcp.json"
grep -F "QWEN_CODE_COMMAND=scripts/dg_agent.sh qwen-code -- --repo /repo --dry-run" <<<"$env_out"
grep_env_path "AUTOGEN_CONFIG" "autogen.dg.json"
grep -F "AUTOGEN_COMMAND=scripts/dg_agent.sh autogen -- --repo /repo --dry-run" <<<"$env_out"
grep -F "AUTOGEN_MODEL=diffusiongemma-local" <<<"$env_out"
grep_env_path "SMOLAGENTS_CONFIG" "smolagents.dg.json"
grep -F "SMOLAGENTS_COMMAND=scripts/dg_agent.sh smolagents -- --repo /repo --dry-run" <<<"$env_out"
grep -F "SMOLAGENTS_MODEL=diffusiongemma-local" <<<"$env_out"
grep_env_path "LANGGRAPH_CONFIG" "langgraph.dg.json"
grep -F "LANGGRAPH_COMMAND=scripts/dg_agent.sh langgraph -- --repo /repo --dry-run" <<<"$env_out"
grep -F "LANGGRAPH_MODEL=diffusiongemma-local" <<<"$env_out"
grep_env_path "CREWAI_CONFIG" "crewai.dg.json"
grep -F "CREWAI_COMMAND=scripts/dg_agent.sh crewai -- --repo /repo --dry-run" <<<"$env_out"
grep -F "CREWAI_MODEL=openai/diffusiongemma-local" <<<"$env_out"
grep_env_path "OPEN_INTERPRETER_CONFIG" "open-interpreter.dg.json"
grep -F "OPEN_INTERPRETER_COMMAND=scripts/dg_agent.sh open-interpreter -- --repo /repo --dry-run" <<<"$env_out"
grep -F "OPEN_INTERPRETER_MODEL=openai/diffusiongemma-local" <<<"$env_out"
grep_env_path "LLAMAINDEX_CONFIG" "llamaindex.dg.json"
grep -F "LLAMAINDEX_COMMAND=scripts/dg_agent.sh llamaindex -- --repo /repo --dry-run" <<<"$env_out"
grep -F "LLAMAINDEX_MODEL=diffusiongemma-local" <<<"$env_out"
grep_env_path "HAYSTACK_CONFIG" "haystack.dg.json"
grep -F "HAYSTACK_COMMAND=scripts/dg_agent.sh haystack -- --repo /repo --dry-run" <<<"$env_out"
grep -F "HAYSTACK_MODEL=diffusiongemma-local" <<<"$env_out"
grep_env_path "MINI_SWE_AGENT_CONFIG" "mini-swe-agent.dg.yaml"
grep_env_path "DG_MCP_CONFIG" "mcp-server.json"
grep_env_path "DG_MCP_CLIENT_SNIPPETS" "mcp-client-snippets.json"
grep -F "DG_CLIENT_INIT_COMMAND=scripts/dg_agent.sh client-init --repo /repo --client cursor" <<<"$env_out"
grep -F "DG_LOCAL_AGENT_COMMAND=scripts/dg_agent.sh agent --repo /repo --task \"...\" --mode auto" <<<"$env_out"
grep -F "DG_AGENT_BRIDGE_COMMAND=scripts/dg_agent.sh agent-bridge --repo /repo --server opencode-acp" <<<"$env_out"
grep -F "DG_WORKSPACE_AGENT_HUB=.dg-agent/AGENT_HUB.md" <<<"$env_out"
grep -F "DG_CLIENT_SMOKE_COMMAND=scripts/dg_agent.sh client-smoke --repo /repo --client cursor" <<<"$env_out"
grep -F "DG_CLIENT_REPORT_COMMAND=scripts/dg_agent.sh client-report --repo /repo --client cursor" <<<"$env_out"
grep -F "DG_CODEX_PROFILE_COMMAND=scripts/dg_agent.sh codex-profile --repo /repo --target all" <<<"$env_out"
grep -F "DG_CODEX_CONFIG_TEMPLATE=.dg-agent/codex.config.toml" <<<"$env_out"
grep -F "DG_AGENT_COMMANDS_COMMAND=scripts/dg_agent.sh agent-commands --repo /repo --target all" <<<"$env_out"
grep -F "DG_IDE_CLIENTS_HANDOFF=.dg-agent/IDE_CLIENTS.md" <<<"$env_out"
grep -F "DG_IDE_CLIENT_SNIPPETS=.dg-agent/ide-client-snippets.json" <<<"$env_out"
grep -F "DG_SAFE_AGENT_BASE_URL=http://127.0.0.1:8090/v1" <<<"$env_out"
grep -F "DG_SAFE_AGENT_MODEL=diffusiongemma-26b-a4b-it-iq4xs-aider-local" <<<"$env_out"
grep_env_path "DG_AGENT_INSTRUCTIONS" "agent-instructions.md"
grep -F "DG_REPO_MAP_COMMAND=scripts/dg_agent.sh repo-map" <<<"$env_out"
grep -F "DG_AST_GREP_COMMAND=scripts/run_ast_grep.sh" <<<"$env_out"
grep -F "DG_CODE_OUTLINE_COMMAND=scripts/dg_agent.sh code-outline" <<<"$env_out"
grep -F "DG_SERENA_MCP_COMMAND=scripts/run_serena_mcp.sh" <<<"$env_out"
grep_env_path "GOOSE_MCP_CONFIG" "goose-mcp.dg.yaml"
test "$(grep -c '^OPENAI_API_KEY=' <<<"$env_out")" -eq 1

manifest_path="$("$DG_ROOT/scripts/dg_agent.sh" client-pack --write)"
manifest_path_slash="$(printf '%s' "$manifest_path" | tr '\\' '/')"
[[ "$manifest_path_slash" == */configs/client_profiles/agent-client-pack.json ]]
"$PY_CMD" -m json.tool "$manifest_path" >/dev/null
grep -F "diffusiongemma-local" "$manifest_path" >/dev/null
grep -F "opencode" "$manifest_path" >/dev/null
grep -F "opencode_acp" "$manifest_path" >/dev/null
grep -F "openhands_mcp" "$manifest_path" >/dev/null
grep -F "qwen_code" "$manifest_path" >/dev/null
grep -F "autogen" "$manifest_path" >/dev/null
grep -F "smolagents" "$manifest_path" >/dev/null
grep -F "langgraph" "$manifest_path" >/dev/null
grep -F "crewai" "$manifest_path" >/dev/null
grep -F "open_interpreter" "$manifest_path" >/dev/null
grep -F "llamaindex" "$manifest_path" >/dev/null
grep -F "haystack" "$manifest_path" >/dev/null
grep -F "mini_swe_agent" "$manifest_path" >/dev/null
grep -F '"rag"' "$manifest_path" >/dev/null
grep -F '"repomix"' "$manifest_path" >/dev/null
grep -F '"repo_map"' "$manifest_path" >/dev/null
grep -F '"ast_grep"' "$manifest_path" >/dev/null
grep -F '"code_outline"' "$manifest_path" >/dev/null
grep -F '"serena_mcp"' "$manifest_path" >/dev/null
grep -F "mcp" "$manifest_path" >/dev/null
grep -F "mcp_http" "$manifest_path" >/dev/null
grep -F "mcp_clients" "$manifest_path" >/dev/null
grep -F "client_init" "$manifest_path" >/dev/null
grep -F "codex_cli" "$manifest_path" >/dev/null
grep -F "codex-profile" "$manifest_path" >/dev/null
grep -F "agent_rules" "$manifest_path" >/dev/null
grep -F "dg_task_note" "$manifest_path" >/dev/null
grep -F "dg_search" "$manifest_path" >/dev/null
grep -F "dg_read_file" "$manifest_path" >/dev/null
grep -F "dg_rag_context" "$manifest_path" >/dev/null
grep -F "dg_rag_answer" "$manifest_path" >/dev/null
grep -F "dg_repo_pack" "$manifest_path" >/dev/null
grep -F "dg_repo_map" "$manifest_path" >/dev/null
grep -F "dg_ast_grep" "$manifest_path" >/dev/null
grep -F "dg_code_outline" "$manifest_path" >/dev/null
grep -F "find_symbol" "$manifest_path" >/dev/null
grep -F "dg_preflight" "$manifest_path" >/dev/null
grep -F "dg_plan" "$manifest_path" >/dev/null
grep -F "dg_task" "$manifest_path" >/dev/null
grep -F "dg_client_smoke" "$manifest_path" >/dev/null
grep -F "dg_client_report" "$manifest_path" >/dev/null
grep -F "dg://client-handoff" "$manifest_path" >/dev/null
grep -F "goose_mcp" "$manifest_path" >/dev/null
grep -F "agent_bridge" "$manifest_path" >/dev/null
grep -F "agent_hub" "$manifest_path" >/dev/null
grep -F "client_smoke" "$manifest_path" >/dev/null
grep -F "client_report" "$manifest_path" >/dev/null
grep -F "agent_commands" "$manifest_path" >/dev/null
grep -F '"extensions"' "$manifest_path" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/litellm-local-model-registry.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/claude-code.mcp.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/claude-desktop-mcp.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/cursor.mcp.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/vscode.mcp.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/autogen.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/smolagents.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/langgraph.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/crewai.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/client_profiles/haystack.dg.json" >/dev/null
"$PY_CMD" -m json.tool "$DG_ROOT/configs/aider.dg-model-metadata.json" >/dev/null
test -f "$DG_ROOT/configs/client_profiles/openhands.dg.toml"
test -f "$DG_ROOT/configs/aider.dg-fast.conf.yml"
test -f "$DG_ROOT/configs/client_profiles/aider.dg-workspace.conf.yml"
test -f "$DG_ROOT/configs/aider.dg-model-settings.yml"
test -f "$DG_ROOT/configs/aider.dg-model-metadata.json"
test -f "$DG_ROOT/configs/client_profiles/openhands.env"
test -f "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json"
test -f "$DG_ROOT/configs/client_profiles/autogen.dg.json"
test -f "$DG_ROOT/configs/client_profiles/smolagents.dg.json"
test -f "$DG_ROOT/configs/client_profiles/langgraph.dg.json"
test -f "$DG_ROOT/configs/client_profiles/crewai.dg.json"
test -f "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json"
test -f "$DG_ROOT/configs/client_profiles/llamaindex.dg.json"
test -f "$DG_ROOT/configs/client_profiles/haystack.dg.json"
test -f "$DG_ROOT/configs/client_profiles/swe-agent.dg.yaml"
test -f "$DG_ROOT/configs/client_profiles/mini-swe-agent.dg.yaml"
test -f "$DG_ROOT/configs/client_profiles/mcp-server.json"
test -f "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json"
test -f "$DG_ROOT/configs/client_profiles/claude-code.mcp.json"
test -f "$DG_ROOT/configs/client_profiles/claude-desktop-mcp.json"
test -f "$DG_ROOT/configs/client_profiles/cursor.mcp.json"
test -f "$DG_ROOT/configs/client_profiles/vscode.mcp.json"
test -f "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml"
grep -F "cmd: /root/diffusiongemma-agent/scripts/run_serena_mcp.sh" "$DG_ROOT/configs/client_profiles/goose-mcp.dg.yaml" >/dev/null
test -f "$DG_ROOT/configs/client_profiles/agent-instructions.md"
test -f "$DG_ROOT/configs/client_profiles/AGENTS.dg.md"
test -f "$DG_ROOT/configs/client_profiles/CLAUDE.dg.md"
test -f "$DG_ROOT/configs/client_profiles/copilot-instructions.dg.md"
test -f "$DG_ROOT/configs/client_profiles/diffusiongemma.instructions.md"
test -f "$DG_ROOT/configs/client_profiles/cursor-rules.dg.mdc"
grep -F '"mcpServers"' "$DG_ROOT/configs/client_profiles/cursor.mcp.json" >/dev/null
grep -F '"servers"' "$DG_ROOT/configs/client_profiles/vscode.mcp.json" >/dev/null
grep -F '/root/diffusiongemma-agent/scripts/run_mcp_server.sh' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '"repomix"' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '/root/diffusiongemma-agent/scripts/run_repomix_mcp.sh' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '"serena"' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '/root/diffusiongemma-agent/scripts/run_serena_mcp.sh' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '"recommended_bundle"' "$DG_ROOT/configs/client_profiles/mcp-client-snippets.json" >/dev/null
grep -F '"diffusiongemma-local-agent"' "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json" >/dev/null
grep -F '"repomix"' "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json" >/dev/null
grep -F '"serena"' "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json" >/dev/null
grep -F 'OpenAIChatCompletionClient' "$DG_ROOT/configs/client_profiles/autogen.dg.json" >/dev/null
grep -F '"diffusiongemma-local"' "$DG_ROOT/configs/client_profiles/autogen.dg.json" >/dev/null
grep -F 'CodeAgent' "$DG_ROOT/configs/client_profiles/smolagents.dg.json" >/dev/null
grep -F '"diffusiongemma-local"' "$DG_ROOT/configs/client_profiles/smolagents.dg.json" >/dev/null
grep -F 'ChatOpenAI' "$DG_ROOT/configs/client_profiles/langgraph.dg.json" >/dev/null
grep -F '"diffusiongemma-local"' "$DG_ROOT/configs/client_profiles/langgraph.dg.json" >/dev/null
grep -F '"crewai.Crew"' "$DG_ROOT/configs/client_profiles/crewai.dg.json" >/dev/null
grep -F '"openai/diffusiongemma-local"' "$DG_ROOT/configs/client_profiles/crewai.dg.json" >/dev/null
grep -F '"interpreter.interpreter"' "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json" >/dev/null
grep -F '"auto_run": false' "$DG_ROOT/configs/client_profiles/open-interpreter.dg.json" >/dev/null
grep -F '"llama_index.llms.openai_like.OpenAILike"' "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
grep -F '"llama_index.core.agent.workflow.AgentWorkflow"' "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
grep -F '"llama_index.core.agent.workflow.ReActAgent"' "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
grep -F '"is_function_calling_model": false' "$DG_ROOT/configs/client_profiles/llamaindex.dg.json" >/dev/null
grep -F '"haystack.components.retrievers.in_memory.InMemoryBM25Retriever"' "$DG_ROOT/configs/client_profiles/haystack.dg.json" >/dev/null
grep -F '"haystack.components.generators.chat.OpenAIChatGenerator"' "$DG_ROOT/configs/client_profiles/haystack.dg.json" >/dev/null
grep -F "dg_task_note" "$DG_ROOT/configs/client_profiles/agent-instructions.md" >/dev/null
grep -F "alwaysApply: true" "$DG_ROOT/configs/client_profiles/cursor-rules.dg.mdc" >/dev/null
grep -F "openai-api-base: http://127.0.0.1:8090/v1" "$DG_ROOT/configs/client_profiles/aider.dg-workspace.conf.yml" >/dev/null
grep -F "model-settings-file: .dg-agent/aider.dg-model-settings.yml" "$DG_ROOT/configs/client_profiles/aider.dg-workspace.conf.yml" >/dev/null

"$DG_ROOT/scripts/dg_agent.sh" client-pack | grep -F "DiffusionGemma local agent client pack"

echo "DG agent client pack smoke passed."
