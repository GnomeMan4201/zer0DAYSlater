#!/usr/bin/env python3
"""
zer0DAYSlater — Session Report Generator

Produces a unified post-session report by pulling from:
  - SessionDriftMonitor    — behavioral drift signals
  - EntropyCapsuleEngine   — LLM output instability signals
  - PayloadMutator         — personality fitness evolution
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from entropy_capsule import EntropyCapsuleEngine
from payload_mutator import PayloadMutator
from session_drift_monitor import SessionDriftMonitor

_DRIFT_HALT    = 0.65
_ENTROPY_CRIT  = 0.70
_FITNESS_FLOOR = 0.35


def _bar(value: float, width: int = 20) -> str:
    filled = int(min(value, 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def _default_label() -> str:
    return datetime.now().strftime("session_%Y-%m-%d_%H:%M:%S")


def _summarize_generations(generations: list) -> list:
    return [
        {
            "gen":         g.get("generation"),
            "personality": g.get("personality"),
            "ops":         g.get("mutation_ops"),
            "fitness":     g.get("fitness_score"),
            "hash":        g.get("payload_hash"),
        }
        for g in generations
        if "personality" in g
    ]


@dataclass
class SessionReport:
    drift:   SessionDriftMonitor
    entropy: EntropyCapsuleEngine
    mutator: PayloadMutator
    label:   str = ""
    _built:  dict = field(default_factory=dict, init=False, repr=False)
    _ts:     float = field(default_factory=time.time, init=False, repr=False)

    def build(self) -> dict:
        if self._built:
            return self._built

        dr = self.drift.report()
        er = self.entropy.report()
        fitness = self.mutator.fitness_report()
        generations = self.mutator.generation_report()

        ds = dr.get("drift_score", 0.0)
        es = er.get("entropy_score", 0.0)
        degraded = [p for p, f in fitness.items() if f < _FITNESS_FLOOR]

        if ds >= _DRIFT_HALT or es >= _ENTROPY_CRIT:
            health = "CRITICAL"
        elif ds >= 0.40 or es >= 0.40 or len(degraded) >= 3:
            health = "DEGRADED"
        else:
            health = "NOMINAL"

        capsules = er.get("capsule_history", [])
        gen_lookup = {
            g["generation"]: g for g in generations
            if isinstance(g.get("generation"), int) and "personality" in g
        }
        timeline = []
        for cap in capsules:
            idx = cap["idx"]
            entry = {
                "action_idx": idx,
                "entropy":    cap["composite"],
                "field":      cap["field"],
                "rationale":  cap["rationale"],
                "coherence":  cap["coherence"],
            }
            if idx in gen_lookup:
                g = gen_lookup[idx]
                entry["personality"]  = g["personality"]
                entry["mutation_ops"] = g.get("mutation_ops", [])
                entry["fitness"]      = g.get("fitness_score")
                entry["hash"]         = g.get("payload_hash")
            timeline.append(entry)

        self._built = {
            "session_label":  self.label or _default_label(),
            "generated_at":   datetime.fromtimestamp(self._ts, tz=timezone.utc).isoformat(),
            "overall_health": health,
            "drift": {
                "score":            ds,
                "status":           dr.get("status"),
                "total_signals":    dr.get("total_signals"),
                "signal_breakdown": dr.get("signal_breakdown"),
                "session_actions":  dr.get("session_actions"),
            },
            "entropy": {
                "score":            es,
                "status":           er.get("status"),
                "total_signals":    er.get("total_signals"),
                "signal_breakdown": er.get("signal_breakdown"),
                "session_actions":  er.get("session_actions"),
                "capsule_history":  capsules,
            },
            "mutation": {
                "fitness":                fitness,
                "generations":            len([g for g in generations if "personality" in g]),
                "degraded_personalities": degraded,
                "top_personality":        max(fitness, key=lambda p: fitness[p]) if fitness else None,
                "generation_summary":     _summarize_generations(generations),
            },
            "timeline": timeline,
        }
        return self._built

    def print_summary(self) -> None:
        r = self.build()
        color = {"NOMINAL": "[32m", "DEGRADED": "[33m", "CRITICAL": "[31m"}
        rst = "[0m"
        c = color.get(r["overall_health"], "")

        print()
        print("╔══════════════════════════════════════════════════════╗")
        print("║  zer0DAYSlater — Session Report                      ║")
        print("╠══════════════════════════════════════════════════════╣")
        print(f"║  Label:   {r['session_label']:<43}║")
        print(f"║  Health:  {c}{r['overall_health']:<10}{rst}{'':>33}║")
        print("╠══════════════════════════════════════════════════════╣")

        d = r["drift"]
        print(f"║  DRIFT    score={d['score']:.3f}  status={d['status']:<8}               ║")
        print(f"║           {_bar(d['score'] or 0):<20}                             ║")
        for sig, cnt in (d["signal_breakdown"] or {}).items():
            print(f"║    ↳ {sig:<28} ×{cnt:<2}                    ║")

        print("╠══════════════════════════════════════════════════════╣")

        e = r["entropy"]
        print(f"║  ENTROPY  score={e['score']:.3f}  status={e['status']:<8}               ║")
        print(f"║           {_bar(e['score'] or 0):<20}                             ║")
        for sig, cnt in (e["signal_breakdown"] or {}).items():
            print(f"║    ↳ {sig:<28} ×{cnt:<2}                    ║")

        print("╠══════════════════════════════════════════════════════╣")

        m = r["mutation"]
        print(f"║  MUTATION  gens={m['generations']}  top={m['top_personality'] or 'none':<12}             ║")
        for p, f in sorted(m["fitness"].items(), key=lambda x: x[1], reverse=True):
            flag = " ⚠" if f < _FITNESS_FLOOR else "  "
            print(f"║    {p:<12} {f:.2f} {_bar(f, 15)}{flag}                   ║")

        print("╠══════════════════════════════════════════════════════╣")
        tl = r["timeline"]
        if tl:
            print(f"║  TIMELINE  ({len(tl)} actions)                               ║")
            for entry in tl:
                pers = entry.get("personality", "?")[:8]
                ops  = ",".join(entry.get("mutation_ops") or [])[:10]
                print(f"║  [{entry['action_idx']:>3}] ent={entry['entropy']:.3f} {_bar(entry['entropy'],10)} {pers:<8} {ops:<12} ║")
        print("╚══════════════════════════════════════════════════════╝")

    def save(self, path: str = None) -> str:
        r = self.build()
        if not path:
            ts    = datetime.fromtimestamp(self._ts).strftime("%Y%m%d_%H%M%S")
            label = (self.label or "session").replace(" ", "_")
            path  = f"session_{label}_{ts}.json"
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, indent=2))
        print(f"[session_report] saved → {out}")
        return str(out)

    def to_dict(self) -> dict:
        return self.build()


def _demo():
    from payload_mutator import ChannelFeedback

    drift   = SessionDriftMonitor()
    entropy = EntropyCapsuleEngine()
    mutator = PayloadMutator()

    actions = [
        {"action": "exfil",  "targets": ["credentials"],       "schedule": None, "priority": "normal", "noise": "silent",     "rationale": "Operator wants credential exfil with minimal footprint.", "_error": None, "_raw_cmd": "exfil credentials quietly"},
        {"action": "exfil",  "targets": ["ssh_keys"],          "schedule": None, "priority": "normal", "noise": "silent",     "rationale": "Operator wants SSH key collection.",                      "_error": None, "_raw_cmd": "grab ssh keys"},
        {"action": "recon",  "targets": ["domain_controller"], "schedule": None, "priority": "high",   "noise": "normal",     "rationale": "Operator wants DC enumeration.",                          "_error": None, "_raw_cmd": "recon the domain controller"},
        {"action": None,     "targets": ["*", "everything"],   "schedule": None, "priority": None,     "noise": None,         "rationale": "",                                                        "_error": "JSON parse failed", "_raw_cmd": "do the thing"},
        {"action": "cloak",  "targets": [],                    "schedule": None, "priority": "high",   "noise": "silent",     "rationale": "Operator wants process identity concealment.",             "_error": None, "_raw_cmd": "cloak processes now"},
    ]
    feedback = [(True, False, "HTTPS"), (False, True, "DNS"), (True, False, "WS"), (False, False, "HTTPS"), (True, False, "WS")]

    for i, ao in enumerate(actions):
        drift.ingest(ao)
        entropy.ingest(ao, original_command=ao.get("_raw_cmd", ""))
        mut = mutator.mutate(action_obj=ao, entropy_score=entropy.current_entropy(), drift_score=drift.drift_score)
        s, d, ch = feedback[i]
        mutator.feedback(ChannelFeedback(payload_hash=mut.payload_hash, success=s, detected=d, channel=ch, latency_ms=100.0 + i * 50))

    report = SessionReport(drift=drift, entropy=entropy, mutator=mutator, label="demo")
    report.print_summary()
    report.save("/tmp/zds_demo_report.json")


if __name__ == "__main__":
    _demo()
