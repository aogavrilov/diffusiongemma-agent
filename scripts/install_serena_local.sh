#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v cygpath >/dev/null 2>&1; then
  DG_ROOT="$(cygpath -au "$DG_ROOT")"
fi
UV_BIN="$DG_ROOT/.tools/uv/bin/uv"
UV_EXE="$DG_ROOT/.tools/uv/bin/uv.exe"
TOOL_DIR="$DG_ROOT/.tools/uv-tools"
BIN_DIR="$TOOL_DIR/bin"
VENV_DIR="${DG_SERENA_VENV:-$DG_ROOT/.venv-serena}"
PYTHON_VERSION="${DG_SERENA_PYTHON:-3.13}"
PACKAGE="${DG_SERENA_PACKAGE:-serena-agent}"

find_venv_python() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    printf '%s\n' "$VENV_DIR/bin/python"
    return 0
  fi
  if [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    printf '%s\n' "$VENV_DIR/Scripts/python.exe"
    return 0
  fi
  return 1
}

cleanup_blocked_native_accelerators() {
  local py="$1"
  "$py" - <<'PY'
from pathlib import Path
import sys

for entry in sys.path:
    pkg = Path(entry) / "charset_normalizer"
    if not pkg.is_dir():
        continue
    for stem in ("cd", "md"):
        if not (pkg / f"{stem}.py").exists():
            continue
        for pyd in pkg.glob(f"{stem}*.pyd"):
            target = pyd.with_name(pyd.name + ".blocked")
            if not target.exists():
                pyd.rename(target)
PY
}

install_with_pip_venv() {
  if ! find_venv_python >/dev/null; then
    if command -v python >/dev/null 2>&1; then
      python -m venv "$VENV_DIR"
    elif command -v python3 >/dev/null 2>&1; then
      python3 -m venv "$VENV_DIR"
    else
      echo "Python is required to create $VENV_DIR" >&2
      return 2
    fi
  fi

  local py
  py="$(find_venv_python)"
  "$py" -m pip install --upgrade pip
  "$py" -m pip install "$PACKAGE"
  cleanup_blocked_native_accelerators "$py"
  echo "$py $DG_ROOT/scripts/serena_cli.py"
}

install_with_uv_tool() {
  if [[ ! -x "$UV_BIN" && ! -x "$UV_EXE" ]]; then
    "$DG_ROOT/scripts/install_uv_local.sh" >/tmp/dg-serena-uv-install.log 2>&1 || return 1
  fi

  mkdir -p "$TOOL_DIR" "$BIN_DIR"

  local uv_cmd=""
  if [[ -x "$UV_BIN" ]]; then
    uv_cmd="$UV_BIN"
  elif [[ -x "$UV_EXE" ]]; then
    uv_cmd="$UV_EXE"
  fi
  [[ -n "$uv_cmd" ]] || return 1
  "$uv_cmd" --version >/dev/null 2>&1 || return 1

  UV_TOOL_DIR="$TOOL_DIR" \
  UV_TOOL_BIN_DIR="$BIN_DIR" \
  "$uv_cmd" tool install --python "$PYTHON_VERSION" "$PACKAGE" --force || return 1

  if [[ -x "$BIN_DIR/serena" ]]; then
    "$BIN_DIR/serena" --version >/dev/null 2>&1 || return 1
    echo "$BIN_DIR/serena"
    return 0
  fi
  if [[ -x "$BIN_DIR/serena.exe" ]]; then
    "$BIN_DIR/serena.exe" --version >/dev/null 2>&1 || return 1
    echo "$BIN_DIR/serena.exe"
    return 0
  fi
  return 1
}

if [[ "${DG_SERENA_FORCE_PIP:-0}" != "1" ]]; then
  if install_with_uv_tool; then
    exit 0
  fi
fi

install_with_pip_venv
