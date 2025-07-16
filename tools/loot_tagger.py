import json
from datetime import datetime
import uuid

def tag_loot(data_type, content):
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": data_type,
        "data": content
    }
    return entry

if __name__ == "__main__":
    example = tag_loot("cookies", {"domain": "example.com", "value": "abc123"})
    print(json.dumps(example, indent=2))
