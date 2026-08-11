# Security Policy

## Reporting a vulnerability

Do **not** open a public issue for a suspected vulnerability in `zer0DAYSlater`.

Preferred reporting path:

1. Use **Security → Report a vulnerability** for this repository when GitHub private vulnerability reporting is available.
2. Otherwise email **badbanana@proton.me** with the subject `zer0DAYSlater security report`.

Include the affected commit/version, execution path, expected invariant, observed behavior, minimal reproduction, impact, and any proposed mitigation. Avoid sending unrelated credentials, third-party data, or executable material that is not necessary to demonstrate the issue.

## What counts as a security defect here

This repository intentionally preserves dual-use adversarial mechanisms for historical/defensive research. A useful report identifies a failure of an intended control or boundary, for example:

- bypass of plugin signature/authentication checks;
- cryptographic key, peer-authentication, or transport-verification failures;
- execution occurring without the documented operator/trust decision;
- unexpected network exposure or unsafe default binding;
- unintended persistence or filesystem modification outside the documented lab behavior;
- secret leakage through logs, environment handling, generated artifacts, or CI;
- dependency or supply-chain issues with a meaningful exploit path;
- a documented remediation that is no longer true in the current implementation.

Simply observing that historical modules model persistence, transport, process masquerading, or dynamic execution is not by itself a vulnerability report; those behaviors are part of the retained research surface.

## Supported state

The current default branch is the maintained reference state. Historical commits may intentionally preserve superseded weaknesses for provenance, so reports against older revisions must identify the exact commit or release.

## Disclosure

I aim to acknowledge reproducible reports within seven days. Validation and remediation timing depends on severity, reproducibility, and project status; no fixed remediation deadline is promised before triage.

Confirmed fixes should be documented when practical. Reporter credit is welcome unless anonymity is requested.

## Research boundary

Repository availability does not authorize deployment or testing against third-party systems. Use this code only in isolated environments you own or are explicitly authorized to assess.
