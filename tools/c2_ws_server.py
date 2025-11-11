import asyncio
import json
import ssl

import websockets

TASK_QUEUE = {}


async def handle_ws(websocket, path):
    try:
        init_msg = await websocket.recv()
        info = json.loads(init_msg)
        agent_id = info.get("agent_id")

        while True:
            if agent_id in TASK_QUEUE:
                payload = TASK_QUEUE.pop(agent_id)
                await websocket.send(json.dumps({"payload": payload}))
            await asyncio.sleep(5)
    except Exception as e:
        print(f"[!] WebSocket connection error: {e}")


async def main():
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain("cert.pem", "key.pem")

    async with websockets.serve(handle_ws, "0.0.0.0", 8765, ssl=ssl_ctx):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
