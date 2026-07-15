#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AIDER_PYTHON="${DG_AIDER_PYTHON:-/root/diffusiongemma-agent/.venv-aider/bin/python}"
CONFIG="$DG_ROOT/configs/aider.dg-fast.conf.yml"
UNAME="$(uname -s 2>/dev/null || true)"

win_to_wsl_path() {
  local value="$1"
  value="${value//\\//}"
  if [[ "$value" =~ ^([A-Za-z]):/(.*)$ ]]; then
    local drive
    drive="$(printf '%s' "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')"
    printf '/mnt/%s/%s' "$drive" "${BASH_REMATCH[2]}"
  else
    printf '%s' "$value"
  fi
}

if [[ "$UNAME" != Linux* ]] && command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
  export MSYS2_ARG_CONV_EXCL='*'
  export MSYS_NO_PATHCONV=1
  win_root="$(cygpath -am "$DG_ROOT")"
  wsl_root="$(win_to_wsl_path "$win_root")"
  mapped_args=()
  path_next=0
  for arg in "$@"; do
    if [[ "$path_next" == 1 ]]; then
      if [[ "$arg" == /mnt/* ]]; then
        mapped_args+=("$arg")
      else
        win_arg="$(cygpath -am "$arg" 2>/dev/null || printf '%s' "$arg")"
        mapped_args+=("$(win_to_wsl_path "$win_arg")")
      fi
      path_next=0
      continue
    fi
    mapped_args+=("$arg")
    if [[ "$arg" == "--repo" ]]; then
      path_next=1
    fi
  done
  quoted_args=()
  for arg in "${mapped_args[@]}"; do
    [[ -n "$arg" ]] && quoted_args+=("$(printf '%q' "$arg")")
  done
  exec wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && exec ./scripts/run_aider_local.sh ${quoted_args[*]}"
fi

if [[ ! -x "$AIDER_PYTHON" ]]; then
  echo "Aider Python runtime is missing: $AIDER_PYTHON" >&2
  echo "Install the WSL Python 3.12 Aider runtime before using this runner." >&2
  exit 2
fi
if [[ ! -f "$CONFIG" ]]; then
  echo "Aider config is missing: $CONFIG" >&2
  exit 2
fi

repo=""
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || { echo "--repo requires a path" >&2; exit 2; }
      repo="$2"
      shift 2
      ;;
    --repo=*)
      repo="${1#--repo=}"
      shift
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

repo="${repo:-$PWD}"
if [[ ! -d "$repo" ]]; then
  echo "Aider repository does not exist: $repo" >&2
  exit 2
fi

cd "$repo"
state_dir="$(mktemp -d "${TMPDIR:-/tmp}/dg-aider.XXXXXX")"
cleanup() {
  rm -rf -- "$state_dir"
}
trap cleanup EXIT

"$AIDER_PYTHON" -m aider \
  --config "$CONFIG" \
  --model-metadata-file "$DG_ROOT/configs/aider.dg-model-metadata.json" \
  --model-settings-file "$DG_ROOT/configs/aider.dg-model-settings.yml" \
  --input-history-file "$state_dir/input.history" \
  --chat-history-file "$state_dir/chat.history.md" \
  --llm-history-file "$state_dir/llm.history.md" \
  "${args[@]}"
exit $?
