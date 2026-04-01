<p align="center">

[![CI](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml/badge.svg)](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml)

  <img src="assets/zer0DAYSlater_logo.jpg" alt="zer0DAYSlater" width="340"/>

</p>

# zer0DAYSlater

**Operator-controlled post-exploitation framework with a local LLM command interface and adversarial session integrity monitoring.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#)
[![Tests](https://img.shields.io/badge/tests-29%2F29-brightgreen.svg)](#)

---

zer0DAYSlater is a post-exploitation research framework built around two ideas that most frameworks ignore:

**1. Natural language should be the operator interface.** Tell it what to do in plain English — `"exfil user profiles and ssh keys after midnight, stay silent"` — and a local Mistral instance parses intent into structured action objects, resolves time expressions, and dispatches to the appropriate module. No fixed command syntax. No cloud. No network calls. The LLM runs on your machine.

**2. An agent that cannot detect its own reasoning degradation is a liability, not a capability.** The session drift monitor sits between the parser and the dispatcher, tracking every parsed action against the operator's stated baseline. Semantic drift, scope creep, noise violations, structural decay — all scored in real time with a rolling entropy model. At WARN threshold the operator is flagged. At HALT threshold execution stops.

---

## How it works
```
operator types natural language command
        ↓
llm_operator — Mistral parses intent into structured action object
  {action, targets, schedule, priority, noise, rationale}
        ↓
session_drift_monitor — scores action against session baseline
  signals: semantic_drift / scope_creep / structural_decay /
           noise_violation / schedule_slip / parse_failure
  NOMINAL → continue │ WARN → flag operator │ HALT → stop execution
        ↓
wait_for_schedule — holds until execution window
        ↓
dispatch to module (exfil / persist / lateral / cloak / recon)
        ↓
c2_mesh_agent — encrypted peer-to-peer result reporting
        ↓
tui_dashboard — live session state
```

---

## Session drift monitor

The drift monitor maintains a rolling session window and scores each
parsed action against the baseline established by the operator's first command.
```
operator> exfil user profiles and ssh keys after midnight, stay silent
[OK  ] drift=0.000 [                    ]

operator> exfil credentials after midnight
[OK  ] drift=0.175 [███                 ]
  ↳ scope_creep (sev=0.40): Target scope expanded beyond baseline
  ↳ noise_violation (sev=0.50): Noise level escalated from 'silent' to 'normal'

operator> exfil credentials, documents, and network configs
[WARN] drift=0.552 [███████████         ]
  ↳ scope_creep (sev=0.60): new targets: ['credentials', 'documents', 'network_configs']

operator> exfil everything aggressively right now
[HALT] drift=1.000 [████████████████████]
  ↳ noise_violation (sev=1.00): Noise escalated to 'aggressive'
  ↳ scope_creep (sev=0.40): new targets: ['*']

SESSION REPORT: HALT
  Actions: 5 │ Final score: 1.0 │ Signals: 10
  Breakdown: scope_creep×3, noise_violation×3, structural_decay×3, semantic_drift×1
```

Drift scoring is weighted by signal type, amplified by repetition, and
decayed by recency. A single anomaly is a signal. The same anomaly three
times in a window is a pattern.

---

## LLM operator interface

Powered by a local Mistral instance via Ollama. Offline. No API key.
Configurable via `ZDS_LLM_MODEL` env var.
```python
from llm_operator import parse_operator_command

result = parse_operator_command("exfil ssh keys and credentials after 3pm, low noise")
# {
#   "action":    "exfil",
#   "targets":   ["ssh_keys", "credentials"],
#   "schedule":  "2025-11-09T15:00:00+00:00",
#   "priority":  "normal",
#   "noise":     "silent",
#   "rationale": "Operator wants credential exfil deferred to afternoon window."
# }
```

Time expressions are pre-resolved before the LLM call to eliminate
hallucination on time arithmetic. Temperature is set to 0.1 for
deterministic structured output.

---

## Architecture
```
zer0DAYSlater/
├── llm_operator.py             Mistral-backed NL → structured action objects
├── session_drift_monitor.py    adversarial session integrity layer
├── omega_campaign.sh           campaign entry point + env validation
├── tui_dashboard.py            live operator session dashboard
├── memory_loader.py            in-memory payload execution without disk touch
├── process_doppelganger.py     process name spoofing via prctl
├── process_cloak.py            process identity masking
├── evasion_win.py              Windows AMSI/ETW patch (xor eax,eax; ret)
├── persistence.py              multi-vector persistence binding
├── lateral.py                  authenticated lateral movement
├── c2_mesh_agent.py            peer-to-peer mesh agent with mTLS
├── peer_auth.py                NaCl symmetric key peer verification
├── proxy_fallback_check.py     C2 channel fallback logic
└── core/
    ├── adaptive_channel_manager.py   transport selection + fallback
    ├── exfil_dns.py                  DNS exfil channel
    ├── exfil_https.py                HTTPS exfil channel
    ├── exfil_ws.py                   WebSocket exfil channel
    └── exfil_mqtt.py                 MQTT exfil channel
```

**C2 channels:** DNS · HTTPS · WebSocket · MQTT · ICMP

---

## Install
```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater
./install_omega.sh
```

Requires [Ollama](https://ollama.ai) with a local model:
```bash
ollama pull mistral
```

Configure before use:
```bash
export ZDS_AUTH_TOKEN=your_token
export ZDS_C2_WS_URL=wss://your-c2-server:8765
export ZDS_HTTPS_ENDPOINT=https://your-c2-server/api
export ZDS_PLUGIN_SERVER=https://your-c2-server
export ZDS_CONTROL_DOMAIN=your.c2.domain
export ZDS_PEERS=192.168.x.x,192.168.x.y
export ZDS_LLM_MODEL=mistral:latest   # or llama3.1, phi3, etc.
```

Run:
```bash
source .venv/bin/activate
./omega_campaign.sh
```

---

## Tests
```bash
source .venv/bin/activate
python3 -m pytest tests/ -v
# 29 passed
```

---

## Legal

For authorized red team operations and security research in controlled
environments only. Unauthorized use is prohibited.

---

*zer0DAYSlater // badBANANA research // GnomeMan4201*
