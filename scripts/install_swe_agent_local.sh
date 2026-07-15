#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$DG_ROOT/.tools/SWE-agent"
VENV="$DG_ROOT/.venv-swe-agent"
SWE_BIN="$VENV/bin/sweagent"

if [[ ! -d "$SRC_DIR/.git" ]]; then
  rm -rf "$SRC_DIR"
  git clone --depth 1 https://github.com/SWE-agent/SWE-agent.git "$SRC_DIR"
elif [[ "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  git -C "$SRC_DIR" pull --ff-only
fi

if [[ ! -x "$SWE_BIN" || "${DG_REFRESH_EXTERNAL_AGENT:-0}" == "1" ]]; then
  python3.12 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip wheel >/tmp/dg-swe-agent-pip-upgrade.log
  "$VENV/bin/python" -m pip install --editable "$SRC_DIR" >/tmp/dg-swe-agent-install.log
fi

"$SWE_BIN" --help >/tmp/dg-swe-agent-help.txt
echo "$SWE_BIN"
