# zer0DAYSlater

> Historical adversarial-systems research framework retained for inspectable defensive study, regression work, and provenance.

[![CI](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml/badge.svg)](https://github.com/GnomeMan4201/zer0DAYSlater/actions/workflows/ci.yml)

![zer0DAYSlater Logo](https://github.com/GnomeMan4201/zer0DAYSlater/raw/main/assets/zer0DAYSlater_logo.jpg)

---

## Status

`zer0DAYSlater` is retained as an adversarial-systems research artifact rather than presented as a current flagship or production red-team platform.

Its useful public value is inspectability: the repository exposes implementation choices, defensive indicators, historical weaknesses, remediation attempts, and an instrumented lab surface for studying how post-exploitation-style behaviors appear to defenders.

The framework includes dual-use mechanisms. Treat the repository as **isolated-lab research code**, not as a deployment recommendation.

---

## Research scope

The codebase explores observable behavior around:

- process-name masquerading and evasion instrumentation
- multi-channel transport and fallback behavior
- peer-to-peer coordination and authentication failure modes
- LLM-assisted operator/session analysis
- local task dispatch and instrumented execution paths
- session logging, replay, and defensive artifact generation

The repository is most useful when read from both sides: implementation behavior and the defender-facing indicators documented below.

---

## Lab installation

Requires Python 3.10+ and Linux for the primary development path. Use an isolated environment.

```bash
git clone https://github.com/GnomeMan4201/zer0DAYSlater.git
cd zer0DAYSlater
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the repository validation harness:

```bash
chmod +x zer0DAYSlater_test_runner.sh
./zer0DAYSlater_test_runner.sh
```

The repository also retains a local demo harness:

```bash
./scripts/demo.sh
```

A passing test/demo run establishes only the behavior covered by that revision's harness. It does not establish stealth, operational effectiveness, cryptographic assurance, or suitability for a real environment.

---

## Architecture under study

The operator pipeline combines task interpretation, execution/transport components, and three monitoring concepts: drift observes what the agent decides, entropy observes confidence characteristics, and mutation analysis records what survives transformations in the channel. Session reports preserve those observations for later analysis.

This architecture should be evaluated as research code with a deliberately visible attack surface, not as a hardened command-and-control design.

---

## Defender perspectives and historical weaknesses

This section documents security-relevant implementation choices and previously identified weaknesses. Publishing them is part of the artifact: the repository should be possible to analyze defensively without reverse-engineering its intent from scratch.

### Dynamic execution boundary

A plugin path historically decrypted a remote buffer and executed it through Python `exec()`. That boundary creates full code-execution authority on the agent host if its trust controls fail.

**Repository status:** Ed25519 signature verification was added before plugin execution; the encryptor signs `SHA256(code_bytes)` and the current loader rejects missing or invalid signatures before reaching `exec()`. Historical remediation commit: `bab60dd`.

The existence of a signature check does not make arbitrary dynamic execution intrinsically safe; reviewers should continue to treat this boundary as high risk.

### Plugin key derivation

The historical plugin encryptor derived an AES-GCM key from an eight-character agent identifier, which did not provide meaningful secret entropy.

**Repository status:** key derivation was changed to HKDF-SHA256 using `ZDS_PLUGIN_SALT` plus a fixed context string. Historical remediation commit: `3a2989c`.

The implementation contains a deterministic fallback salt when `ZDS_PLUGIN_SALT` is not configured. That fallback improves derivation structure but is not an out-of-band secret; a real trust boundary requires an operator-supplied random salt.

### Mesh handshake authentication

A historical mesh handshake token used an unkeyed SHA-256 digest over public material. Commit `ea805df` attempted to harden the signer with HMAC-SHA256 and constant-time comparison.

**Current status: unresolved / internally inconsistent.** The current `_sign_handshake()` emits an HMAC keyed from the sender's private material, but the live `_handle_handshake()` path calls `_verify_handshake()` without that HMAC key. The verifier then falls back to bare SHA-256 over public data. Because the sender emits HMAC while the live verifier computes bare SHA-256, the real call path does not establish a functioning authenticated handshake. Tests that manually supply the HMAC key do not exercise this live peer-verification boundary.

Do not treat the mesh `VERIFIED` state as a cryptographically validated trust guarantee in the current revision. Correct peer authentication requires a protocol redesign with a verifier-available trust anchor or proof-of-possession mechanism, not another wording change.

### TLS verification

Historical C2-related components disabled certificate verification, creating a straightforward interception opportunity.

**Repository status:** the documented remediation introduced certificate-fingerprint pinning when configured and system CA verification otherwise. Historical remediation commit: `2b0ea7a`.

These status notes identify repository changes and current source observations, not independent cryptographic assurance.

---

## Published defensive indicators

The following artifacts are associated with normal framework operation and are retained so defenders can build detections without first reconstructing the codebase.

### Linux filesystem

| Path | Source |
|---|---|
| `/tmp/.zds_agent.py` | deployed agent artifact |
| `/tmp/.zds.log` | agent runtime log |
| `/etc/cron.d/systemd-updater` | persistence simulation artifact |
| `~/.local/bin/sysupd` | installed binary path used by the persistence path |
| `loot_log.json` | C2-side collection log |

### Windows registry

| Key | Value name |
|---|---|
| `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` | `OneDrive` |

### Network and environment

Potentially useful framework-specific indicators include WebSocket traffic on the configured lab endpoint, DNS task/exfil patterns, MQTT topics under `zds/exfil/`, and process environments containing names such as `ZDS_AUTH_TOKEN`, `ZDS_C2_WS_URL`, `ZDS_HTTPS_ENDPOINT`, or `ZDS_CONTROL_DOMAIN`.

Context matters: indicator presence establishes correspondence with a known artifact or configuration pattern, not attribution to a particular operator.

### YARA research rule

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

## Process masquerading as a detection surface

The repository includes Linux process-name manipulation using `setproctitle` / `prctl(PR_SET_NAME)`-style behavior. A useful defensive correlation is a process whose displayed name resembles a normal system binary while its executable path, parentage, environment, or runtime behavior does not match that identity.

This is a stronger investigative signal when combined with additional telemetry than when treated as a standalone attribution rule.

---

## Verification boundary

A green CI badge or local test run means the checks configured for that revision passed. It does **not** prove:

- operational effectiveness or stealth
- resistance to EDR or network controls
- cryptographic correctness beyond the exercised tests
- functioning peer authentication on the current mesh handshake path
- safety of dynamic execution paths
- suitability for deployment outside an isolated lab

Historical vulnerability descriptions and remediation commits should be checked against the current call paths before being repeated as current findings.

---

## Provenance

This repository is retained because deleting historical adversarial research would erase useful implementation history, defensive indicators, and remediation lineage. It is intentionally not positioned as the front door to current badBANANA work.

For current public research, start from the main GnomeMan4201 profile and the projects explicitly featured there.

---

## Author

**GnomeMan4201**

badBANANA Research