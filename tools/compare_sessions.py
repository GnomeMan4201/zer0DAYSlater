#!/usr/bin/env python3
"""
zer0DAYSlater — Session Comparator
Diffs two session JSON reports and surfaces divergence across
drift, entropy, and mutation fitness dimensions.

Usage:
    python3 tools/compare_sessions.py session_a.json session_b.json
    python3 tools/compare_sessions.py session_a.json session_b.json --json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

_SCORE_SIGNIFICANT   = 0.10
_FITNESS_SIGNIFICANT = 0.08

def _bar(v, w=15):
    f = int(min(max(v,0),1)*w); return "█"*f + "░"*(w-f)

def _load(path):
    p = Path(path)
    if not p.exists(): print(f"[!] Not found: {path}"); sys.exit(1)
    return json.loads(p.read_text())

def compare(a, b):
    r = {
        "label_a": a.get("session_label","session_a"),
        "label_b": b.get("session_label","session_b"),
        "health_a": a.get("overall_health"),
        "health_b": b.get("overall_health"),
        "health_changed": a.get("overall_health") != b.get("overall_health"),
    }
    da,db = a["drift"], b["drift"]
    dd = (db["score"] or 0) - (da["score"] or 0)
    r["drift"] = {
        "score_a": da["score"], "score_b": db["score"],
        "delta": round(dd,4), "significant": abs(dd) >= _SCORE_SIGNIFICANT,
        "status_a": da["status"], "status_b": db["status"],
        "status_changed": da["status"] != db["status"],
        "signals_a": da.get("signal_breakdown") or {},
        "signals_b": db.get("signal_breakdown") or {},
        "new_signals":      [s for s in (db.get("signal_breakdown") or {}) if s not in (da.get("signal_breakdown") or {})],
        "resolved_signals": [s for s in (da.get("signal_breakdown") or {}) if s not in (db.get("signal_breakdown") or {})],
    }
    ea,eb = a["entropy"], b["entropy"]
    ed = (eb["score"] or 0) - (ea["score"] or 0)
    r["entropy"] = {
        "score_a": ea["score"], "score_b": eb["score"],
        "delta": round(ed,4), "significant": abs(ed) >= _SCORE_SIGNIFICANT,
        "status_a": ea["status"], "status_b": eb["status"],
        "status_changed": ea["status"] != eb["status"],
        "signals_a": ea.get("signal_breakdown") or {},
        "signals_b": eb.get("signal_breakdown") or {},
        "new_signals":      [s for s in (eb.get("signal_breakdown") or {}) if s not in (ea.get("signal_breakdown") or {})],
        "resolved_signals": [s for s in (ea.get("signal_breakdown") or {}) if s not in (eb.get("signal_breakdown") or {})],
    }
    fa = a["mutation"].get("fitness") or {}
    fb = b["mutation"].get("fitness") or {}
    fd = {}
    for p in set(list(fa)+list(fb)):
        va,vb = fa.get(p,0.0), fb.get(p,0.0); d = vb-va
        fd[p] = {"a":round(va,4),"b":round(vb,4),"delta":round(d,4),
                 "significant":abs(d)>=_FITNESS_SIGNIFICANT,
                 "direction":"improved" if d>0 else "degraded" if d<0 else "stable"}
    r["mutation"] = {
        "top_a": a["mutation"].get("top_personality"),
        "top_b": b["mutation"].get("top_personality"),
        "top_changed": a["mutation"].get("top_personality") != b["mutation"].get("top_personality"),
        "generations_a": a["mutation"].get("generations",0),
        "generations_b": b["mutation"].get("generations",0),
        "fitness_deltas": fd,
        "degraded_a": a["mutation"].get("degraded_personalities",[]),
        "degraded_b": b["mutation"].get("degraded_personalities",[]),
        "newly_degraded": [p for p in b["mutation"].get("degraded_personalities",[]) if p not in a["mutation"].get("degraded_personalities",[])],
        "recovered":      [p for p in a["mutation"].get("degraded_personalities",[]) if p not in b["mutation"].get("degraded_personalities",[])],
    }
    tla,tlb = a.get("timeline",[]), b.get("timeline",[])
    n = min(len(tla),len(tlb))
    diff = []
    for i in range(n):
        ae,be = tla[i].get("entropy",0), tlb[i].get("entropy",0); d = be-ae
        diff.append({"idx":i,"entropy_a":round(ae,4),"entropy_b":round(be,4),"delta":round(d,4),
                     "pers_a":tla[i].get("personality"),"pers_b":tlb[i].get("personality"),
                     "pers_changed":tla[i].get("personality")!=tlb[i].get("personality")})
    r["timeline"] = {"actions_a":len(tla),"actions_b":len(tlb),"comparable":n,"diff":diff,
                     "max_spike":max((abs(e["delta"]) for e in diff),default=0.0)}
    return r

def print_comparison(r):
    hc = {"NOMINAL":"\033[32m","DEGRADED":"\033[33m","CRITICAL":"\033[31m"}
    rst = "\033[0m"
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  zer0DAYSlater — Session Comparison                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  A: {r['label_a']:<57}║")
    print(f"║  B: {r['label_b']:<57}║")
    ha,hb = r["health_a"],r["health_b"]
    chg = " ← CHANGED" if r["health_changed"] else ""
    print(f"║  Health: {hc.get(ha,'')}{ha:<10}{rst} → {hc.get(hb,'')}{hb:<10}{rst}{chg:<20}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    d = r["drift"]
    print(f"║  DRIFT                                                       ║")
    print(f"║    A: {d['score_a']:.3f} {_bar(d['score_a'] or 0)}  {d['status_a']:<8}              ║")
    print(f"║    B: {d['score_b']:.3f} {_bar(d['score_b'] or 0)}  {d['status_b']:<8}              ║")
    flag = " ◄ SIGNIFICANT" if d["significant"] else ""
    print(f"║    Δ: {d['delta']:+.3f}{flag:<46}    ║")
    for s in d["new_signals"]:      print(f"║    + new signal:  {s:<43}║")
    for s in d["resolved_signals"]: print(f"║    - resolved:    {s:<43}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    e = r["entropy"]
    print(f"║  ENTROPY                                                     ║")
    print(f"║    A: {e['score_a']:.3f} {_bar(e['score_a'] or 0)}  {e['status_a']:<8}              ║")
    print(f"║    B: {e['score_b']:.3f} {_bar(e['score_b'] or 0)}  {e['status_b']:<8}              ║")
    flag = " ◄ SIGNIFICANT" if e["significant"] else ""
    print(f"║    Δ: {e['delta']:+.3f}{flag:<46}    ║")
    for s in e["new_signals"]:      print(f"║    + new signal:  {s:<43}║")
    for s in e["resolved_signals"]: print(f"║    - resolved:    {s:<43}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    m = r["mutation"]
    top = f"{m['top_a']} → {m['top_b']}" if m["top_changed"] else f"{m['top_a']} (stable)"
    print(f"║  MUTATION  top: {top:<46}║")
    for p,fd in sorted(m["fitness_deltas"].items(),key=lambda x:abs(x[1]["delta"]),reverse=True):
        sig = " ◄" if fd["significant"] else "  "
        d_sym = {"improved":"\033[32m↑\033[0m","degraded":"\033[31m↓\033[0m","stable":"~"}.get(fd["direction"],"")
        print(f"║    {p:<12} A:{fd['a']:.2f} B:{fd['b']:.2f} Δ{fd['delta']:+.3f} {d_sym}{sig:<25} ║")
    for p in m["newly_degraded"]: print(f"║    ⚠ newly degraded: {p:<40}║")
    for p in m["recovered"]:      print(f"║    ✓ recovered:      {p:<40}║")
    print("╠══════════════════════════════════════════════════════════════╣")
    tl = r["timeline"]
    print(f"║  TIMELINE  A={tl['actions_a']}  B={tl['actions_b']}  comparable={tl['comparable']}{'':>30}║")
    if tl["diff"]:
        print(f"║  {'idx':>3}  {'ent_A':>6}  {'ent_B':>6}  {'Δ':>7}  {'pers_A':<10}  {'pers_B':<8}  ║")
        for e in tl["diff"]:
            pc = " ←" if e["pers_changed"] else "  "
            pa=(e["pers_a"] or "?")[:8]; pb=(e["pers_b"] or "?")[:8]
            print(f"║  [{e['idx']:>3}]  {e['entropy_a']:.3f}    {e['entropy_b']:.3f}   {e['delta']:+.3f}   {pa:<10}  {pb:<8}{pc}  ║")
    print(f"║  Max spike: {tl['max_spike']:.4f}{'':>49}║")
    print("╚══════════════════════════════════════════════════════════════╝")

def main():
    import argparse
    ap = argparse.ArgumentParser(prog="compare_sessions")
    ap.add_argument("session_a"); ap.add_argument("session_b")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save", metavar="PATH", default=None)
    args = ap.parse_args()
    a,b = _load(args.session_a), _load(args.session_b)
    result = compare(a,b)
    if args.json: print(json.dumps(result,indent=2))
    else: print_comparison(result)
    if args.save:
        Path(args.save).write_text(json.dumps(result,indent=2))
        print(f"[compare_sessions] saved → {args.save}")

if __name__ == "__main__":
    main()
