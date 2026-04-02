#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
set -a; source .env; set +a

echo "[*] Starting C2 listeners..."

uvicorn tools.c2_server:app \
    --host 0.0.0.0 \
    --port 8080 \
    --ssl-keyfile key.pem \
    --ssl-certfile cert.pem \
    --log-level warning &
HTTPS_PID=$!

python3 tools/c2_ws_server.py &
WS_PID=$!

echo "[✓] HTTPS C2 listening on :8080 (pid $HTTPS_PID)"
echo "[✓] WebSocket C2 listening on :8765 (pid $WS_PID)"
echo "[*] Press Ctrl+C to stop all listeners"

trap "kill $HTTPS_PID $WS_PID 2>/dev/null; echo '[*] C2 listeners stopped'" EXIT
wait
