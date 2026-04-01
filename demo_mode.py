"""
Demo mode stubs — imported by any module that checks config.DEMO_MODE.
Replaces network calls, LLM calls, and payload execution with safe fakes.
"""
import time, random

def fake_llm_parse(command: str) -> dict:
    return {
        "action": "exfil",
        "targets": ["ssh_keys", "credentials"],
        "schedule": "now",
        "priority": "normal",
        "noise": "silent",
        "rationale": f"[DEMO] Parsed: '{command}'"
    }

def fake_channel_result() -> dict:
    channels = ["HTTPS", "WS", "DNS"]
    detected = random.random() < 0.2
    return {
        "channel": random.choice(channels),
        "success": not detected,
        "detected": detected,
        "latency_ms": random.randint(10, 300)
    }

def fake_exfil(targets: list) -> dict:
    time.sleep(0.3)
    return {t: f"[DEMO] {t} exfil simulated" for t in targets}

def fake_peer_handshake() -> dict:
    return {
        "peer": "127.0.0.1",
        "verified": True,
        "fingerprint": "demo_aabbccdd",
        "quarantined": False
    }
