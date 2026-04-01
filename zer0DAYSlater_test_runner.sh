#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
PASS=0
FAIL=0
run_test() {
    local label="$1"
    local cmd="$2"
    if timeout 3s bash -c "$cmd" > /dev/null 2>&1; then
        echo "[✓] $label"
        PASS=$((PASS+1))
    else
        echo "[!] Failed: $label"
        FAIL=$((FAIL+1))
    fi
}
run_test "memory_loader.py"                  "python3 -c 'import memory_loader'"
run_test "process_doppelganger.py"           "python3 -c 'import process_doppelganger'"
run_test "process_cloak.py"                  "python3 -c 'import process_cloak'"
run_test "proxy_fallback_check.py"           "python3 -c 'import proxy_fallback_check'"
run_test "evasion_win.py"                    "python3 -c 'import evasion_win'"
run_test "lateral.py"                        "python3 -c 'import lateral'"
run_test "persistence.py"                    "python3 -c 'import persistence'"
run_test "peer_auth.py"                      "python3 -c 'import peer_auth'"
run_test "core/exfil_icmp.py"               "python3 -c 'import core.exfil_icmp'"
run_test "core/exfil_mqtt.py"               "python3 -c 'import core.exfil_mqtt'"
run_test "core/adaptive_channel_manager.py" "python3 -c 'import core.adaptive_channel_manager'"
run_test "core/ws_client.py"                "python3 -c 'import core.ws_client'"
run_test "agent/agent_core.py"              "python3 -c 'import agent.agent_core'"
run_test "agent/plugin_fetcher.py"          "python3 -c 'import agent.plugin_fetcher'"
run_test "agent/session_exfil_main.py"      "python3 -c 'import agent.session_exfil_main'"
run_test "agent/ghost_daemon.py"            "python3 -c 'import agent.ghost_daemon'"
run_test "agent/sandbox_check.py"           "python3 -c 'import agent.sandbox_check'"
run_test "agent/advanced_evasion.py"        "python3 -c 'import agent.advanced_evasion'"
run_test "agent/kill_switch.py"             "python3 -c 'import agent.kill_switch'"
run_test "agent/session_memory.py"          "python3 -c 'import agent.session_memory'"
run_test "agent/session_replay.py"          "python3 -c 'import agent.session_replay'"
run_test "tools/plugin_encryptor.py"        "python3 -c 'import tools.plugin_encryptor'"
run_test "tools/shellcode_loader.py"        "python3 -c 'import tools.shellcode_loader'"
run_test "tools/c2_server.py"               "python3 -c 'import tools.c2_server'"
run_test "tools/c2_ws_server.py"            "python3 -c 'import tools.c2_ws_server'"
run_test "tools/task_dispatcher.py"         "python3 -c 'import tools.task_dispatcher'"
run_test "tools/mission_report.py"          "python3 -c 'import tools.mission_report'"
run_test "tools/loot_report_pdf.py"         "python3 -c 'import tools.loot_report_pdf'"
run_test "tools/loot_tagger.py"             "python3 -c 'import tools.loot_tagger'"
echo ""
echo "Results: $PASS passed, $FAIL failed"
