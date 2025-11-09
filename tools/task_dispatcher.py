
import base64
import json

TASK_QUEUE = {}

def queue_plugin(agent_id, encrypted_blob):
    payload = base64.b64encode(encrypted_blob).decode()
    TASK_QUEUE[agent_id] = json.dumps({"payload": payload})

def get_queued_payload(agent_id):
    return TASK_QUEUE.pop(agent_id, None)
