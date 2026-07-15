#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/.bin/opencode"
if [[ "$(uname -s 2>/dev/null || true)" == Linux* && -x "$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode" ]]; then
  OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode"
fi
CONFIG="${OPENCODE_CONFIG:-$DG_ROOT/configs/opencode.dg.json}"

if [[ -x "$DG_ROOT/.tools/node-linux/bin/node" ]]; then
  export PATH="$DG_ROOT/.tools/node-linux/bin:$PATH"
fi

if [[ ! -x "$OPENCODE_BIN" ]]; then
  "$DG_ROOT/scripts/install_opencode_local.sh" >/tmp/dg-opencode-install.log
  if [[ "$(uname -s 2>/dev/null || true)" == Linux* && -x "$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode" ]]; then
    OPENCODE_BIN="$DG_ROOT/.tools/opencode/node_modules/opencode-linux-x64/bin/opencode"
  fi
fi
if [[ ! -s "$CONFIG" ]]; then
  echo "OpenCode config is missing: $CONFIG" >&2
  exit 1
fi

tmp_dir="$(mktemp -d /tmp/dg-opencode-config.XXXXXX)"
work_dir="$PWD"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

cp "$CONFIG" "$tmp_dir/opencode.json"
escaped_root="${DG_ROOT//\\/\\\\}"
escaped_root="${escaped_root//&/\\&}"
sed -i "s|/root/diffusiongemma-agent|$escaped_root|g" "$tmp_dir/opencode.json"
set +e
(
  cd "$work_dir"
  OPENCODE_CONFIG="$tmp_dir/opencode.json" "$OPENCODE_BIN" "$@"
)
rc=$?
set -e
exit "$rc"
