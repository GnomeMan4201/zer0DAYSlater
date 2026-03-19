<p align="center">
  <img src="assets/zer0DAYSlater_logo.jpg" alt="zer0DAYSlater" width="340"/>
</p>

# zer0DAYSlater

**Post-exploitation framework — process cloaking, multi-channel C2, adaptive persistence, and LLM-driven operator interface.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](#)

---

zer0DAYSlater is an operator-centric post-exploitation framework built for stealth and resilience. It runs multi-channel C2 across DNS, HTTPS, MQTT, and ICMP, with a natural-language operator interface powered by a local LLM and a live TUI dashboard for session management.

---

## Capabilities

- `memory_loader.py` — in-memory payload execution without touching disk
- `process_doppelganger.py` — process name spoofing via prctl
- `evasion_win.py` — Windows-side evasion and sandbox detection
- `persistence.py` — multi-vector persistence binding
- `lateral.py` — authenticated lateral movement
- `c2_mesh_agent.py` — peer-to-peer mesh agent with mTLS
- `peer_auth.py` — symmetric key peer verification
- `process_cloak.py` — process identity masking
- `proxy_fallback_check.py` — C2 channel fallback logic
- `llm_command_parser.py` — natural language command interface
- `tui_dashboard.py` — live operator dashboard

**C2 channels:** DNS, HTTPS, MQTT, ICMP

---

## Install
```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./install_omega.sh
./omega_campaign.sh
```

---

## Legal

For authorized red team operations and security research in controlled environments only. Unauthorized use is prohibited.

---

*zer0DAYSlater // badBANANA research // GnomeMan4201*
