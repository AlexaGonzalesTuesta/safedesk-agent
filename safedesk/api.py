"""HTTP API and web console.

    uvicorn safedesk.api:app --reload
    open http://127.0.0.1:8000

Every browser gets its own sandbox (a private copy of the demo data, sessions,
and metrics), identified by the X-Sandbox-Id header the console sends. On a
public deployment, one visitor's refunds or resets never affect another's.
Requests without the header share a "default" sandbox, which is what the CLI,
curl, and tests use.
"""
from __future__ import annotations

import os
import re
from collections import OrderedDict
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import SupportAgent
from .config import PACKAGE_DIR, TenantConfig
from .guardrails import SECURITY_DENIAL_REASONS
from .session import Session
from .store import Store, refund_eligibility
from .tracing import Tracer

app = FastAPI(title="SafeDesk Agent", version="0.2.0")

MAX_SANDBOXES = 300          # oldest idle sandbox is dropped beyond this
MAX_SESSIONS_PER_SANDBOX = 100
SANDBOX_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

_state: dict = {}


class Sandbox:
    def __init__(self, tenant: TenantConfig, trace_dir: str):
        self.agent = SupportAgent(store=Store(), tenant=tenant, tracer=Tracer(trace_dir))
        self.sessions: OrderedDict[str, Session] = OrderedDict()


def _boot() -> None:
    _state["tenant"] = TenantConfig.load()
    _state["trace_dir"] = os.environ.get("SAFEDESK_TRACE_DIR", "traces")
    _state["sandboxes"] = OrderedDict()


_boot()


def _sandbox(sandbox_id: Optional[str]) -> Sandbox:
    key = sandbox_id if sandbox_id and SANDBOX_ID.match(sandbox_id) else "default"
    boxes: OrderedDict[str, Sandbox] = _state["sandboxes"]
    if key in boxes:
        boxes.move_to_end(key)
        return boxes[key]
    box = Sandbox(_state["tenant"], _state["trace_dir"])
    boxes[key] = box
    while len(boxes) > MAX_SANDBOXES:
        boxes.popitem(last=False)
    return box


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(PACKAGE_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict:
    tenant: TenantConfig = _state["tenant"]
    mode = os.environ.get("SAFEDESK_MODE", "rules")
    return {"status": "ok", "tenant": tenant.tenant_id, "brand": tenant.brand_name, "mode": mode}


@app.post("/chat")
def chat(req: ChatRequest, x_sandbox_id: Optional[str] = Header(default=None)) -> dict:
    box = _sandbox(x_sandbox_id)
    session = box.sessions.get(req.session_id) if req.session_id else None
    if session is None:
        session = box.agent.new_session()
        box.sessions[session.session_id] = session
        while len(box.sessions) > MAX_SESSIONS_PER_SANDBOX:
            box.sessions.popitem(last=False)
    reply = box.agent.handle(session, req.message)
    return {"session_id": session.session_id, "session": session.public_state(), **reply.to_dict()}


@app.get("/sessions/{session_id}")
def get_session(session_id: str, x_sandbox_id: Optional[str] = Header(default=None)) -> dict:
    session = _sandbox(x_sandbox_id).sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session.public_state()


@app.get("/traces")
def traces(limit: int = 20, x_sandbox_id: Optional[str] = Header(default=None)) -> list[dict]:
    return list(_sandbox(x_sandbox_id).agent.tracer.recent)[-limit:][::-1]


@app.get("/metrics")
def metrics(x_sandbox_id: Optional[str] = Header(default=None)) -> dict:
    agent = _sandbox(x_sandbox_id).agent
    store = agent.store
    turns = list(agent.tracer.recent)

    def stopped(t: dict) -> bool:
        g = t.get("guardrails", {})
        return bool(g.get("injection") or g.get("security_hold") or any(
            not c.get("allowed") and c.get("reason") in SECURITY_DENIAL_REASONS | {"order_not_owned_by_verified_customer"}
            for c in t.get("tool_calls", [])))

    return {
        **agent.tracer.metrics(),
        # The three numbers the console leads with.
        "attacks_stopped": sum(1 for t in turns if stopped(t)),
        "customers_helped": sum(
            1 for t in turns
            if not t.get("escalated") and any(
                c.get("allowed") and c.get("name") in {"issue_refund", "get_order_status", "update_email", "search_kb"}
                for c in t.get("tool_calls", []))),
        "sent_to_human": sum(1 for t in turns if t.get("escalated") and not stopped(t)),
        "refunds_issued": len(store.refunds),
        "refund_dollars": round(sum(r["amount"] for r in store.refunds), 2),
        "cases_opened": len(store.cases),
        "email_changes": len(store.email_changes),
    }


@app.get("/demo-data")
def demo_data(x_sandbox_id: Optional[str] = Header(default=None)) -> dict:
    """Fictional test accounts so reviewers can try every outcome. No real customer data."""
    agent = _sandbox(x_sandbox_id).agent
    store, tenant = agent.store, agent.tenant
    hints = {
        "eligible": "Refund goes through automatically",
        "not_delivered": "Not delivered yet, so refund is refused",
        "outside_window": f"Outside the {tenant.refund_window_days}-day window, so refund is refused",
        "final_sale": "Final sale, so refund is refused",
        "already_refunded": "Already refunded in this sandbox",
    }
    orders = []
    for order in store.orders.values():
        customer = store.customers[order["customer_id"]]
        elig = refund_eligibility(order, tenant)
        hint = hints.get(elig["reason"], elig["reason"])
        if elig["eligible"] and elig["requires_human"]:
            hint = f"Above the ${tenant.auto_refund_limit:.0f} limit, so it goes to a human"
        orders.append({
            "order_id": order["order_id"],
            "customer": customer["name"],
            "email": customer["email"],
            "status": "refunded" if order.get("refunded") else order["status"],
            "items": ", ".join(i["name"] for i in order["items"]),
            "amount": elig["amount"],
            "refund_outcome": hint,
        })
    return {"tenant": tenant.tenant_id, "today": tenant.today.isoformat(), "orders": orders}


@app.post("/reset")
def reset(x_sandbox_id: Optional[str] = Header(default=None)) -> dict:
    """Reset only the caller's sandbox: fresh orders, no sessions, zeroed metrics."""
    boxes: OrderedDict[str, Sandbox] = _state["sandboxes"]
    key = x_sandbox_id if x_sandbox_id and SANDBOX_ID.match(x_sandbox_id) else "default"
    boxes.pop(key, None)
    _sandbox(x_sandbox_id)
    return {"status": "reset"}
