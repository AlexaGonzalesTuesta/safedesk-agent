"""HTTP API and web console.

    uvicorn safedesk.api:app --reload
    open http://127.0.0.1:8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import SupportAgent
from .config import PACKAGE_DIR, TenantConfig
from .session import Session
from .store import Store
from .tracing import Tracer

app = FastAPI(title="SafeDesk Agent", version="0.1.0")

_state: dict = {}


def _boot() -> None:
    _state["agent"] = SupportAgent(
        store=Store(),
        tenant=TenantConfig.load(),
        tracer=Tracer(os.environ.get("SAFEDESK_TRACE_DIR", "traces")),
    )
    _state["sessions"] = {}


_boot()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PACKAGE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    agent: SupportAgent = _state["agent"]
    return {"status": "ok", "tenant": agent.tenant.tenant_id, "mode": agent.mode}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    agent: SupportAgent = _state["agent"]
    sessions: dict[str, Session] = _state["sessions"]
    session = sessions.get(req.session_id) if req.session_id else None
    if session is None:
        session = agent.new_session()
        sessions[session.session_id] = session
    reply = agent.handle(session, req.message)
    return {"session_id": session.session_id, "session": session.public_state(), **reply.to_dict()}


@app.get("/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = _state["sessions"].get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session.public_state()


@app.get("/traces")
def traces(limit: int = 20) -> list[dict]:
    agent: SupportAgent = _state["agent"]
    return list(agent.tracer.recent)[-limit:][::-1]


@app.get("/metrics")
def metrics() -> dict:
    agent: SupportAgent = _state["agent"]
    store = agent.store
    return {
        **agent.tracer.metrics(),
        "refunds_issued": len(store.refunds),
        "refund_dollars": round(sum(r["amount"] for r in store.refunds), 2),
        "cases_opened": len(store.cases),
        "email_changes": len(store.email_changes),
    }


@app.post("/reset")
def reset() -> dict:
    _boot()
    return {"status": "reset"}
