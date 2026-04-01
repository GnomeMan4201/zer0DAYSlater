import os

CONFIG = {
    "mqtt_broker": os.environ.get("ZDS_MQTT_BROKER", "127.0.0.1"),
    "mqtt_port": int(os.environ.get("ZDS_MQTT_PORT", "1883")),
    "https_endpoint": os.environ.get("ZDS_HTTPS_ENDPOINT", "https://127.0.0.1/api"),
    "auth_token": os.environ.get("ZDS_AUTH_TOKEN", ""),
    "c2_ws_url": os.environ.get("ZDS_C2_WS_URL", ""),
    "plugin_server": os.environ.get("ZDS_PLUGIN_SERVER", ""),
}
