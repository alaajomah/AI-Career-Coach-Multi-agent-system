import json
from datetime import datetime

def save_trace(session_id, steps):

    trace = {
        "session_id": session_id,
        "timestamp": str(datetime.now()),
        "steps": steps
    }

    with open("trace.json", "a") as f:
        f.write(json.dumps(trace))
        f.write("\n")