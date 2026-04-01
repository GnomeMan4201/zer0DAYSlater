## Quickstart
```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater
./install_omega.sh
./doctor.sh        # verify environment
./demo.sh          # confirm system works without live infrastructure
```

Expected demo output:
```
[✓] DEMO_MODE active
[✓] LLM parse: {action: exfil, ...}
[✓] session_drift_monitor loaded
[✓] entropy_capsule loaded
[✓] payload_mutator loaded
[Gen 0] HTTPS  ✓ OK  142ms
[Gen 1] WS     ✓ OK   87ms
[Gen 2] DNS    ✗ DETECTED  201ms
[✓] Peer 127.0.0.1 verified=True
[✓] Demo complete
```

For live use:
```bash
cp .env.example .env
# edit .env with real values
source .env
./omega_campaign.sh
```

---

<p align="center">

[![CI](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml/badge.svg)](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml)

  <img src="assets/zer0DAYSlater_logo.jpg" alt="zer0DAYSlater" width="340"/>

</p>

# zer0DAYSlater

**Operator-controlled post-exploitation framework with a local LLM command interface, adversarial session integrity monitoring, and feedback-driven payload mutation.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#)
[![Tests](https://img.shields.io/badge/tests-56%2F56-brightgreen.svg)](#)

---

zer0DAYSlater is a post-exploitation research framework built around ideas most frameworks ignore.

**Natural language is the operator interface.** Tell it what to do in plain English — `"exfil user profiles and ssh keys after midnight, stay silent"` — and a local Mistral instance parses intent into structured action objects, resolves time expressions, and dispatches to the appropriate module. No fixed command syntax. No cloud. No network calls. The LLM runs on your machine.

**An agent that cannot detect its own reasoning degradation is a liability, not a capability.** Two monitoring layers sit between the parser and the dispatcher. The drift monitor tracks what the agent decides. The entropy capsule tracks how confidently it decides. Together they score every action against the session baseline and halt execution before bad decisions propagate.

**Payloads evolve.** The mutation engine maintains fitness scores per personality, updated by channel feedback. Detection penalizes. Success boosts. High entropy and drift trigger forced rotation. The agent learns what works for this operator, on this network, in this session.

**Trust is cryptographic.** The mTLS mesh issues ephemeral NaCl keypairs, verifies peers with time-bounded signed handshakes, encrypts all relay traffic with Curve25519/XSalsa20/Poly1305, and quarantines peers that fail verification. No plaintext. No assumed trust.

---

## Pipeline
```
operator types natural language command
        ↓
llm_operator          — Mistral parses intent → structured action object
  {action, targets, schedule, priority, noise, rationale}
        ↓
entropy_capsule       — scores LLM output confidence and coherence
  signals: token_entropy / confidence_collapse / hallucination /
           coherence_drift / instability_spike
  entropy score 0.0–1.0 │ NOMINAL → ELEVATED → CRITICAL
        ↓
session_drift_monitor — scores behavioral deviation from baseline
  signals: semantic_drift / scope_creep / structural_decay /
           noise_violation / schedule_slip / parse_failure
  drift score 0.0–1.0 │ NOMINAL → WARN → HALT
        ↓
payload_mutator       — selects personality, applies mutation ops
  personalities: scout / ghost / leech / phantom / parasite / surgeon
  ops: rotate / morph / fragment / delay / decoy
  fitness updated by channel feedback each generation
        ↓
adaptive_channel_manager — transport selection with fallback
        ↓
mtls_mesh             — encrypted peer relay, verified handshake,
                        quarantine for unverified nodes
        ↓
agent_core            — executes, reports back through mesh
        ↓
tui_dashboard         — live session state
```

---

## Session drift monitor
```
operator> exfil user profiles and ssh keys after midnight, stay silent
[OK  ] drift=0.000 [                    ]

operator> exfil credentials after midnight
[OK  ] drift=0.175 [███                 ]
  ↳ scope_creep (sev=0.40): Target scope expanded beyond baseline
  ↳ noise_violation (sev=0.50): Noise escalated from 'silent' to 'normal'

operator> exfil credentials, documents, and network configs
[WARN] drift=0.552 [███████████         ]
  ↳ scope_creep (sev=0.60): new targets: ['credentials', 'documents', 'network_configs']

operator> exfil everything aggressively right now
[HALT] drift=1.000 [████████████████████]
  ↳ noise_violation (sev=1.00): Noise escalated to 'aggressive'
  ↳ scope_creep (sev=0.40): new targets: ['*']

SESSION REPORT: HALT
  Actions: 5 │ Score: 1.0 │ Signals: 10
  Breakdown: scope_creep×3, noise_violation×3, structural_decay×3, semantic_drift×1
```

Drift scoring is weighted by signal type, amplified by repetition, decayed
by recency. A single anomaly is a signal. The same anomaly three times is a pattern.

---

## Entropy capsule engine

Instruments the LLM's output stream directly — not what it decides,
but how confidently it decides it.
```
operator> exfil user profiles and ssh keys after midnight, stay silent
[OK  ] entropy=0.138 [██                  ]

operator> do the thing with the stuff
[OK  ] entropy=0.181 [███                 ]
  ↳ hallucination (mag=1.00): 100% of targets not grounded in operator command
  ↳ coherence_drift (mag=0.60): rationale does not explain action 'recon'

operator> [degraded parse]
[ELEV] entropy=0.420 [████████            ]
  ↳ confidence_collapse (mag=0.90): model explanation missing
  ↳ instability_spike (mag=0.94): Δ0.473 entropy jump between actions

ENTROPY REPORT: ELEVATED
  Breakdown: hallucination×2, coherence_drift×2, token_entropy×2,
             confidence_collapse×1, instability_spike×1
```

Shannon entropy scoring on rationale text. Hallucination detection
compares output targets against grounded operator input. Instability
spikes catch sudden model degradation between consecutive actions.

---

## Payload mutator

Feedback-driven mutation engine. Personalities have fitness scores.
Fitness is updated by what succeeds and what gets detected.
```
[Gen 0] surgeon    ops=['delay', 'morph']  fitness=0.70  ✓ HTTPS
[Gen 1] surgeon    ops=['delay', 'morph']  fitness=0.78  ✗ DNS [DETECTED]
[Gen 2] surgeon    ops=['delay', 'morph']  fitness=0.58  ✓ WS
[Gen 3] surgeon    ops=['morph']           fitness=0.66  ✗ HTTPS
[Gen 4] surgeon    ops=['delay', 'morph']  fitness=0.61  ✓ WS
[Gen 5] leech      ops=['fragment']        fitness=0.65  ✗ DNS [DETECTED]

── Fitness after campaign ──
  scout        0.60 ████████████
  ghost        0.55 ███████████
  leech        0.45 █████████
  surgeon      0.69 █████████████
```

Inspired by the [chain mutation engine](https://github.com/GnomeMan4201/chain),
rebuilt as a clean typed API integrated with the operator pipeline.
High drift + high entropy triggers forced personality rotation.

---

## mTLS mesh

Mutual authentication before any data relay. Peers that fail
verification are quarantined — not retried.
```
[A] fingerprint: 5a29cce0619698ec
[B] fingerprint: 911871d07b46a115

[*] B → A handshake token valid:     True
[*] Tampered token rejected:         True
[*] Encrypted message roundtrip:     True
[*] Tampered ciphertext rejected:    True
[*] Quarantine state recorded:       True
```

Ephemeral NaCl keypairs per node. Signed handshake with 30-second
replay protection window. Length-prefixed framing with 10MB max frame.
Dynamic topology — peer list propagation, dead peer pruning every 30s.

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

Time expressions pre-resolved before the LLM call to eliminate
hallucination on time arithmetic. Temperature 0.1 for deterministic output.

---

## Architecture
```
zer0DAYSlater/
├── llm_operator.py             Mistral-backed NL → structured action objects
├── session_drift_monitor.py    behavioral drift detection + HALT logic
├── entropy_capsule.py          LLM output entropy + hallucination tracking
├── payload_mutator.py          feedback-driven personality/mutation engine
├── mtls_mesh.py                NaCl mTLS peer mesh with quarantine
├── omega_campaign.sh           campaign entry point + env validation
├── tui_dashboard.py            live operator session dashboard
├── memory_loader.py            in-memory payload execution without disk touch
├── process_doppelganger.py     process name spoofing via prctl
├── process_cloak.py            process identity masking
├── evasion_win.py              Windows AMSI/ETW patch (xor eax,eax; ret)
├── persistence.py              multi-vector persistence binding
├── lateral.py                  authenticated lateral movement
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

## Tests
```bash
source .venv/bin/activate
python3 -m pytest tests/ -v      # unit tests
./scripts/smoke.sh               # runtime smoke checks
# 56 passed
```

---

## Legal

For authorized red team operations and security research in controlled
environments only. Unauthorized use is prohibited.

---

*zer0DAYSlater // badBANANA research // GnomeMan4201*
