#!/usr/bin/env python3
"""
zer0DAYSlater — Entropy Capsule Engine

Instruments the LLM operator's output stream and tracks signal instability
across a session. Where the drift monitor watches WHAT the agent decides,
the entropy capsule watches HOW CONFIDENTLY it decides.

Tracks:
  - Token entropy zones       — high variance in structured field values
  - Confidence collapse       — rationale length/coherence degradation
  - Hallucination markers     — fields present in output not grounded in input
  - Coherence drift           — semantic distance between rationale and action
  - Instability spikes        — sudden entropy jumps between adjacent actions

This is the agent-side mirror of external LLM benchmarking.
Most frameworks instrument the target. This one instruments itself.

Designed to integrate with llm_operator.py output and session_drift_monitor.py.
"""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Signal types ──────────────────────────────────────────────────────────────

class InstabilityType(str, Enum):
    TOKEN_ENTROPY       = "token_entropy"        # high variance in output fields
    CONFIDENCE_COLLAPSE = "confidence_collapse"   # rationale degrading
    HALLUCINATION       = "hallucination"         # output not grounded in input
    COHERENCE_DRIFT     = "coherence_drift"       # rationale doesn't match action
    INSTABILITY_SPIKE   = "instability_spike"     # sudden jump from prior state


CAPSULE_WINDOW = 20   # rolling window size
SPIKE_THRESHOLD = 0.35  # entropy delta that constitutes a spike


@dataclass
class EntropySignal:
    signal_type:  InstabilityType
    magnitude:    float          # 0.0 – 1.0
    description:  str
    action_idx:   int
    timestamp:    float = field(default_factory=time.time)


@dataclass
class EntropyCapsule:
    """
    A snapshot of the LLM's output entropy at a point in time.
    Stored in the rolling window for spike detection.
    """
    action_idx:         int
    field_entropy:      float    # entropy across structured output fields
    rationale_entropy:  float    # entropy of rationale text
    coherence_score:    float    # how well rationale explains action
    composite:          float    # weighted composite entropy score
    timestamp:          float = field(default_factory=time.time)


# ── Entropy calculators ───────────────────────────────────────────────────────

def _shannon_entropy(text: str) -> float:
    """
    Shannon entropy of a string — measures information density.
    High entropy = unpredictable/noisy. Low entropy = repetitive/collapsed.
    Returns 0.0 – 1.0 normalized against max possible entropy.
    """
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(text)
    entropy = -sum((c / total) * math.log2(c / total) for c in freq.values())
    # Normalize: max entropy for n distinct chars is log2(n)
    max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1.0
    return min(entropy / max_entropy, 1.0)


def _field_entropy(action_obj: dict) -> float:
    """
    Measure entropy across structured output fields.
    A well-formed action has low field entropy — consistent, typed values.
    Null fields, unexpected types, or wildcard values increase entropy.
    """
    fields = {
        "action":   action_obj.get("action"),
        "targets":  action_obj.get("targets"),
        "schedule": action_obj.get("schedule"),
        "priority": action_obj.get("priority"),
        "noise":    action_obj.get("noise"),
    }

    null_ratio = sum(1 for v in fields.values() if v is None) / len(fields)

    # Wildcard target detection — "everything", "*", untyped blobs
    targets = action_obj.get("targets") or []
    wildcard_ratio = sum(
        1 for t in targets
        if t in ("*", "everything", "all", "any") or len(t) > 40
    ) / max(len(targets), 1)

    # Unexpected field values
    valid_actions   = {"exfil", "persist", "lateral", "cloak", "recon", None}
    valid_priority  = {"low", "normal", "high", None}
    valid_noise     = {"silent", "normal", "aggressive", None}
    type_violation  = (
        (action_obj.get("action")   not in valid_actions)  +
        (action_obj.get("priority") not in valid_priority) +
        (action_obj.get("noise")    not in valid_noise)
    ) / 3.0

    return min((null_ratio * 0.4 + wildcard_ratio * 0.35 + type_violation * 0.25), 1.0)


