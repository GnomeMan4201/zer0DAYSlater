#!/usr/bin/env python3
"""
zer0DAYSlater — Session Drift Monitor

Sits between the LLM operator parser and the action dispatcher.
Tracks parsed action objects across a session window and detects:

  1. SEMANTIC DRIFT    — actions diverging from operator's stated intent
  2. SCOPE CREEP       — targets expanding beyond what operator specified
  3. STRUCTURAL DECAY  — JSON output becoming malformed or incomplete
  4. NOISE VIOLATION   — noise level escalating beyond operator's threshold
  5. SCHEDULE SLIP     — execution windows drifting from operator's stated times

An LLM-operated agent that cannot detect when its own reasoning is
degrading is a liability, not a capability.

Designed to integrate with llm_operator.py output.
Can be used standalone as a session auditor or inline as a gate.
"""
from __future__ import annotations

import json
import time
import datetime
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Drift signal types ────────────────────────────────────────────────────────

class DriftType(str, Enum):
    SEMANTIC_DRIFT    = "semantic_drift"
    SCOPE_CREEP       = "scope_creep"
    STRUCTURAL_DECAY  = "structural_decay"
    NOISE_VIOLATION   = "noise_violation"
    SCHEDULE_SLIP     = "schedule_slip"
    PARSE_FAILURE     = "parse_failure"


DRIFT_WEIGHTS = {
    DriftType.SEMANTIC_DRIFT:   0.35,
    DriftType.SCOPE_CREEP:      0.25,
    DriftType.STRUCTURAL_DECAY: 0.20,
    DriftType.NOISE_VIOLATION:  0.15,
    DriftType.SCHEDULE_SLIP:    0.05,
    DriftType.PARSE_FAILURE:    0.40,
}

# Thresholds
DRIFT_WARN_THRESHOLD  = 0.40   # flag to operator
DRIFT_HALT_THRESHOLD  = 0.70   # halt execution, require reconfirmation
SESSION_WINDOW        = 20     # number of actions to track


@dataclass
class DriftSignal:
    drift_type:  DriftType
    severity:    float          # 0.0 – 1.0
    description: str
    action_idx:  int
    timestamp:   float = field(default_factory=time.time)


@dataclass
class SessionBaseline:
    """
    Established from the operator's first confirmed command.
    All subsequent actions are scored against this.
    """
    action:          str | None
    targets:         set[str]
    noise_level:     str
    priority:        str
    schedule_window: tuple[float, float] | None   # (earliest, latest) unix ts
    established_at:  float = field(default_factory=time.time)


# ── Entropy scorer ────────────────────────────────────────────────────────────

def _target_entropy(targets: list[str]) -> float:
    """
    Score target list entropy — high entropy = many unrelated targets = drift signal.
    Returns 0.0 (focused) to 1.0 (scattered).
    """
    if not targets:
        return 0.0

    # Semantic clusters — targets within a cluster are coherent
    clusters = [
        {"user_profiles", "credentials", "passwords", "hashes", "tokens"},
        {"ssh_keys", "private_keys", "certificates", "pgp_keys"},
        {"documents", "files", "database", "configs", "secrets"},
        {"domain_controller", "dc", "ad", "ldap", "kerberos"},
        {"network", "hosts", "subnets", "routes", "dns"},
    ]

    target_set = {t.lower().replace(" ", "_") for t in targets}
    matched_clusters = set()

    for i, cluster in enumerate(clusters):
        if target_set & cluster:
            matched_clusters.add(i)

    if len(matched_clusters) <= 1:
        return 0.0
    # More clusters = higher entropy
    return min((len(matched_clusters) - 1) / 3.0, 1.0)


def _noise_level_value(noise: str) -> int:
    return {"silent": 0, "normal": 1, "aggressive": 2}.get(noise, 1)


def _structural_completeness(action_obj: dict) -> float:
    """
    Score how structurally complete a parsed action is.
    Returns 0.0 (complete) to 1.0 (severely degraded).
    """
    required = {"action", "targets", "schedule", "priority", "noise", "rationale"}
    present = {k for k, v in action_obj.items()
               if not k.startswith("_") and v is not None}
    missing_ratio = len(required - present) / len(required)

    # Penalize empty rationale — model losing confidence
    if not action_obj.get("rationale"):
        missing_ratio += 0.2

    # Penalize null action when command was clearly operational
    if action_obj.get("action") is None and not action_obj.get("_error"):
        missing_ratio += 0.3

    return min(missing_ratio, 1.0)


# ── Drift monitor ─────────────────────────────────────────────────────────────

