#!/usr/bin/env bash
# Modified 2026-10-29 for the independent Simulation Lab edition; see NOTICE and MODIFICATIONS.md.
set -euo pipefail
cd "$(dirname "$0")/.."
repo_dir="$PWD"
mkdir -p .run backend/logs
case "${1:-status}" in
  setup)
    uv_exe="${UV_BIN:-$HOME/.local/bin/uv}"
    command -v "$uv_exe" >/dev/null || { echo 'Install uv from https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
    if [[ ! -f .env ]]; then
      python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
p.write_text(Path('.env.simlab.example').read_text().replace('replace-with-local-password', secrets.token_urlsafe(24)))
p.chmod(0o600)
PY
    fi
    "$uv_exe" venv --python 3.11 .venv --allow-existing
    if [[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 ]]; then
      "$uv_exe" pip install --python .venv/bin/python 'torch==2.15.0+cpu' --index-url https://download.pytorch.org/whl/cpu
      "$uv_exe" pip install --python .venv/bin/python -r backend/requirements.simlab.lock
    else
      "$uv_exe" pip install --python .venv/bin/python -r backend/requirements.txt pytest pytest-asyncio
    fi
    .venv/bin/python -m playwright install chromium
    npm --prefix frontend ci
    docker compose -f compose.simlab.yml up -d
    docker compose -f compose.simlab.yml exec -T ollama ollama pull nomic-embed-text
    echo 'Setup complete. Run: ./scripts/simlab-local.sh start'
    ;;
  start)
    [[ -x .venv/bin/python && -d frontend/node_modules ]] || { echo 'Run ./scripts/simlab-local.sh setup first'; exit 1; }
    docker compose -f compose.simlab.yml up -d
    for service in backend frontend; do
      pid_file=".run/$service.pid"
      if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo "$service is already running"
        continue
      fi
      if [[ "$service" == backend ]]; then
        port=5001
      else
        port=3000
      fi
      .venv/bin/python - "$port" <<'PY'
import socket, sys
with socket.socket() as s:
    try:
        s.bind(('127.0.0.1', int(sys.argv[1])))
    except OSError:
        raise SystemExit('Port ' + sys.argv[1] + ' is in use. No existing process was changed.')
PY
      if [[ "$service" == backend ]]; then
        nohup setsid .venv/bin/python backend/run.py > backend/logs/simlab-backend.log 2>&1 < /dev/null &
      else
        nohup setsid node frontend/node_modules/vite/bin/vite.js frontend --config frontend/vite.config.js --host 127.0.0.1 > backend/logs/simlab-frontend.log 2>&1 < /dev/null &
      fi
      echo "$!" > "$pid_file"
    done
    .venv/bin/python - <<'PYWAIT'
import time, urllib.request
for url in ['http://127.0.0.1:5001/health', 'http://127.0.0.1:3000/simlab']:
    for attempt in range(40):
        try:
            urllib.request.urlopen(url, timeout=1).close()
            break
        except Exception:
            time.sleep(.5)
    else:
        raise SystemExit('Service did not start: ' + url + '. Check backend/logs.')
PYWAIT
    echo 'SimLab Lab: http://localhost:3000/simlab'
    echo 'Backend: http://localhost:5001/health'
    echo 'Logs: backend/logs/simlab-backend.log and simlab-frontend.log'
    ;;
  stop)
    for service in frontend backend; do
      pid_file=".run/$service.pid"
      if [[ -f "$pid_file" ]]; then
        service_pid="$(cat "$pid_file")"
        if [[ -d "/proc/$service_pid" && "$(readlink "/proc/$service_pid/cwd")" == "$repo_dir" ]]; then
          kill -- "-$service_pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
      fi
    done
    docker compose -f compose.simlab.yml stop
    ;;
  status)
    docker compose -f compose.simlab.yml ps
    for service in backend frontend; do
      if [[ -f ".run/$service.pid" ]] && kill -0 "$(cat ".run/$service.pid")" 2>/dev/null; then
        echo "$service running (PID $(cat ".run/$service.pid"))"
      else
        echo "$service stopped"
      fi
    done
    ;;
  *) echo 'Usage: ./scripts/simlab-local.sh {setup|start|stop|status}'; exit 1 ;;
esac