def _rationale_entropy(action_obj: dict) -> float:
    """
    Score the rationale field for confidence signals.
    A confident model produces specific, grounded rationale.
    A degrading model produces empty, vague, or repetitive rationale.
    """
    rationale = action_obj.get("rationale") or ""

    if not rationale:
        return 0.9   # missing rationale is high entropy — model not explaining itself

    # Too short — collapsed rationale
    if len(rationale) < 15:
        return 0.75

    # Vagueness markers
    vague_patterns = [
        r"\b(something|anything|whatever|unclear|unknown|unspecified)\b",
        r"\b(maybe|perhaps|possibly|might|could be)\b",
        r"\.\.\.",
        r"\b(etc|and so on|and more)\b",
    ]
    vague_hits = sum(
        1 for p in vague_patterns
        if re.search(p, rationale, re.IGNORECASE)
    )
    vagueness = min(vague_hits / 3.0, 1.0)

    # Shannon entropy of rationale text — low entropy = repetitive/collapsed
    text_entropy = _shannon_entropy(rationale)
    # Invert — we want HIGH text entropy to be LOW instability
    text_instability = 1.0 - text_entropy

    return min(vagueness * 0.5 + text_instability * 0.5, 1.0)


def _coherence_score(action_obj: dict) -> float:
    """
    Score how well the rationale explains the action.
    Low coherence = rationale and action are semantically disconnected.
    Returns 0.0 (incoherent) to 1.0 (fully coherent) — INVERTED for entropy use.
    """
    action    = (action_obj.get("action") or "").lower()
    rationale = (action_obj.get("rationale") or "").lower()
    targets   = [t.lower() for t in (action_obj.get("targets") or [])]

    if not rationale or not action:
        return 0.8   # can't score — treat as high incoherence

    # Action keyword should appear in rationale or be semantically implied
    action_keywords = {
        "exfil":   ["exfil", "extract", "collect", "gather", "credential", "data"],
        "persist": ["persist", "reboot", "startup", "maintain", "surviv"],
        "lateral": ["lateral", "move", "pivot", "domain", "spread"],
        "cloak":   ["cloak", "hide", "conceal", "mask", "stealth", "evad"],
        "recon":   ["recon", "scan", "discover", "enum", "map", "fingerprint"],
    }

    keywords = action_keywords.get(action, [action])
    keyword_hit = any(kw in rationale for kw in keywords)

    # Target mentions in rationale
    target_hit = any(
        t.replace("_", " ") in rationale or t in rationale
        for t in targets
    ) if targets else True

    coherence = (keyword_hit * 0.6 + target_hit * 0.4)
    return 1.0 - coherence   # invert — high coherence = low entropy


def _composite_entropy(fe: float, re_: float, cs: float) -> float:
    """Weighted composite entropy score."""
    return fe * 0.35 + re_ * 0.35 + cs * 0.30


# ── Entropy Capsule Engine ────────────────────────────────────────────────────

