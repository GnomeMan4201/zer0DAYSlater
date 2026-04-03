#!/usr/bin/env bash
source .venv/bin/activate
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  zer0DAYSlater — Full Pipeline Demo"
echo "  badBANANA research // GnomeMan4201"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "▶ LAYER 1 — mTLS Mesh (cryptographic peer authentication)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 mtls_mesh.py
echo ""

echo "▶ LAYER 2 — Payload Mutator (fitness-scored adaptive mutation)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 payload_mutator.py
echo ""

echo "▶ LAYER 3 — Entropy Capsule Engine (LLM confidence + hallucination tracking)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 entropy_capsule.py
echo ""

echo "▶ LAYER 4 — Session Drift Monitor (behavioral integrity + HALT logic)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 session_drift_monitor.py
echo ""

echo "▶ LAYER 5 — Process Doppelganger (kernel-level name spoofing via prctl)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 -c "
from process_doppelganger import hide_process_name
hide_process_name('rsyslogd')
print('[+] prctl(PR_SET_NAME) called — process renamed to: rsyslogd')
with open('/proc/self/comm', 'r') as f:
    name = f.read().strip()
print(f'[+] /proc/self/comm confirms: {name}')
print(f'[+] Visible to ps/top/htop as: {name}')
print('[i] Agent now masquerades as legitimate system daemon')
"
echo ""

echo "▶ LAYER 6 — Sandbox Detection (environment fingerprinting)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 -c "
from agent.sandbox_check import is_sandbox, is_low_uptime
with open('/proc/uptime', 'r') as f:
    uptime_secs = float(f.read().split()[0])
hours = uptime_secs / 3600
print(f'[+] System uptime:      {uptime_secs:.0f}s ({hours:.1f}h)')
print(f'[+] Low uptime flag:    {is_low_uptime()}')
print(f'[+] Sandbox verdict:    {is_sandbox()}')
verdict = 'EXIT — sandbox detected' if is_sandbox() else 'CONTINUE — environment looks real'
print(f'[i] Agent decision:     {verdict}')
"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pipeline complete — 6 layers demonstrated"
echo "  56 tests passing │ CI green │ Offline │ No API key │ No cloud"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
