#!/usr/bin/env bash
# zer0DAYSlater full test runner
set -e
echo '🧪 Running zer0DAYSlater full test suite...'
export PYTHONPATH=$(pwd)
cd "$(dirname "$0")"

echo '▶️ Testing Python: memory_loader.py'
timeout 3s timeout 3s python3 "memory_loader.py" || echo '[!] Failed: memory_loader.py'

echo '▶️ Testing Python: process_doppelganger.py'
timeout 3s timeout 3s python3 "process_doppelganger.py" || echo '[!] Failed: process_doppelganger.py'

echo '▶️ Testing Python: process_cloak.py'
timeout 3s timeout 3s python3 "process_cloak.py" || echo '[!] Failed: process_cloak.py'

echo '▶️ Testing Python: llm_command_parser.py'
timeout 3s timeout 3s echo "exit" | python3 "llm_command_parser.py" || echo '[!] Failed: llm_command_parser.py'

echo '▶️ Testing Python: tui_dashboard.py'
timeout 3s timeout 3s echo "exit" | python3 "tui_dashboard.py" || echo '[!] Failed: tui_dashboard.py'

echo '▶️ Testing Python: c2_mesh_agent.py'
timeout 3s timeout 3s echo "exit" | python3 "c2_mesh_agent.py" || echo '[!] Failed: c2_mesh_agent.py'

echo '▶️ Testing Python: proxy_fallback_check.py'
timeout 3s timeout 3s python3 "proxy_fallback_check.py" || echo '[!] Failed: proxy_fallback_check.py'

echo '▶️ Testing Shell Script: install_omega.sh'
bash "install_omega.sh" || echo '[!] Failed: install_omega.sh'

echo '▶️ Testing Shell Script: omega_campaign.sh'
bash "omega_campaign.sh" || echo '[!] Failed: omega_campaign.sh'

echo '▶️ Testing Python: evasion_win.py'
timeout 3s timeout 3s python3 "evasion_win.py" || echo '[!] Failed: evasion_win.py'

echo '▶️ Testing Python: lateral.py'
timeout 3s timeout 3s python3 "lateral.py" || echo '[!] Failed: lateral.py'

echo '▶️ Testing Python: persistence.py'
timeout 3s timeout 3s python3 "persistence.py" || echo '[!] Failed: persistence.py'

echo '▶️ Testing Python: peer_auth.py'
timeout 3s timeout 3s python3 "peer_auth.py" || echo '[!] Failed: peer_auth.py'

echo '▶️ Testing Python: core/exfil_icmp.py'
timeout 3s timeout 3s python3 "core/exfil_icmp.py" || echo '[!] Failed: core/exfil_icmp.py'

echo '▶️ Testing Python: core/exfil_mqtt.py'
timeout 3s timeout 3s python3 "core/exfil_mqtt.py" || echo '[!] Failed: core/exfil_mqtt.py'

echo '▶️ Testing Python: core/adaptive_channel_manager.py'
timeout 3s timeout 3s python3 "core/adaptive_channel_manager.py" || echo '[!] Failed: core/adaptive_channel_manager.py'

echo '▶️ Testing Python: core/ws_client.py'
timeout 3s timeout 3s python3 "core/ws_client.py" || echo '[!] Failed: core/ws_client.py'

echo '▶️ Testing Python: agent/agent_core.py'
timeout 3s timeout 3s python3 "agent/agent_core.py" || echo '[!] Failed: agent/agent_core.py'

echo '▶️ Testing Python: agent/plugin_fetcher.py'
timeout 3s timeout 3s python3 "agent/plugin_fetcher.py" || echo '[!] Failed: agent/plugin_fetcher.py'

echo '▶️ Testing Python: agent/mtls_plugin_fetcher.py'
timeout 3s timeout 3s python3 "agent/mtls_plugin_fetcher.py" || echo '[!] Failed: agent/mtls_plugin_fetcher.py'

echo '▶️ Testing Python: agent/session_exfil_main.py'
timeout 3s timeout 3s python3 "agent/session_exfil_main.py" || echo '[!] Failed: agent/session_exfil_main.py'

echo '▶️ Testing Python: agent/ghost_daemon.py'
timeout 3s timeout 3s python3 "agent/ghost_daemon.py" || echo '[!] Failed: agent/ghost_daemon.py'

echo '▶️ Testing Python: agent/sandbox_check.py'
timeout 3s timeout 3s python3 "agent/sandbox_check.py" || echo '[!] Failed: agent/sandbox_check.py'

echo '▶️ Testing Python: agent/advanced_evasion.py'
timeout 3s timeout 3s python3 "agent/advanced_evasion.py" || echo '[!] Failed: agent/advanced_evasion.py'

echo '▶️ Testing Python: agent/kill_switch.py'
timeout 3s timeout 3s python3 "agent/kill_switch.py" || echo '[!] Failed: agent/kill_switch.py'

echo '▶️ Testing Python: agent/session_memory.py'
timeout 3s timeout 3s python3 "agent/session_memory.py" || echo '[!] Failed: agent/session_memory.py'

echo '▶️ Testing Python: agent/session_replay.py'
timeout 3s timeout 3s python3 "agent/session_replay.py" || echo '[!] Failed: agent/session_replay.py'

echo '▶️ Testing Python: tools/plugin_encryptor.py'
timeout 3s timeout 3s python3 "tools/plugin_encryptor.py" || echo '[!] Failed: tools/plugin_encryptor.py'

echo '▶️ Testing Python: tools/shellcode_loader.py'
timeout 3s timeout 3s python3 "tools/shellcode_loader.py" || echo '[!] Failed: tools/shellcode_loader.py'

echo '▶️ Testing Python: tools/c2_server.py'
timeout 3s timeout 3s python3 "tools/c2_server.py" || echo '[!] Failed: tools/c2_server.py'

echo '▶️ Testing Python: tools/c2_ws_server.py'
timeout 3s timeout 3s python3 "tools/c2_ws_server.py" || echo '[!] Failed: tools/c2_ws_server.py'

echo '▶️ Testing Python: tools/task_dispatcher.py'
timeout 3s timeout 3s python3 "tools/task_dispatcher.py" || echo '[!] Failed: tools/task_dispatcher.py'

echo '▶️ Testing Python: tools/mission_report.py'
timeout 3s timeout 3s python3 "tools/mission_report.py" || echo '[!] Failed: tools/mission_report.py'

echo '▶️ Testing Python: tools/loot_report_pdf.py'
timeout 3s timeout 3s python3 "tools/loot_report_pdf.py" || echo '[!] Failed: tools/loot_report_pdf.py'

echo '▶️ Testing Python: tools/loot_tagger.py'
timeout 3s timeout 3s python3 "tools/loot_tagger.py" || echo '[!] Failed: tools/loot_tagger.py'
