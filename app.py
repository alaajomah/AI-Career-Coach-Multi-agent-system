from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import hashlib
import time
import uuid
from coordinator import CoordinatorAgent
from memory import (
    save_user_memory,
    get_user_memory
)

from logging_config import logger
from traces import save_trace

from metrics import (
    REQUEST_COUNT,
    ERROR_COUNT,
    LATENCY
)

from prometheus_client import generate_latest
from fastapi.responses import Response

app = FastAPI()
coordinator = CoordinatorAgent()

class ChatRequest(BaseModel):
    user_id: str
    message: str
    resume: str | None = None
    level: str | None = "Junior"

@app.post("/chat")
def chat(data: ChatRequest):

    REQUEST_COUNT.inc()

    start = time.time()
    session_id = str(uuid.uuid4())
    steps = []

    try:
        steps.append("Receive Message")

        memory = get_user_memory(data.user_id)

        steps.append("Load Memory")

        # build user context
        user_data = {
            "resume": data.resume,
            "career_goal": memory.get("goal"),
            "level": data.level
        }

        # Coordinator decides which agent to use, OR — if the user
        # owes an answer to a previously-asked interview question —
        # routes straight to evaluation, skipping the router.
        outcome = coordinator.run(
            message=data.message,
            user_id=data.user_id,
            user_data=user_data
        )

        steps.append(f"Coordinator -> {outcome['agent']} ({outcome['type']})")

        save_user_memory(data.user_id, data.message)

        steps.append("Save Memory")

        latency = time.time() - start
        LATENCY.observe(latency)

        logger.info({
            "timestamp": str(datetime.now()),
            "request_id": session_id,
            "hashed_user_id": hashlib.sha256(data.user_id.encode()).hexdigest(),
            "prompt": data.message,
            "model_version": "gpt-4.1-mini",
            "latency_ms": round(latency * 1000),
            "agent": outcome["agent"],
            "response_type": outcome["type"],
            "error_code": None,
            "evaluation_score": 0.95
        })

        save_trace(session_id, steps)

        return {
            "agent": outcome["agent"],
            "type": outcome["type"],
            "response": outcome["result"],
            "memory": memory
        }

    except Exception as e:
        ERROR_COUNT.inc()
        return {"error": str(e)}

from interview_state import end_session

@app.post("/end_interview")
def end_interview(data: dict):
    user_id = data.get("user_id")
    summary = end_session(user_id)
    if summary is None:
        return {"agent": "interview", "response": {"message": "No interview session found."}}
    return {"agent": "interview", "response": summary}


@app.get("/metrics")
def metrics():

    return Response(
        generate_latest(),
        media_type="text/plain"
    )