#!/usr/bin/env python3
"""
zer0DAYSlater — Payload Mutator

Feedback-driven payload mutation engine. Selects and evolves payloads
based on channel feedback, behavioral profiles, and operational context.

Inspired by the chain mutation engine (github.com/GnomeMan4201/chain),
rebuilt here as a clean typed API integrated with the zer0DAYSlater
operator pipeline.

Core concept: payloads have personalities. Personalities have fitness scores.
Fitness is updated by channel feedback. The mutator selects the highest-fitness
personality for the current context, then mutates it based on what failed.

Mutation operators:
  - ROTATE    — switch to a different personality entirely
  - MORPH     — modify encoding/obfuscation of current payload
  - FRAGMENT  — split payload into smaller delivery chunks
  - DELAY     — add jitter and timing randomization
  - DECOY     — prepend benign-looking header to mask intent
"""
from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Personality definitions ───────────────────────────────────────────────────

class Personality(str, Enum):
    SCOUT     = "scout"       # lightweight recon — minimal footprint
    GHOST     = "ghost"       # stealth-first — slow, silent, persistent
    LEECH     = "leech"       # data collection — focused exfil
    PHANTOM   = "phantom"     # evasion-heavy — detection avoidance priority
    PARASITE  = "parasite"    # persistence — survives across sessions
    SURGEON   = "surgeon"     # precision — targeted single-objective ops


# Default fitness scores per personality
_BASE_FITNESS: dict[Personality, float] = {
    Personality.SCOUT:    0.60,
    Personality.GHOST:    0.55,
    Personality.LEECH:    0.65,
    Personality.PHANTOM:  0.50,
    Personality.PARASITE: 0.55,
    Personality.SURGEON:  0.70,
}

# Action → personality affinity mapping
_ACTION_AFFINITY: dict[str, list[Personality]] = {
    "exfil":   [Personality.LEECH,    Personality.GHOST,   Personality.SURGEON],
    "persist": [Personality.PARASITE, Personality.GHOST,   Personality.PHANTOM],
    "lateral": [Personality.SCOUT,    Personality.PHANTOM, Personality.SURGEON],
    "cloak":   [Personality.PHANTOM,  Personality.GHOST,   Personality.PARASITE],
    "recon":   [Personality.SCOUT,    Personality.SURGEON, Personality.GHOST],
}

# Noise level → personality constraints
_NOISE_CONSTRAINTS: dict[str, set[Personality]] = {
    "silent":     {Personality.GHOST, Personality.PHANTOM, Personality.SURGEON},
    "normal":     {Personality.SCOUT, Personality.LEECH, Personality.GHOST,
                   Personality.PHANTOM, Personality.PARASITE, Personality.SURGEON},
    "aggressive": {Personality.SCOUT, Personality.LEECH, Personality.PARASITE},
}


# ── Mutation operators ────────────────────────────────────────────────────────

class MutationOp(str, Enum):
    ROTATE   = "rotate"    # switch personality
    MORPH    = "morph"     # re-encode/obfuscate
    FRAGMENT = "fragment"  # chunk delivery
    DELAY    = "delay"     # add timing jitter
    DECOY    = "decoy"     # prepend cover traffic


@dataclass
class MutationResult:
    personality:    Personality
    mutation_ops:   list[MutationOp]
    payload_hash:   str             # fingerprint of this mutation
    fitness_score:  float
    generation:     int
    rationale:      str
    metadata:       dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelFeedback:
    """
    Feedback from a channel attempt.
    Fed back into the mutator to update fitness scores.
    """
    payload_hash:   str
    success:        bool
    detected:       bool            # was detection triggered?
    channel:        str             # which C2 channel was used
    latency_ms:     float           # response latency
    error:          str | None = None


# ── Mutation memory ───────────────────────────────────────────────────────────

