# zer0DAYSlater

> Advanced post-exploitation framework with evasion, persistence, and covert C2 capabilities.

![zer0DAYSlater Logo](assets/zer0DAYSlater_logo.png)

---

## Overview

`zer0DAYSlater` is an operator-centric, modular post-exploitation framework built for stealth, resilience, and operational control. Designed for advanced red team campaigns and security research, it includes:

- Dynamic process cloaking and evasion  
- Multi-channel exfiltration (DNS, HTTPS, MQTT, ICMP)  
- Peer-to-peer mesh agent C2  
- Live operator dashboard with interactive command execution  
- Loot tagging, PDF generation, and session replay  

---

## Features

- Evasion — memory loaders, process spoofing, sandbox detection  
- Persistence — ghost daemons, lateral movement, kill switches  
- Covert C2 — MQTT, DNS, and mTLS plugins for flexible communication  
- LLM Command Parsing — natural-language interface for automation  
- Mission Reporting — generates mission_report.pdf and loot summaries  

---

## Installation

> Requires: Python 3.13+, Linux. A virtual environment is recommended.

```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater

# Optional: create isolated venv
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run campaign setup
./install_omega.sh
```

Testing

chmod +x zer0DAYSlater_test_runner.sh
./zer0DAYSlater_test_runner.sh

Usage

./omega_campaign.sh
omega-operator

This drops you into an interactive Ω> shell to issue system-level commands via the operator interface.
Example Modules

    memory_loader.py – in-memory stealth execution

    process_doppelganger.py – process name spoofing

    peer_auth.py – peer verification using symmetric keys

    tools/task_dispatcher.py – dispatch commands to agents

    agent/ghost_daemon.py – stealthy persistence loop

Assets Preview

zer0DAYSlater Logo
Legal Disclaimer

These tools are intended strictly for authorized research, security testing, and educational purposes. Unauthorized use is prohibited.

    Authorization Notice:
    Use only in environments where you have explicit legal authorization.
    You are solely responsible for compliance with all applicable laws and regulations.

Known Dependency Notice

scapy==2.6.1 is present in requirements.txt and currently has a known deserialization vulnerability (see Safety ID 80587).
If you use Scapy, only process trusted inputs or isolate its usage. This will be updated once a patched version is available.
Author

GnomeMan4201
dev.to/gnomeman4201

github.com/GnomeMan4201

