#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_REPO="$(mktemp -d /tmp/dg-qwen-code.XXXXXX)"
PYTHON_CMD=()

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import json' >/dev/null 2>&1; then
    PYTHON_CMD=("$candidate")
    break
  fi
done
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]] && command -v py >/dev/null 2>&1 && py -3 -c 'import json' >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
fi
if [[ "${#PYTHON_CMD[@]}" -eq 0 ]]; then
  echo "Python with the stdlib json module is required for Qwen Code smoke." >&2
  exit 1
fi

cleanup() {
  echo "DG Qwen Code smoke repo: $TMP_REPO"
}
trap cleanup EXIT

cd "$TMP_REPO"
git init -q
git config user.email "local-smoke@example.invalid"
git config user.name "Local Smoke"
printf 'def add(a, b):\n    return a + b\n' > calc.py
git add calc.py
git commit -qm initial

test -x "$DG_ROOT/scripts/install_qwen_code_local.sh"
test -x "$DG_ROOT/scripts/run_qwen_code_local.sh"
bash -n "$DG_ROOT/scripts/install_qwen_code_local.sh" "$DG_ROOT/scripts/run_qwen_code_local.sh"
"${PYTHON_CMD[@]}" -m json.tool "$DG_ROOT/configs/client_profiles/qwen-code.mcp.json" >/dev/null

"$DG_ROOT/scripts/install_qwen_code_local.sh" >/tmp/dg-qwen-code-version.txt
grep -E '^[0-9]+\.[0-9]+\.[0-9]+' /tmp/dg-qwen-code-version.txt

"$DG_ROOT/scripts/run_qwen_code_local.sh" --help-local >/tmp/dg-qwen-code-help-local.txt
grep -F "Runs Qwen Code" /tmp/dg-qwen-code-help-local.txt
grep -F "qwen-code.mcp.json" /tmp/dg-qwen-code-help-local.txt

"$DG_ROOT/scripts/run_qwen_code_local.sh" --repo "$TMP_REPO" --dry-run -- --help >/tmp/dg-qwen-code-dry.txt
grep -F "qwen:" /tmp/dg-qwen-code-dry.txt
grep -F "openai_base_url: http://127.0.0.1:4100/v1" /tmp/dg-qwen-code-dry.txt
grep -F "openai_model: diffusiongemma-local" /tmp/dg-qwen-code-dry.txt
grep -F -- "--auth-type openai" /tmp/dg-qwen-code-dry.txt
grep -F -- "--mcp-config" /tmp/dg-qwen-code-dry.txt
grep -F "qwen-code.mcp.json" /tmp/dg-qwen-code-dry.txt
grep -F "diffusiongemma-local-agent" /tmp/dg-qwen-code-dry.txt
grep -F "repomix" /tmp/dg-qwen-code-dry.txt
grep -F "serena" /tmp/dg-qwen-code-dry.txt

"$DG_ROOT/scripts/dg_agent.sh" qwen-code -- --repo "$TMP_REPO" --dry-run -- --help >/tmp/dg-qwen-code-dg-dry.txt
grep -F -- "--auth-type openai" /tmp/dg-qwen-code-dg-dry.txt
grep -F "qwen-code.mcp.json" /tmp/dg-qwen-code-dg-dry.txt

"$DG_ROOT/scripts/dg_agent.sh" workspace-init --repo "$TMP_REPO" --json >/tmp/dg-qwen-code-workspace.json
test -s "$TMP_REPO/.dg-agent/qwen-code.mcp.json"
"${PYTHON_CMD[@]}" -m json.tool "$TMP_REPO/.dg-agent/qwen-code.mcp.json" >/dev/null
test -x "$TMP_REPO/.dg-agent/bin/qwen-code"
bash -n "$TMP_REPO/.dg-agent/bin/qwen-code"
"$TMP_REPO/.dg-agent/bin/qwen-code" --dry-run -- --help >/tmp/dg-qwen-code-workspace-dry.txt
grep -F ".dg-agent/qwen-code.mcp.json" /tmp/dg-qwen-code-workspace-dry.txt
grep -F -- "--allowed-mcp-server-names diffusiongemma-local-agent" /tmp/dg-qwen-code-workspace-dry.txt

node_path_entries=()
case "$(uname -s)" in
  Linux*)
    if [[ -x "$DG_ROOT/.tools/node-linux/bin/node" ]]; then
      node_path_entries+=("$DG_ROOT/.tools/node-linux/bin")
    fi
    ;;
esac
if [[ -x "$DG_ROOT/.tools/node/bin/node" ]]; then
  node_path_entries+=("$DG_ROOT/.tools/node/bin")
fi
if [[ -x "$DG_ROOT/.tools/node-v22.17.1-win-x64/node.exe" ]]; then
  node_path_entries+=("$DG_ROOT/.tools/node-v22.17.1-win-x64")
fi
if ((${#node_path_entries[@]})); then
  export PATH="$(IFS=:; echo "${node_path_entries[*]}"):$DG_ROOT/.tools/qwen-code/node_modules/.bin:$PATH"
else
  export PATH="$DG_ROOT/.tools/qwen-code/node_modules/.bin:$PATH"
fi
"$DG_ROOT/.tools/qwen-code/node_modules/.bin/qwen" --help >/tmp/dg-qwen-code-upstream-help.txt
grep -F "Qwen Code" /tmp/dg-qwen-code-upstream-help.txt
grep -F "qwen mcp" /tmp/dg-qwen-code-upstream-help.txt

echo "DG Qwen Code smoke passed."