class MutationMemory:
    """
    Tracks payload performance across the session.
    Updates personality fitness based on channel feedback.
    Prevents repeat mutations that have already failed.
    """

    def __init__(self) -> None:
        self.fitness:     dict[Personality, float] = dict(_BASE_FITNESS)
        self.history:     list[dict[str, Any]]     = []
        self.failed_ops:  set[str]                 = set()  # hash:op combos
        self.generation:  int                      = 0

    def update(self, feedback: ChannelFeedback) -> None:
        """Update fitness based on channel feedback."""
        # Find which personality produced this hash
        for entry in reversed(self.history):
            if entry["payload_hash"] == feedback.payload_hash:
                p = Personality(entry["personality"])

                if feedback.success and not feedback.detected:
                    # Success — boost fitness
                    self.fitness[p] = min(self.fitness[p] + 0.08, 1.0)
                elif feedback.detected:
                    # Detected — significant penalty
                    self.fitness[p] = max(self.fitness[p] - 0.20, 0.0)
                    # Mark this op as failed for this hash
                    for op in entry["mutation_ops"]:
                        self.failed_ops.add(f"{feedback.payload_hash}:{op}")
                else:
                    # Failed but not detected — minor penalty
                    self.fitness[p] = max(self.fitness[p] - 0.05, 0.0)
                break

        self.history.append({
            "feedback":     feedback.__dict__,
            "fitness_snapshot": dict(self.fitness),
            "timestamp":    time.time(),
        })

    def best_personality(
        self,
        action: str | None,
        noise: str,
    ) -> Personality:
        """Select highest-fitness personality for given action and noise level."""
        candidates = list(Personality)

        # Filter by action affinity
        if action and action in _ACTION_AFFINITY:
            affinity = _ACTION_AFFINITY[action]
            # Prefer affinity candidates but don't exclude others entirely
            candidates = affinity + [p for p in candidates if p not in affinity]

        # Filter by noise constraint
        allowed = _NOISE_CONSTRAINTS.get(noise, set(Personality))
        candidates = [p for p in candidates if p in allowed] or candidates

        # Sort by fitness
        candidates.sort(key=lambda p: self.fitness[p], reverse=True)
        return candidates[0]

    def select_mutation_ops(
        self,
        personality: Personality,
        noise: str,
        entropy_score: float = 0.0,
    ) -> list[MutationOp]:
        """
        Select mutation operators based on personality, noise, and
        current session entropy. High entropy = more aggressive mutation.
        """
        ops: list[MutationOp] = []

        # Base ops by noise level
        if noise == "silent":
            ops.append(MutationOp.DELAY)
            ops.append(MutationOp.MORPH)
        elif noise == "normal":
            ops.append(MutationOp.MORPH)
        else:  # aggressive
            ops.append(MutationOp.FRAGMENT)

        # Personality-specific ops
        if personality == Personality.PHANTOM:
            ops.append(MutationOp.DECOY)
        elif personality == Personality.GHOST:
            ops.append(MutationOp.DELAY)
            if MutationOp.MORPH not in ops:
                ops.append(MutationOp.MORPH)
        elif personality == Personality.SCOUT:
            # Minimal ops — scout is lightweight
            ops = [MutationOp.MORPH]

        # High entropy — add rotation to try a different approach
        if entropy_score > 0.55 and MutationOp.ROTATE not in ops:
            ops.append(MutationOp.ROTATE)

        return list(dict.fromkeys(ops))   # deduplicate preserving order

    def record(self, result: MutationResult) -> None:
        self.history.append({
            "generation":    result.generation,
            "personality":   result.personality.value,
            "mutation_ops":  [op.value for op in result.mutation_ops],
            "payload_hash":  result.payload_hash,
            "fitness_score": result.fitness_score,
            "timestamp":     time.time(),
        })
        self.generation += 1


# ── Payload mutator ───────────────────────────────────────────────────────────

