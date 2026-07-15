#!/usr/bin/env bash
set -euo pipefail

DG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNLOG_DIR="${DG_STACK_RUNLOG_DIR:-$DG_ROOT/runlogs}"
BACKEND_HEALTH="${DG_BACKEND_HEALTH:-http://127.0.0.1:4100/healthz}"
BACKEND_MODELS="${DG_BACKEND_MODELS:-http://127.0.0.1:4100/v1/models}"
PROXY_HEALTH="${DG_PROXY_HEALTH:-http://127.0.0.1:8090/healthz}"
DEFAULT_TIMEOUT=3

usage() {
  cat <<'EOF'
Watch and recover the local DiffusionGemma agent stack.

Usage:
  scripts/run_stack_watchdog.sh status [--json] [--timeout N]
  scripts/run_stack_watchdog.sh ensure [--json] [--restart] [--wait-timeout N] [--timeout N]
  scripts/run_stack_watchdog.sh down [backend|proxy|litellm|all...]
  scripts/run_stack_watchdog.sh watch [--interval N] [--restart]

Environment:
  DG_BACKEND_START_CMD       optional command used when backend 4100 is down
  DG_BACKEND_START_SCRIPT    optional script used when backend 4100 is down
  DG_AGENT_PYTHON            optional Python for proxy startup in WSL
EOF
}

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

http_body() {
  local url="$1"
  local timeout="$2"
  curl -fsS --max-time "$timeout" "$url" 2>/dev/null || true
}

http_ok() {
  local url="$1"
  local timeout="$2"
  curl -fsS --max-time "$timeout" "$url" >/dev/null 2>&1
}

service_ok() {
  local name="$1"
  local timeout="$2"
  case "$name" in
    backend) http_ok "$BACKEND_HEALTH" "$timeout" ;;
    proxy) http_ok "$PROXY_HEALTH" "$timeout" ;;
    litellm) http_ok "$BACKEND_MODELS" "$timeout" ;;
    *) return 2 ;;
  esac
}

status_json() {
  local timeout="$1"
  local backend_ok=false proxy_ok=false litellm_ok=false
  service_ok backend "$timeout" && backend_ok=true
  service_ok proxy "$timeout" && proxy_ok=true
  service_ok litellm "$timeout" && litellm_ok=true
  local backend_detail proxy_detail litellm_detail
  backend_detail="$(http_body "$BACKEND_HEALTH" "$timeout")"
  proxy_detail="$(http_body "$PROXY_HEALTH" "$timeout")"
  litellm_detail="$(http_body "$BACKEND_MODELS" "$timeout")"
  local ok=false
  if [[ "$backend_ok" == true && "$proxy_ok" == true && "$litellm_ok" == true ]]; then
    ok=true
  fi
  cat <<EOF
{
  "status": "watchdog",
  "ok": $ok,
  "services": {
    "backend": {"ok": $backend_ok, "url": "$BACKEND_HEALTH", "detail": "$(json_escape "$backend_detail")"},
    "proxy": {"ok": $proxy_ok, "url": "$PROXY_HEALTH", "detail": "$(json_escape "$proxy_detail")"},
    "litellm": {"ok": $litellm_ok, "url": "$BACKEND_MODELS", "detail": "$(json_escape "$litellm_detail")"}
  }
}
EOF
}

status_text() {
  local timeout="$1"
  echo "DG stack watchdog"
  for name in backend proxy litellm; do
    if service_ok "$name" "$timeout"; then
      case "$name" in
        backend) echo "backend: ok $BACKEND_HEALTH" ;;
        proxy) echo "proxy: ok $PROXY_HEALTH" ;;
        litellm) echo "litellm: ok $BACKEND_MODELS" ;;
      esac
    else
      case "$name" in
        backend) echo "backend: bad $BACKEND_HEALTH" ;;
        proxy) echo "proxy: bad $PROXY_HEALTH" ;;
        litellm) echo "litellm: bad $BACKEND_MODELS" ;;
      esac
    fi
  done
}

start_backend() {
  if service_ok backend "$DEFAULT_TIMEOUT"; then
    return 0
  fi
  mkdir -p "$RUNLOG_DIR"
  if [[ -n "${DG_BACKEND_START_CMD:-}" ]]; then
    nohup bash -lc "$DG_BACKEND_START_CMD" >"$RUNLOG_DIR/backend_watchdog.out.log" 2>"$RUNLOG_DIR/backend_watchdog.err.log" &
    echo $! >"$RUNLOG_DIR/backend_watchdog.pid"
    return 0
  fi
  if [[ -n "${DG_BACKEND_START_SCRIPT:-}" && -f "${DG_BACKEND_START_SCRIPT}" ]]; then
    nohup bash "${DG_BACKEND_START_SCRIPT}" >"$RUNLOG_DIR/backend_watchdog.out.log" 2>"$RUNLOG_DIR/backend_watchdog.err.log" &
    echo $! >"$RUNLOG_DIR/backend_watchdog.pid"
    return 0
  fi
  local ps_script="$DG_ROOT/scripts/start_agent_fast_service_windows.ps1"
  if [[ -f "$ps_script" && "$(uname -s 2>/dev/null || true)" != Linux* ]] && command -v powershell.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -aw "$ps_script")" >/dev/null
    return 0
  fi
  echo "backend is down and no DG_BACKEND_START_CMD/DG_BACKEND_START_SCRIPT/start_agent_fast_service_windows.ps1 is available" >&2
  return 1
}

