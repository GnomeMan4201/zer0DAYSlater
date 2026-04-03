# Changelog

All notable changes to zer0DAYSlater are documented here.

---

## [Unreleased]

---

## [2026.04.02] — Crypto Hardening + Research Instrumentation

### Security — all four open issues closed

- **fix: HMAC-SHA256 mesh handshake tokens** (`ea805df`)
  Replaced bare `SHA256(public_key || peer_ip || timestamp)` with
  `HMAC-SHA256` keyed on `SHA256(private_key_bytes)`. Tokens are no longer
  forgeable from public data. Added `hmac.compare_digest()` to prevent
  timing oracle attacks. Closes #3.

- **fix: HKDF-SHA256 plugin key derivation** (`3a2989c`)
  Replaced `agent_id[:32].ljust(32, b"0")` with HKDF-SHA256 keyed on
  `ZDS_PLUGIN_SALT`. Plugin keys are no longer derivable from the agent ID
  alone. Closes #2.

- **fix: Ed25519 plugin signature verification** (`bab60dd`)
  `exec()` now requires a valid Ed25519 signature over `SHA256(code_bytes)`
  before execution. Unsigned plugins are rejected when `ZDS_PLUGIN_PUBKEY`
  is set. `plugin_encryptor.py` updated to sign blobs via
  `ZDS_PLUGIN_SIGNING_KEY`. Closes #1.

- **fix: TLS certificate fingerprint pinning** (`2b0ea7a`)
  Replaced `verify=False` with `FingerprintAdapter` in `dispatcher.py`.
  Pins against `ZDS_C2_CERT_FINGERPRINT` when set; falls back to system CA
  verification. Never silently accepts arbitrary certificates. Closes #4.

### Research instrumentation — new modules

- **entropy_capsule.py** — instruments LLM output entropy across a session.
  Tracks token entropy, confidence collapse, hallucination, coherence drift,
  and instability spikes. The agent-side mirror of external LLM benchmarking.

- **session_drift_monitor.py** — behavioral integrity monitoring with HALT
  logic. Signals: semantic_drift, scope_creep, noise_violation,
  parse_failure, escalation_pattern.

- **payload_mutator.py** — feedback-driven personality and mutation operator
  selection. Six personalities, five mutation ops, fitness scores update
  per channel attempt.

- **mtls_mesh.py** — NaCl Box peer mesh with HMAC-SHA256 handshake tokens,
  quarantine state, heartbeat pruning, and length-prefix framing.

### Toolchain

- **tools/session_report.py** — unified drift + entropy + mutation artifact.
  Terminal summary and JSON export. Fires automatically on operator console
  exit. `--save-report PATH` flag available.

- **tools/compare_sessions.py** — diffs two session JSON reports. Surfaces
  drift/entropy score deltas, new/resolved signals, fitness shifts, and
  timeline entropy correlation.

- **llm_operator.py** — readline history (`~/.zds_history`), `--replay`
  flag, `--save-report` flag. Session report fires on exit via `finally:`.

- **dispatcher.py** — `_run()` extracted, eliminating ~60 lines of
  duplicated dispatch logic. Full pipeline: drift → entropy → mutation →
  handler → feedback.

### Code quality

- Zero flake8 violations (F401, F811, F841, W291, W293, W391)
- 79 tests across `tests/test_core.py` and `tests/test_tools.py`
- CI enforces: pytest → flake8 → secrets check on every push
- `.env.example` documents all env vars with generation instructions
- VERSION bumped to 2026.04.02.0001

---

## [v1.1.0] — Defender Perspective Release

Initial public release with full Defender Perspectives section, YARA rule,
known IoCs, and cryptographic weakness documentation.

---

*badBANANA research // GnomeMan4201*
