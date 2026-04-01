#!/usr/bin/env bash
PASS=0; FAIL=0

check() {
    local label="$1"; local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo "[✓] $label"; ((PASS++))
    else
        echo "[✗] $label"; ((FAIL++))
    fi
}

echo ""
echo "  zer0DAYSlater — doctor"
echo ""

check "Python 3.10+"        'python3 -c "import sys; assert sys.version_info >= (3,10)"'
check "venv exists"         'test -d .venv'
check "venv active OR pip reachable" 'python3 -m pip show requests &>/dev/null'
check "requests installed"  'python3 -c "import requests"'
check "pynacl installed"    'python3 -c "import nacl"'
check "websockets installed" 'python3 -c "import websockets"'
check "fastapi installed"   'python3 -c "import fastapi"'
check "ollama installed"    'python3 -c "import ollama"'
check "ollama CLI present"  'command -v ollama'
check "ollama running"      'ollama list'
check ".env.example exists" 'test -f .env.example'
check "ZDS_AUTH_TOKEN set"  'test -n "$ZDS_AUTH_TOKEN"'
check "ZDS_C2_WS_URL set"   'test -n "$ZDS_C2_WS_URL"'
check "ZDS_HTTPS_ENDPOINT set" 'test -n "$ZDS_HTTPS_ENDPOINT"'
check "ZDS_LLM_MODEL set"   'test -n "$ZDS_LLM_MODEL"'
check "config.py loads"     'python3 -c "import config"'
check "session_drift_monitor loads" 'python3 -c "import session_drift_monitor"'
check "entropy_capsule loads" 'python3 -c "import entropy_capsule"'
check "payload_mutator loads" 'python3 -c "import payload_mutator"'
check "demo.sh executable"  'test -x demo.sh'

echo ""
echo "  $PASS passed / $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    echo "  Run './demo.sh' only after all checks pass."
    exit 1
else
    echo "  All checks passed. Run './demo.sh' to verify or './omega_campaign.sh' for live."
fi
echo ""
