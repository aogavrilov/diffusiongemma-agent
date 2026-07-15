#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODE_DIR="$DG_ROOT/.tools/node"
NODE_LINUX_DIR="$DG_ROOT/.tools/node-linux"
NODE_WIN_DIR="$DG_ROOT/.tools/node-v22.17.1-win-x64"
QWEN_PREFIX="$DG_ROOT/.tools/qwen-code"
QWEN_BIN="$QWEN_PREFIX/node_modules/.bin/qwen"
PACKAGE="${DG_QWEN_CODE_PACKAGE:-@qwen-code/qwen-code@latest}"

node_path_entries=()
case "$(uname -s)" in
  Linux*)
    if [[ -x "$NODE_LINUX_DIR/bin/node" ]]; then
      node_path_entries+=("$NODE_LINUX_DIR/bin")
    fi
    ;;
esac
if [[ -x "$NODE_DIR/bin/node" ]]; then
  node_path_entries+=("$NODE_DIR/bin")
fi
if [[ -x "$NODE_WIN_DIR/node.exe" ]]; then
  node_path_entries+=("$NODE_WIN_DIR")
fi
if ((${#node_path_entries[@]})); then
  export PATH="$(IFS=:; echo "${node_path_entries[*]}"):$PATH"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js >=22 is required for Qwen Code. Install Node or provide .tools/node-linux/bin/node." >&2
  exit 1
fi

if [[ ! -x "$QWEN_BIN" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required to install Qwen Code." >&2
    exit 1
  fi
  npm install --prefix "$QWEN_PREFIX" "$PACKAGE"
fi

"$QWEN_BIN" --version
