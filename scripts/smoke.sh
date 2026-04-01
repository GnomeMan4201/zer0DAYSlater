#!/usr/bin/env bash
# Runtime smoke checks — separate from unit tests
set -e
source .venv/bin/activate
export PYTHONPATH=$(pwd)

run() {
    local f="$1"
    echo -n "  [smoke] $f ... "
    if timeout 3s python3 "$f" &>/dev/null; then
        echo "ok"
    else
        echo "FAILED"
    fi
}

echo ""
echo "  Smoke checks (import + init only)"
echo ""
run memory_loader.py
run process_doppelganger.py
run process_cloak.py
run proxy_fallback_check.py
run agent/sandbox_check.py
run agent/session_memory.py
run core/adaptive_channel_manager.py
echo ""
echo "  For full unit tests: python3 -m pytest tests/ -v"
echo ""
