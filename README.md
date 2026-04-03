# zer0DAYSlater

> Operator-controlled post-exploitation research framework with adaptive C2, evasion instrumentation, and LLM-driven session analysis.

[![CI](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml/badge.svg)](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml)


![zer0DAYSlater Logo](https://github.com/GnomeMan4201/zer0DAYSlater/raw/main/assets/zer0DAYSlater_logo.jpg)

---

## Overview

`zer0DAYSlater` is a modular post-exploitation framework built for **authorized red team research and adversarial simulation**. It is designed to replicate the tradecraft of advanced persistent threat actors in a controlled, fully observable environment — so defenders can study, instrument, and respond to realistic attack behavior without exposing live infrastructure.

Core capabilities:

- Dynamic process cloaking and evasion instrumentation
- Multi-channel exfiltration (DNS, HTTPS, MQTT, ICMP) with adaptive channel selection
- Peer-to-peer mesh agent C2 with cryptographic peer verification
- LLM operator console with session drift monitoring and hallucination kill-switch
- Live TUI dashboard with interactive command execution
- Loot tagging, PDF mission reporting, and session replay

This is not a fire-and-forget exploit kit. Every action is logged, every channel is observable, and the entire system is designed to be run in air-gapped or isolated lab environments. The goal is instrumented adversarial simulation — not operational offense.

---

## Features

| Module | Description |
|---|---|
| `memory_loader.py` | In-memory payload execution without disk writes |
| `process_doppelganger.py` | Process name spoofing via `prctl(PR_SET_NAME)` |
| `evasion_win.py` | Windows AMSI/ETW instrumentation (research only) |
| `peer_auth.py` | Peer verification using NaCl Box key exchange |
| `c2_mesh_agent.py` | P2P mesh C2 with covert channel routing |
| `agent/ghost_daemon.py` | Stealthy persistence loop for simulation |
| `tools/task_dispatcher.py` | Agent tasking and command dispatch |
| `llm_command_parser.py` | Natural language → structured operator commands |
| `core/adaptive_channel_manager.py` | Multi-protocol transport with fallback logic |

---

## Installation

> Requires: Python 3.10+, Linux. Virtual environment strongly recommended.
```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
./install_omega.sh
```

**Testing:**
```bash
chmod +x zer0DAYSlater_test_runner.sh
./zer0DAYSlater_test_runner.sh
```

**Demo mode** (local endpoints, no external infrastructure required):
```bash
./scripts/demo.sh
```

---

## Usage
```bash
./omega_campaign.sh
omega-operator
```

This drops you into an interactive `Ω>` shell for issuing system-level commands via the LLM operator interface.

---

## Architecture

The operator pipeline — from natural language command to execution:
The three monitoring layers compose: drift watches *what* the agent decides,
entropy watches *how confidently* it decides, and the mutator watches
*what survives* in the channel. All three feed into the session report
for post-op analysis.

---

## Defender Perspectives & Known Weaknesses

This section documents the framework's attack surface, cryptographic limitations, and behavioral indicators — written for defenders, researchers, and contributors who want to understand the threat model from the inside.

Publishing this is intentional. Transparency about how a dual-use tool works is what separates research infrastructure from a weapon. If you're conducting a defensive assessment of this repo, this section is where to start.

---

### Dynamic Execution (exec() on Remote Buffers)

**What it does:** The plugin execution path in `memory_loader.py` decrypts an AES-GCM blob received over the WebSocket channel and executes it via `exec(decrypted, {})`. The WebSocket client (`core/ws_client.py`) orchestrates the receive-decrypt-execute chain.

**Why it exists:** This is the modularity mechanism — it allows the operator to deliver arbitrary instrumentation payloads to a running agent without disk writes, mimicking fileless malware tradecraft for research observation.

**The risk, stated plainly:** If the C2 channel is compromised or the encryption key is obtained, this is full remote code execution on the agent host. There is no sandbox, no capability restriction, and no signature verification on the decrypted payload. A defender observing a Python process invoking `exec()` on a decrypted remote buffer should treat it as high-confidence malicious activity regardless of the operator's intent.

**Status: Fixed.** Ed25519 signature verification is now enforced before `exec()` in `memory_loader.py`. The plugin encryptor signs `SHA256(code_bytes)` with the operator signing key. Unsigned or incorrectly signed plugins are rejected. See commit `bab60dd`.

---

### Weak Plugin Key Derivation

**What it does:** `tools/plugin_encryptor.py` derives the AES-GCM encryption key from the `agent_id`, padded or truncated to 32 bytes. The `agent_id` is generated as the first 8 characters of a UUID string.

**The risk:** 8 characters of a UUID is not a secret. The key space is drastically smaller than AES-256 implies. An attacker who can observe agent IDs (trivially possible if C2 traffic is captured) can brute-force or reconstruct plugin keys. The encryption primitive (AES-GCM) is sound; the key derivation is not.

**Status: Fixed.** `derive_key()` now uses HKDF-SHA256 with a salt from `ZDS_PLUGIN_SALT` and a fixed context string. The key is no longer derivable from the agent ID alone. See commit `3a2989c`.

---

### Mesh Handshake Token Is Not a MAC

**What it does:** `mtls_mesh.py` generates a handshake token via `_sign_handshake()`, described in the docstring as an HMAC. In practice it computes `SHA256(public_key || peer_ip || timestamp)`.

**The risk:** This is not a keyed MAC. It incorporates no secret material. Any peer can compute a valid token from public data alone — which means "no trust without cryptographic proof" does not hold as currently implemented. The mTLS peer authentication claim is overstated.

**Status: Fixed.** `_sign_handshake()` now uses `HMAC-SHA256` keyed on `SHA256(private_key_bytes)`. The token is no longer forgeable from public data alone. `hmac.compare_digest()` prevents timing oracle attacks. See commit `ea805df`.

---

### TLS Verification Disabled

**What it does:** Multiple components disable certificate verification when connecting to `wss://` endpoints — `core/exfil_ws.py` and `core/ws_client.py` both set `check_hostname = False` and `CERT_NONE`. The generated agent bundle in `tools/agent_deploy.py` does the same for HTTPS polling.

**The risk:** Any network position capable of intercepting traffic can MitM the C2 channel without detection. This is a significant operational weakness — and also a defensive opportunity. A sinkhole or TLS inspection proxy can silently intercept all C2 communications.

**Status: Fixed.** `_handle_exfil()` in `dispatcher.py` now uses a `FingerprintAdapter` that pins against `ZDS_C2_CERT_FINGERPRINT` when set. Falls back to system CA verification (`verify=True`) — never `verify=False`. See commit `2b0ea7a`.

---

### Operational Footprint (Known IoCs)

The following artifacts are written by the framework during normal operation. These are published here proactively so defenders can build detection without reverse-engineering the source.

**Linux filesystem:**

| Path | Source |
|---|---|
| `/tmp/.zds_agent.py` | `tools/agent_deploy.py` — deployed agent script |
| `/tmp/.zds.log` | Agent runtime log |
| `/etc/cron.d/systemd-updater` | `persistence.py` — Linux persistence mechanism |
| `~/.local/bin/sysupd` | `persistence.py` — installed binary path |
| `loot_log.json` | `tools/c2_ws_server.py` — C2 loot log |

**Windows registry:**

| Key | Value Name | Source |
|---|---|---|
| `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` | `OneDrive` | `persistence.py` — disguised Run key |

**Network:**

| Indicator | Description |
|---|---|
| WebSocket on TCP 8765 (TLS) | C2 server; JSON messages contain `agent_id`, `payload` fields |
| DNS TXT query to `tasks.<domain>` | Task retrieval channel |
| High-volume `dig` with base64 subdomains | DNS exfiltration chunks |
| MQTT topic `zds/exfil/<agent_id>` | MQTT exfiltration channel |

**Environment variables:**

`ZDS_AUTH_TOKEN`, `ZDS_C2_WS_URL`, `ZDS_HTTPS_ENDPOINT`, `ZDS_CONTROL_DOMAIN` — presence of any of these in a process environment is a strong indicator of framework operation.

---

### YARA Detection Rule
```yara
rule ZDS_Zer0DAYSlater_Research_Framework
{
    meta:
        description = "Detects zer0DAYSlater framework artifacts by unique strings"
        author      = "GnomeMan4201 (self-published for defensive use)"
        confidence  = "medium"
    strings:
        $s1 = "zer0DAYSlater" ascii nocase
        $s2 = "ZDS_AUTH_TOKEN" ascii
        $s3 = "ZDS_C2_WS_URL" ascii
        $s4 = "ZDS_HTTPS_ENDPOINT" ascii
        $s5 = "ZDS_CONTROL_DOMAIN" ascii
        $s6 = "/tmp/.zds_agent.py" ascii
        $s7 = "/etc/cron.d/systemd-updater" ascii
        $s8 = "zds/exfil/" ascii
    condition:
        3 of them
}
```

---

### Process Masquerading

`process_cloak.py` uses `setproctitle` and `process_doppelganger.py` uses `prctl(PR_SET_NAME)` to rename the agent process to common system names (`systemd`, `dbus-daemon`, `sshd`, etc.).

**Detection:** Alert on processes whose name matches a known system binary but whose executable path does not correspond to the expected binary location. EDRs and auditd rules filtering on `prctl(PR_SET_NAME)` calls from non-root processes are effective here.

---

## Known Dependency Notice

`scapy==2.6.1` is present in `requirements.txt` and has a known deserialization vulnerability (Safety ID 80587). Only process trusted inputs when using Scapy, or isolate its usage. This will be updated when a patched version is available.

---

## Legal Disclaimer

These tools are intended strictly for authorized security research, red team operations, and educational purposes in environments where you have **explicit legal authorization**.
```
Authorization Notice:
Use only in environments where you have explicit written authorization.
You are solely responsible for compliance with all applicable laws.
Unauthorized use is illegal and unethical.
```

Releasing this framework publicly comes with the expectation that the security research community will use it responsibly — to build better defenses, study adversarial tradecraft, and contribute improvements. The Defender Perspectives section above exists because opacity is not a security property.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Priority areas for contribution:

- Cross-session fitness persistence for the mutation engine
- Persistent mesh node identity across sessions
- Gradual degradation detection below threshold
- Additional exfil channel implementations (ICMP, covert HTTP)

---

## Author

**GnomeMan4201**
[dev.to/gnomeman4201](https://dev.to/gnomeman4201) · [github.com/GnomeMan4201](https://github.com/GnomeMan4201)