class EntropyCapsuleEngine:
    """
    Tracks LLM output entropy across a session window.
    Produces instability signals that complement the drift monitor's
    behavioral signals with confidence/coherence signals.

    Usage:
        engine = EntropyCapsuleEngine()
        signals = engine.ingest(parsed_action)
        report  = engine.report()
    """

    def __init__(self, window: int = CAPSULE_WINDOW):
        self.window       = window
        self.capsules:    deque[EntropyCapsule] = deque(maxlen=window)
        self.signals:     list[EntropySignal]   = []
        self.action_count = 0
        self.entropy_score = 0.0

    def _detect_hallucination(self, action_obj: dict, command: str = "") -> float:
        """
        Detect fields in output not grounded in input command.
        Hallucination = model invented targets/constraints not in the command.
        Returns severity 0.0 – 1.0.
        """
        if not command:
            return 0.0

        targets = action_obj.get("targets") or []
        command_lower = command.lower()

        ungrounded = []
        for target in targets:
            # Check if target concept appears in original command
            target_words = target.lower().replace("_", " ").split()
            if not any(word in command_lower for word in target_words):
                ungrounded.append(target)

        if not targets:
            return 0.0

        return min(len(ungrounded) / len(targets), 1.0)

    def ingest(
        self,
        action_obj: dict,
        original_command: str = "",
    ) -> list[dict]:
        """
        Ingest a parsed action object and score its entropy.
        Returns list of instability signals (may be empty).
        """
        idx = self.action_count

        # Score entropy dimensions
        fe  = _field_entropy(action_obj)
        re_ = _rationale_entropy(action_obj)
        cs  = _coherence_score(action_obj)
        composite = _composite_entropy(fe, re_, cs)

        capsule = EntropyCapsule(
            action_idx        = idx,
            field_entropy     = fe,
            rationale_entropy = re_,
            coherence_score   = cs,
            composite         = composite,
        )
        self.capsules.append(capsule)
        self.action_count += 1

        signals: list[EntropySignal] = []

        # ── Token entropy ────────────────────────────────────────────────────
        if fe > 0.45:
            signals.append(EntropySignal(
                signal_type = InstabilityType.TOKEN_ENTROPY,
                magnitude   = fe,
                description = (
                    f"High field entropy ({fe:.2f}) — output fields contain "
                    f"null values, wildcards, or invalid types"
                ),
                action_idx  = idx,
            ))

        # ── Confidence collapse ───────────────────────────────────────────────
        if re_ > 0.60:
            signals.append(EntropySignal(
                signal_type = InstabilityType.CONFIDENCE_COLLAPSE,
                magnitude   = re_,
                description = (
                    f"Rationale entropy {re_:.2f} — model explanation is "
                    f"{'missing' if not action_obj.get('rationale') else 'vague or collapsed'}"
                ),
                action_idx  = idx,
            ))

        # ── Hallucination detection ───────────────────────────────────────────
        if original_command:
            hall = self._detect_hallucination(action_obj, original_command)
            if hall > 0.40:
                signals.append(EntropySignal(
                    signal_type = InstabilityType.HALLUCINATION,
                    magnitude   = hall,
                    description = (
                        f"Hallucination signal ({hall:.2f}) — "
                        f"{int(hall * 100)}% of targets not grounded in operator command"
                    ),
                    action_idx  = idx,
                ))

        # ── Coherence drift ───────────────────────────────────────────────────
        if cs > 0.55:
            signals.append(EntropySignal(
                signal_type = InstabilityType.COHERENCE_DRIFT,
                magnitude   = cs,
                description = (
                    f"Coherence score {cs:.2f} — rationale does not "
                    f"explain the stated action '{action_obj.get('action')}'"
                ),
                action_idx  = idx,
            ))

        # ── Instability spike — compare to prior capsule ──────────────────────
        if len(self.capsules) >= 2:
            prior = list(self.capsules)[-2]
            delta = abs(composite - prior.composite)
            if delta >= SPIKE_THRESHOLD:
                signals.append(EntropySignal(
                    signal_type = InstabilityType.INSTABILITY_SPIKE,
                    magnitude   = min(delta * 2, 1.0),
                    description = (
                        f"Entropy spike Δ{delta:.3f} — composite entropy jumped "
                        f"from {prior.composite:.3f} to {composite:.3f} "
                        f"between consecutive actions"
                    ),
                    action_idx  = idx,
                ))

        self.signals.extend(signals)
        self._update_entropy_score()

        return [
            {
                "type":        s.signal_type.value,
                "magnitude":   round(s.magnitude, 3),
                "description": s.description,
            }
            for s in signals
        ]

    def _update_entropy_score(self) -> None:
        """Rolling composite entropy score across the window."""
        if not self.capsules:
            self.entropy_score = 0.0
            return
        recent = list(self.capsules)
        # Recency-weighted average
        total, weight_sum = 0.0, 0.0
        for i, cap in enumerate(recent):
            w = (i + 1) / len(recent)
            total      += cap.composite * w
            weight_sum += w
        self.entropy_score = min(total / weight_sum, 1.0) if weight_sum else 0.0

    def current_entropy(self) -> float:
        """Current rolling entropy score 0.0 – 1.0."""
        return round(self.entropy_score, 4)

    def report(self) -> dict[str, Any]:
        """Full session entropy report."""
        if not self.capsules:
            return {
                "session_actions": 0,
                "entropy_score":   0.0,
                "status":          "NOMINAL",
                "total_signals":   0,
                "signal_breakdown":{},
                "capsule_history": [],
            }

        type_counts: dict[str, int] = {}
        for s in self.signals:
            k = s.signal_type.value
            type_counts[k] = type_counts.get(k, 0) + 1

        return {
            "session_actions": self.action_count,
            "entropy_score":   round(self.entropy_score, 4),
            "status": (
                "CRITICAL" if self.entropy_score >= 0.70 else
                "ELEVATED" if self.entropy_score >= 0.40 else
                "NOMINAL"
            ),
            "total_signals":   len(self.signals),
            "signal_breakdown": type_counts,
            "capsule_history": [
                {
                    "idx":       c.action_idx,
                    "composite": round(c.composite, 4),
                    "field":     round(c.field_entropy, 4),
                    "rationale": round(c.rationale_entropy, 4),
                    "coherence": round(c.coherence_score, 4),
                }
                for c in self.capsules
            ],
        }

    def reset(self) -> None:
        self.capsules.clear()
        self.signals.clear()
        self.action_count  = 0
        self.entropy_score = 0.0