class PayloadMutator:
    """
    Main mutation engine. Integrates with the operator pipeline:

        parsed_action = parse_operator_command(cmd)
        drift_status  = drift_monitor.ingest(parsed_action)
        entropy_sigs  = entropy_engine.ingest(parsed_action, cmd)

        mutation = mutator.mutate(
            action_obj     = parsed_action,
            entropy_score  = entropy_engine.current_entropy(),
            drift_score    = drift_monitor.drift_score,
        )

        # After channel attempt:
        mutator.feedback(ChannelFeedback(...))
    """

    def __init__(self) -> None:
        self.memory = MutationMemory()

    def mutate(
        self,
        action_obj:    dict[str, Any],
        entropy_score: float = 0.0,
        drift_score:   float = 0.0,
    ) -> MutationResult:
        """
        Produce a mutation result for the given action object.
        Selects personality and operators based on context and fitness history.
        """
        action = action_obj.get("action")
        noise  = action_obj.get("noise") or "normal"

        # Select best personality
        personality = self.memory.best_personality(action, noise)

        # Select mutation operators
        ops = self.memory.select_mutation_ops(personality, noise, entropy_score)

        # If both drift and entropy are high — force rotation
        if drift_score > 0.55 and entropy_score > 0.45:
            if MutationOp.ROTATE not in ops:
                ops.insert(0, MutationOp.ROTATE)
            # Rotate to next best personality
            current_idx = list(Personality).index(personality)
            next_idx    = (current_idx + 1) % len(Personality)
            personality = list(Personality)[next_idx]

        # Generate payload fingerprint
        fingerprint_data = (
            f"{personality.value}:"
            f"{','.join(op.value for op in ops)}:"
            f"{action}:{noise}:"
            f"{self.memory.generation}"
        )
        payload_hash = hashlib.sha256(
            fingerprint_data.encode()
        ).hexdigest()[:16]

        fitness = self.memory.fitness[personality]

        rationale = self._build_rationale(
            personality, ops, action, noise, entropy_score, drift_score
        )

        result = MutationResult(
            personality   = personality,
            mutation_ops  = ops,
            payload_hash  = payload_hash,
            fitness_score = fitness,
            generation    = self.memory.generation,
            rationale     = rationale,
            metadata      = {
                "action":        action,
                "noise":         noise,
                "entropy_score": round(entropy_score, 4),
                "drift_score":   round(drift_score, 4),
            },
        )

        self.memory.record(result)
        return result

    def feedback(self, fb: ChannelFeedback) -> None:
        """Feed channel result back into the mutation memory."""
        self.memory.update(fb)

    def _build_rationale(
        self,
        personality:   Personality,
        ops:           list[MutationOp],
        action:        str | None,
        noise:         str,
        entropy_score: float,
        drift_score:   float,
    ) -> str:
        parts = [f"Personality: {personality.value}"]
        parts.append(f"Ops: {', '.join(op.value for op in ops)}")
        parts.append(f"Fitness: {self.memory.fitness[personality]:.2f}")
        if entropy_score > 0.40:
            parts.append(f"High entropy ({entropy_score:.2f}) — increased mutation pressure")
        if drift_score > 0.40:
            parts.append(f"Drift detected ({drift_score:.2f}) — rotation considered")
        return " | ".join(parts)

    def fitness_report(self) -> dict[str, float]:
        """Current fitness scores for all personalities."""
        return {p.value: round(v, 4) for p, v in self.memory.fitness.items()}

    def generation_report(self) -> list[dict[str, Any]]:
        """Full mutation history."""
        return self.memory.history


# ── CLI demo ──────────────────────────────────────────────────────────────────

def _demo() -> None:
    print("\n[zer0DAYSlater] Payload Mutator — demo")
    print("[*] Simulating mutation across a campaign session.\n")

    mutator = PayloadMutator()

    # Simulate a campaign sequence with feedback
    scenarios = [
        # (action_obj, feedback_success, feedback_detected, channel)
        ({"action": "exfil",   "noise": "silent",     "targets": ["credentials"]}, True,  False, "HTTPS"),
        ({"action": "exfil",   "noise": "silent",     "targets": ["ssh_keys"]},    False, True,  "DNS"),
        ({"action": "persist", "noise": "silent",     "targets": []},              True,  False, "WS"),
        ({"action": "lateral", "noise": "normal",     "targets": ["dc"]},          False, False, "HTTPS"),
        ({"action": "cloak",   "noise": "silent",     "targets": []},              True,  False, "WS"),
        ({"action": "exfil",   "noise": "aggressive", "targets": ["everything"]},  False, True,  "DNS"),
    ]

    for i, (action_obj, success, detected, channel) in enumerate(scenarios):
        result = mutator.mutate(action_obj, entropy_score=i * 0.08, drift_score=i * 0.06)

        status = "✓" if success else "✗"
        detect = " [DETECTED]" if detected else ""
        print(f"[Gen {result.generation}] {result.personality.value:<10} "
              f"ops={[op.value for op in result.mutation_ops]} "
              f"fitness={result.fitness_score:.2f} "
              f"hash={result.payload_hash}")
        print(f"         {status} {channel}{detect}")

        # Feed back result
        mutator.feedback(ChannelFeedback(
            payload_hash = result.payload_hash,
            success      = success,
            detected     = detected,
            channel      = channel,
            latency_ms   = random.uniform(50, 800),
        ))

    print(f"\n── Fitness after campaign ──")
    for personality, fitness in mutator.fitness_report().items():
        bar = "█" * int(fitness * 20)
        print(f"  {personality:<12} {fitness:.2f} {bar}")


if __name__ == "__main__":
    _demo()