start_proxy() {
  if service_ok proxy "$DEFAULT_TIMEOUT"; then
    return 0
  fi
  mkdir -p "$RUNLOG_DIR"
  if [[ "$(uname -s 2>/dev/null || true)" == Linux* ]]; then
    nohup "$DG_ROOT/scripts/run_agent_gateway_wsl.sh" >"$RUNLOG_DIR/agent_gateway_watchdog.out.log" 2>"$RUNLOG_DIR/agent_gateway_watchdog.err.log" &
    echo $! >"$RUNLOG_DIR/agent_gateway_watchdog.pid"
    return 0
  fi
  local ps_script="$DG_ROOT/scripts/start_agent_gateway.ps1"
  if [[ -f "$ps_script" && "$(uname -s 2>/dev/null || true)" != Linux* ]] && command -v powershell.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -aw "$ps_script")" >/dev/null
    return 0
  fi
  if command -v wsl.exe >/dev/null 2>&1 && command -v cygpath >/dev/null 2>&1; then
    local win_root wsl_root
    win_root="$(cygpath -am "$DG_ROOT")"
    wsl_root="$(wsl.exe wslpath -a "$win_root" | sed 's/\r$//')"
    export MSYS2_ARG_CONV_EXCL='*'
    export MSYS_NO_PATHCONV=1
    wsl.exe bash -lc "cd $(printf '%q' "$wsl_root") && nohup ./scripts/run_agent_gateway_wsl.sh >runlogs/agent_gateway_watchdog.out.log 2>runlogs/agent_gateway_watchdog.err.log &"
    return 0
  fi
  echo "proxy is down and no supported WSL/PowerShell launcher is available" >&2
  return 1
}

stop_service() {
  local service="$1"
  case "$service" in
    backend)
      if command -v wsl.exe >/dev/null 2>&1; then
        wsl.exe bash -lc "pkill -f llama-diffusion-gemma-visual-server || true"
      else
        pkill -f llama-diffusion-gemma-visual-server 2>/dev/null || true
      fi
      ;;
    proxy)
      if command -v wsl.exe >/dev/null 2>&1; then
        wsl.exe bash -lc "pkill -f aider_dg_proxy.py || true"
      else
        pkill -f aider_dg_proxy.py 2>/dev/null || true
      fi
      ;;
    litellm)
      ;;
    all)
      stop_service proxy
      stop_service backend
      ;;
    *)
      echo "unknown service: $service" >&2
      return 2
      ;;
  esac
}

wait_until_ready() {
  local wait_timeout="$1"
  local timeout="$2"
  local started
  started="$(date +%s)"
  while true; do
    if service_ok backend "$timeout" && service_ok proxy "$timeout" && service_ok litellm "$timeout"; then
      return 0
    fi
    if (( $(date +%s) - started >= ${wait_timeout%.*} )); then
      return 1
    fi
    sleep 1
  done
}

cmd="${1:-status}"
shift || true

json=0
restart=0
timeout="$DEFAULT_TIMEOUT"
wait_timeout=180
interval=30

case "$cmd" in
  -h|--help|--help-local|help)
    usage
    exit 0
    ;;
  status)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --json) json=1 ;;
        --timeout) timeout="$2"; shift ;;
        *) echo "unknown status argument: $1" >&2; exit 2 ;;
      esac
      shift
    done
    if [[ "$json" == 1 ]]; then
      status_json "$timeout"
    else
      status_text "$timeout"
    fi
    service_ok backend "$timeout" && service_ok proxy "$timeout" && service_ok litellm "$timeout"
    ;;
  ensure)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --json) json=1 ;;
        --restart) restart=1 ;;
        --timeout) timeout="$2"; shift ;;
        --wait-timeout) wait_timeout="$2"; shift ;;
        *) echo "unknown ensure argument: $1" >&2; exit 2 ;;
      esac
      shift
    done
    if [[ "$restart" == 1 ]]; then
      stop_service proxy
    fi
    start_backend || true
    start_proxy || true
    wait_until_ready "$wait_timeout" "$timeout" || true
    if [[ "$json" == 1 ]]; then
      status_json "$timeout"
    else
      status_text "$timeout"
    fi
    service_ok backend "$timeout" && service_ok proxy "$timeout" && service_ok litellm "$timeout"
    ;;
  down)
    if [[ $# -eq 0 ]]; then
      set -- all
    fi
    for service in "$@"; do
      stop_service "$service"
    done
    ;;
  watch)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --interval) interval="$2"; shift ;;
        --restart) restart=1 ;;
        *) echo "unknown watch argument: $1" >&2; exit 2 ;;
      esac
      shift
    done
    while true; do
      if ! service_ok backend "$timeout" || ! service_ok proxy "$timeout" || ! service_ok litellm "$timeout"; then
        if [[ "$restart" == 1 ]]; then
          "$0" ensure --wait-timeout 180 || true
        else
          status_text "$timeout"
        fi
      fi
      sleep "$interval"
    done
    ;;
  *)
    echo "unknown command: $cmd" >&2
    usage >&2
    exit 2
    ;;
esac