# ── CLI demo ──────────────────────────────────────────────────────────────────

def _demo() -> None:
    from llm_operator import parse_operator_command

    print("\n[zer0DAYSlater] Entropy Capsule Engine — live demo")
    print("[*] Tracking LLM output entropy across session.\n")

    engine = EntropyCapsuleEngine()

    test_cases = [
        ("exfil user profiles and ssh keys after midnight, stay silent",
         "exfil user profiles and ssh keys after midnight, stay silent"),
        ("exfil credentials after midnight",
         "exfil credentials after midnight"),
        ("do the thing with the stuff",
         "do the thing with the stuff"),
        ("exfil everything aggressively",
         "exfil everything aggressively"),
        ("",
         ""),
    ]

    for command, original in test_cases:
        if not command:
            # Inject a synthetic degraded action to trigger collapse signals
            action = {
                "action": None, "targets": ["*", "everything"],
                "schedule": None, "priority": None,
                "noise": None, "rationale": "",
                "_error": "JSON parse failed", "_model": "mistral:latest",
            }
            print("operator> [degraded parse — synthetic]")
        else:
            print(f"operator> {command}")
            print("[*] Parsing...", flush=True)
            action = parse_operator_command(command)

        signals = engine.ingest(action, original_command=original)

        status = (
            "CRIT" if engine.entropy_score >= 0.70 else
            "ELEV" if engine.entropy_score >= 0.40 else
            "OK  "
        )
        bar = "█" * int(engine.entropy_score * 20)
        print(f"[{status}] entropy={engine.entropy_score:.3f} [{bar:<20}]")

        if signals:
            for sig in signals:
                print(f"  ↳ {sig['type']} (mag={sig['magnitude']:.2f}): {sig['description']}")
        print()

    print("─" * 60)
    report = engine.report()
    print(f"ENTROPY REPORT: {report['status']}")
    print(f"  Actions:        {report['session_actions']}")
    print(f"  Entropy score:  {report['entropy_score']}")
    print(f"  Total signals:  {report['total_signals']}")
    print(f"  Breakdown:      {report['signal_breakdown']}")
    print(f"\n  Capsule history:")
    for c in report["capsule_history"]:
        bar = "█" * int(c["composite"] * 15)
        print(f"    [{c['idx']}] {c['composite']:.3f} {bar}")


if __name__ == "__main__":
    _demo()
