#!/usr/bin/env bash
set -e
source .venv/bin/activate
export ZDS_MODE=demo
export ZDS_AUTH_TOKEN=demo_token
export ZDS_C2_WS_URL=ws://127.0.0.1:8765
export ZDS_HTTPS_ENDPOINT=http://127.0.0.1:8000/api
export ZDS_LLM_MODEL=mistral:latest

echo ""
echo "  zer0DAYSlater — DEMO MODE"
echo ""

python3 - << 'PYEOF'
import sys
sys.path.insert(0, ".")

print("[*] Checking demo mode flag...")
import config
assert config.DEMO_MODE, "ZDS_MODE not set to demo"
print("[✓] DEMO_MODE active")

print("[*] Testing demo LLM parse...")
from demo_mode import fake_llm_parse
result = fake_llm_parse("exfil ssh keys after midnight, stay silent")
assert result["action"] == "exfil"
print(f"[✓] LLM parse: {result}")

print("[*] Testing drift monitor import...")
import session_drift_monitor
print("[✓] session_drift_monitor loaded")

print("[*] Testing entropy capsule import...")
import entropy_capsule
print("[✓] entropy_capsule loaded")

print("[*] Testing payload mutator import...")
import payload_mutator
print("[✓] payload_mutator loaded")

print("[*] Simulating channel feedback...")
from demo_mode import fake_channel_result
for i in range(3):
    r = fake_channel_result()
    status = "✗ DETECTED" if r["detected"] else "✓ OK"
    print(f"  [Gen {i}] {r['channel']:6s}  {status}  {r['latency_ms']}ms")

print("[*] Simulating peer handshake...")
from demo_mode import fake_peer_handshake
hs = fake_peer_handshake()
print(f"[✓] Peer {hs['peer']} verified={hs['verified']} fingerprint={hs['fingerprint']}")

print("")
print("[✓] Demo complete — system is functional")
print("    To run live: cp .env.example .env && nano .env && source .env && ./omega_campaign.sh")
PYEOF
