#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_BIN="$DG_ROOT/.tools/node/bin"
if [[ -d "$NODE_BIN" ]]; then
  export PATH="$NODE_BIN:$PATH"
fi

if [[ "${1:-}" == "--help-local" ]]; then
  cat <<'TXT'
Runs upstream ast-grep (sg) through the local Node toolchain.

Examples:
  scripts/run_ast_grep.sh --version
  scripts/run_ast_grep.sh run -l python -p 'return $X' --json=compact /path/to/repo
  scripts/dg_agent.sh ast-grep --repo /path/to/repo --lang python --pattern 'return $X' --json
TXT
  exit 0
fi

exec npx --yes -p @ast-grep/cli sg "$@"
