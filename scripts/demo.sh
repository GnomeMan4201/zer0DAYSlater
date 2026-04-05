#!/usr/bin/env bash
set -euo pipefail
export PYTHONWARNINGS=ignore

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

GRN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'
CYN='\033[0;36m'; DIM='\033[2m'; BLD='\033[1m'; RST='\033[0m'

sep() { echo -e "${DIM}────────────────────────────────────────${RST}"; }

sep
echo -e "  ${BLD}zer0DAYSlater${RST} — LLM-Driven Adaptive Exfil Framework"
sep
echo ""

python3 -c "import config, llm_command_parser" 2>/dev/null || {
  echo -e "  ${RED}✗${RST}  missing deps — run: pip install -r requirements.txt"
  exit 1
}
echo -e "  ${GRN}✓${RST}  core modules loaded"
echo -e "  ${CYN}→${RST}  mode: DEMO  (no live infrastructure required)"
echo ""

python3 - << 'PYEOF'
import time, random

GRN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'
CYN='\033[0;36m'; DIM='\033[2m'; BLD='\033[1m'; RST='\033[0m'

def delay(t=0.3): time.sleep(t)

# ── LLM PARSE ───────────────────────────────────────────────────
print(f"  {BLD}LLM OPERATOR{RST}")
delay(0.4)
print(f"  {DIM}parsing command: 'exfil ssh_keys via best available channel'{RST}")
delay(0.5)
print(f"  {GRN}✓{RST}  action    : exfil")
print(f"  {GRN}✓{RST}  targets   : ssh_keys, credentials")
print(f"  {GRN}✓{RST}  priority  : high")
print(f"  {GRN}✓{RST}  noise     : silent")
print()

# ── DRIFT MONITOR ────────────────────────────────────────────────
delay(0.3)
print(f"  {BLD}SESSION DRIFT MONITOR{RST}")
sessions = [
    ("gen-001", 0.91, "STABLE"),
    ("gen-002", 0.87, "STABLE"),
    ("gen-003", 0.61, "WARN"),
    ("gen-004", 0.94, "STABLE"),
]
for sid, score, status in sessions:
    delay(0.25)
    col = GRN if status == "STABLE" else YEL
    print(f"  [{DIM}{sid}{RST}]  drift={score:.2f}  {col}{status}{RST}")
print()

# ── CHANNEL SELECTION ────────────────────────────────────────────
delay(0.3)
print(f"  {BLD}ADAPTIVE CHANNEL MANAGER{RST}")
channels = [
    ("HTTPS",  True,  142, "OK"),
    ("WS",     True,   87, "OK"),
    ("DNS",    False, 201, "DETECTED"),
    ("ICMP",   True,   34, "OK"),
]
for ch, ok, ms, result in channels:
    delay(0.2)
    col = GRN if ok else RED
    print(f"  {ch:<6}  {col}{result:<10}{RST}  {ms}ms")
print(f"  {GRN}✓{RST}  selected: HTTPS + ICMP  (DNS suppressed)")
print()

# ── PAYLOAD MUTATION ─────────────────────────────────────────────
delay(0.3)
print(f"  {BLD}PAYLOAD MUTATOR{RST}")
mutations = [
    ("base64_wrap",   "personality: ghost"),
    ("chunk_split",   "personality: ghost"),
    ("timing_jitter", "personality: ghost"),
]
for mut, persona in mutations:
    delay(0.2)
    print(f"  {GRN}✓{RST}  {mut:<18} [{DIM}{persona}{RST}]")
print()

# ── ENTROPY GATE ─────────────────────────────────────────────────
delay(0.3)
print(f"  {BLD}ENTROPY CAPSULE{RST}")
delay(0.4)
print(f"  entropy score : 0.83")
print(f"  gate decision : {GRN}PASS{RST}")
print(f"  {GRN}✓{RST}  payload cleared for dispatch")
PYEOF

echo ""
sep
echo -e "  ${GRN}✓${RST}  session complete"
echo -e "  ${CYN}→${RST}  3 mutations applied — DNS suppressed by channel manager"
echo -e "  ${CYN}→${RST}  entropy gate passed — payload dispatched via HTTPS + ICMP"
sep
echo ""