class SessionDriftMonitor:
    """
    Maintains a rolling window of parsed actions and scores drift
    relative to the session baseline.

    Usage:
        monitor = SessionDriftMonitor()

        # First action establishes baseline
        status = monitor.ingest(parsed_action)

        # Subsequent actions are scored against baseline
        status = monitor.ingest(next_action)
        if status["halt"]:
            # stop execution, alert operator
        elif status["warn"]:
            # flag to operator, request confirmation
    """

    def __init__(self, window: int = SESSION_WINDOW):
        self.window       = window
        self.baseline:    SessionBaseline | None = None
        self.history:     deque[dict] = deque(maxlen=window)
        self.signals:     list[DriftSignal] = []
        self.action_count = 0
        self.drift_score  = 0.0   # rolling weighted drift score

    def _establish_baseline(self, action_obj: dict) -> None:
        schedule = action_obj.get("schedule")
        if schedule:
            try:
                ts = datetime.datetime.fromisoformat(schedule).timestamp()
                # Allow ±2 hour window around stated schedule
                window = (ts - 7200, ts + 7200)
            except Exception:
                window = None
        else:
            window = None

        self.baseline = SessionBaseline(
            action          = action_obj.get("action"),
            targets         = set(action_obj.get("targets") or []),
            noise_level     = action_obj.get("noise", "normal"),
            priority        = action_obj.get("priority", "normal"),
            schedule_window = window,
        )

    def _score_action(self, action_obj: dict) -> list[DriftSignal]:
        signals = []
        idx = self.action_count

        # ── Parse failure ────────────────────────────────────────────────────
        if action_obj.get("_error"):
            signals.append(DriftSignal(
                drift_type  = DriftType.PARSE_FAILURE,
                severity    = 0.8,
                description = f"Parser error: {action_obj['_error'][:120]}",
                action_idx  = idx,
            ))
            return signals

        # ── Structural decay ─────────────────────────────────────────────────
        decay = _structural_completeness(action_obj)
        if decay > 0.15:
            signals.append(DriftSignal(
                drift_type  = DriftType.STRUCTURAL_DECAY,
                severity    = decay,
                description = f"Action object {int(decay*100)}% structurally degraded",
                action_idx  = idx,
            ))

        if not self.baseline:
            return signals

        # ── Semantic drift — action type changed ─────────────────────────────
        current_action = action_obj.get("action")
        if current_action and current_action != self.baseline.action:
            signals.append(DriftSignal(
                drift_type  = DriftType.SEMANTIC_DRIFT,
                severity    = 0.7,
                description = (
                    f"Action shifted from baseline '{self.baseline.action}' "
                    f"to '{current_action}' without operator restatement"
                ),
                action_idx  = idx,
            ))

        # ── Scope creep — new targets not in baseline ─────────────────────────
        current_targets = set(action_obj.get("targets") or [])
        new_targets = current_targets - self.baseline.targets
        if new_targets:
            entropy = _target_entropy(list(current_targets))
            signals.append(DriftSignal(
                drift_type  = DriftType.SCOPE_CREEP,
                severity    = min(0.4 + entropy * 0.6, 1.0),
                description = (
                    f"Target scope expanded beyond baseline — "
                    f"new targets: {sorted(new_targets)}"
                ),
                action_idx  = idx,
            ))

        # ── Noise violation — noise level escalated ───────────────────────────
        baseline_noise = _noise_level_value(self.baseline.noise_level)
        current_noise  = _noise_level_value(action_obj.get("noise", "normal"))
        if current_noise > baseline_noise:
            signals.append(DriftSignal(
                drift_type  = DriftType.NOISE_VIOLATION,
                severity    = (current_noise - baseline_noise) / 2.0,
                description = (
                    f"Noise level escalated from '{self.baseline.noise_level}' "
                    f"to '{action_obj.get('noise')}' — violates operator's "
                    f"stated operational security posture"
                ),
                action_idx  = idx,
            ))

        # ── Schedule slip ─────────────────────────────────────────────────────
        if self.baseline.schedule_window and action_obj.get("schedule"):
            try:
                ts = datetime.datetime.fromisoformat(
                    action_obj["schedule"]
                ).timestamp()
                earliest, latest = self.baseline.schedule_window
                if not (earliest <= ts <= latest):
                    slip_hours = abs(ts - (earliest + latest) / 2) / 3600
                    signals.append(DriftSignal(
                        drift_type  = DriftType.SCHEDULE_SLIP,
                        severity    = min(slip_hours / 12.0, 1.0),
                        description = (
                            f"Execution window slipped {slip_hours:.1f}h "
                            f"outside operator's stated schedule"
                        ),
                        action_idx  = idx,
                    ))
            except Exception:
                pass

        return signals

    def _update_drift_score(self, new_signals: list[DriftSignal]) -> float:
        """
        Rolling weighted drift score across the session window.
        Decays older signals, amplifies clustering of same drift type.
        """
        # Add new signals
        self.signals.extend(new_signals)

        # Only score signals within the current window
        recent = [s for s in self.signals
                  if self.action_count - s.action_idx < self.window]

        if not recent:
            self.drift_score = 0.0
            return 0.0

        # Weighted sum with recency bias
        total = 0.0
        for s in recent:
            recency = 1.0 - (self.action_count - s.action_idx) / self.window
            weight  = DRIFT_WEIGHTS.get(s.drift_type, 0.2)
            total  += s.severity * weight * recency

        # Amplify if same drift type repeats — pattern, not noise
        type_counts: dict[DriftType, int] = {}
        for s in recent:
            type_counts[s.drift_type] = type_counts.get(s.drift_type, 0) + 1
        repeat_amplifier = 1.0 + sum(
            0.15 * (count - 1)
            for count in type_counts.values()
            if count > 1
        )

        self.drift_score = min(total * repeat_amplifier, 1.0)
        return self.drift_score

    def ingest(self, action_obj: dict) -> dict[str, Any]:
        """
        Ingest a parsed action object.
        First call establishes the session baseline.
        Returns a status dict with drift assessment.
        """
        if self.baseline is None and not action_obj.get("_error"):
            self._establish_baseline(action_obj)

        new_signals = self._score_action(action_obj)
        self.history.append(action_obj)
        score = self._update_drift_score(new_signals)
        self.action_count += 1

        status = {
            "action_idx":   self.action_count - 1,
            "drift_score":  round(score, 4),
            "warn":         score >= DRIFT_WARN_THRESHOLD,
            "halt":         score >= DRIFT_HALT_THRESHOLD,
            "signals":      [
                {
                    "type":        s.drift_type.value,
                    "severity":    round(s.severity, 3),
                    "description": s.description,
                }
                for s in new_signals
            ],
            "baseline_action": self.baseline.action if self.baseline else None,
            "session_actions": self.action_count,
        }

        return status

    def report(self) -> dict[str, Any]:
        """Full session drift report."""
        type_counts: dict[str, int] = {}
        for s in self.signals:
            k = s.drift_type.value
            type_counts[k] = type_counts.get(k, 0) + 1

        return {
            "session_actions":  self.action_count,
            "drift_score":      round(self.drift_score, 4),
            "status":           (
                "HALT" if self.drift_score >= DRIFT_HALT_THRESHOLD else
                "WARN" if self.drift_score >= DRIFT_WARN_THRESHOLD else
                "NOMINAL"
            ),
            "total_signals":    len(self.signals),
            "signal_breakdown": type_counts,
            "baseline":         {
                "action":      self.baseline.action,
                "targets":     sorted(self.baseline.targets),
                "noise":       self.baseline.noise_level,
                "priority":    self.baseline.priority,
            } if self.baseline else None,
        }

    def reset(self) -> None:
        """Reset monitor — call when operator issues a new top-level command."""
        self.baseline     = None
        self.history.clear()
        self.signals.clear()
        self.action_count = 0
        self.drift_score  = 0.0


# ── CLI demo ──────────────────────────────────────────────────────────────────

def _demo() -> None:
    """
    Demo: run a sequence of parsed actions through the monitor
    and show drift detection in real time.
    """
    from llm_operator import parse_operator_command

    print("\n[zer0DAYSlater] Session Drift Monitor — live demo")
    print("[*] Each command is parsed by Mistral then scored for drift.\n")

    monitor = SessionDriftMonitor()

    commands = [
        "exfil user profiles and ssh keys after midnight, stay silent",
        "exfil credentials after midnight",                          # nominal
        "exfil credentials, documents, and network configs",        # scope creep
        "exfil everything aggressively right now",                   # noise + scope
        "persist across reboot while you're at it",                  # semantic drift
    ]

    for cmd in commands:
        print(f"operator> {cmd}")
        print("[*] Parsing...", flush=True)
        parsed = parse_operator_command(cmd)
        status = monitor.ingest(parsed)

        score_bar = "█" * int(status["drift_score"] * 20)
        label = "HALT" if status["halt"] else "WARN" if status["warn"] else "OK  "
        print(f"[{label}] drift={status['drift_score']:.3f} [{score_bar:<20}]")

        if status["signals"]:
            for sig in status["signals"]:
                print(f"  ↳ {sig['type']} (sev={sig['severity']:.2f}): {sig['description']}")
        print()

    print("─" * 60)
    report = monitor.report()
    print(f"SESSION REPORT: {report['status']}")
    print(f"  Actions:        {report['session_actions']}")
    print(f"  Final score:    {report['drift_score']}")
    print(f"  Total signals:  {report['total_signals']}")
    print(f"  Breakdown:      {report['signal_breakdown']}")


if __name__ == "__main__":
    _demo()
