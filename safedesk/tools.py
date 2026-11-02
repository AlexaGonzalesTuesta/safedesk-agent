"""Tools the agent can call. Each tool has a JSON schema so an LLM can call it too."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .config import TenantConfig
from .guardrails import EMAIL_RE
from .session import Session
from .store import Store, refund_eligibility


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    func: Callable[..., dict]


class ToolRegistry:
    def __init__(self, store: Store, tenant: TenantConfig):
        self.store = store
        self.tenant = tenant
        self.tools: dict[str, Tool] = {}
        self._register_all()

    # ---------- registry helpers ----------
    def _add(self, name: str, description: str, properties: dict, required: list[str], func):
        self.tools[name] = Tool(
            name=name,
            description=description,
            input_schema={"type": "object", "properties": properties, "required": required},
            func=func,
        )

    def call(self, name: str, session: Session, args: dict) -> dict:
        if name not in self.tools:
            return {"error": "unknown_tool", "tool": name}
        try:
            return self.tools[name].func(session, **args)
        except TypeError as exc:
            return {"error": "bad_arguments", "detail": str(exc)}

    def claude_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self.tools.values()
        ]

    # ---------- tool implementations ----------
    def _register_all(self) -> None:
        s = {"type": "string"}
        self._add(
            "verify_identity",
            "Verify the customer by matching an order number with the email on the account. "
            "Required before any account action.",
            {"email": s, "order_id": s},
            ["email", "order_id"],
            self.verify_identity,
        )
        self._add(
            "get_order_status",
            "Get shipping status, carrier, ETA, and items for an order owned by the verified customer.",
            {"order_id": s},
            ["order_id"],
            self.get_order_status,
        )
        self._add(
            "check_refund_eligibility",
            "Check whether an order can be refunded under the store policy and whether a human must approve it.",
            {"order_id": s},
            ["order_id"],
            self.check_refund_eligibility,
        )
        self._add(
            "issue_refund",
            "Issue a refund to the original payment method. Only allowed for eligible orders under the auto-approval limit.",
            {"order_id": s, "reason": s},
            ["order_id"],
            self.issue_refund,
        )
        self._add(
            "update_email",
            "Change the email address on the verified customer's account.",
            {"new_email": s},
            ["new_email"],
            self.update_email,
        )
        self._add(
            "search_kb",
            "Search store policy articles (shipping, returns, warranty, international, passwords).",
            {"query": s, "language": {"type": "string", "enum": ["en", "es"]}},
            ["query"],
            self.search_kb,
        )
        self._add(
            "create_case",
            "Open a support case for a human specialist.",
            {"summary": s, "priority": {"type": "string", "enum": ["normal", "high"]}},
            ["summary"],
            self.create_case,
        )
        self._add(
            "escalate_to_human",
            "Hand the conversation to a human specialist queue.",
            {"reason": s, "case_id": s},
            ["reason"],
            self.escalate_to_human,
        )

    def verify_identity(self, session: Session, email: str, order_id: str) -> dict:
        order = self.store.get_order(order_id)
        customer = self.store.get_customer(order["customer_id"]) if order else None
        if customer and customer["email"].lower() == email.strip().lower():
            session.verified_customer_id = customer["customer_id"]
            session.failed_verifications = 0
            session.last_order_id = order["order_id"]
            return {"verified": True, "first_name": customer["name"].split()[0]}
        session.failed_verifications += 1
        remaining = max(self.tenant.max_verification_attempts - session.failed_verifications, 0)
        return {"verified": False, "attempts_remaining": remaining}

    def get_order_status(self, session: Session, order_id: str) -> dict:
        order = self.store.get_order(order_id)
        session.last_order_id = order["order_id"]
        status = "refunded" if order.get("refunded") else order["status"]
        return {
            "order_id": order["order_id"],
            "status": status,
            "carrier": order.get("carrier"),
            "eta": order.get("eta"),
            "delivered_on": order.get("delivered_on"),
            "items": [item["name"] for item in order["items"]],
        }

    def check_refund_eligibility(self, session: Session, order_id: str) -> dict:
        order = self.store.get_order(order_id)
        session.last_order_id = order["order_id"]
        return refund_eligibility(order, self.tenant)

    def issue_refund(self, session: Session, order_id: str, reason: str = "customer request") -> dict:
        order = self.store.get_order(order_id)
        amount = round(sum(item["price"] for item in order["items"]), 2)
        refund_id = f"R-{len(self.store.refunds) + 1:04d}"
        order["refunded"] = True
        self.store.refunds.append(
            {"refund_id": refund_id, "order_id": order["order_id"], "amount": amount, "reason": reason}
        )
        return {"refund_id": refund_id, "order_id": order["order_id"], "amount": amount}

    def update_email(self, session: Session, new_email: str) -> dict:
        if not EMAIL_RE.fullmatch(new_email.strip()):
            return {"error": "invalid_email"}
        customer = self.store.get_customer(session.verified_customer_id)
        old_email = customer["email"]
        customer["email"] = new_email.strip()
        self.store.email_changes.append(
            {"customer_id": customer["customer_id"], "old": old_email, "new": customer["email"]}
        )
        return {"updated": True, "new_email": customer["email"], "confirmation_sent_to": old_email}

    def search_kb(self, session: Session, query: str, language: str | None = None) -> dict:
        language = language or session.language
        q = query.lower()
        best, best_score = None, 0
        for article in self.store.kb:
            score = 0
            for lang_keywords in article["keywords"].values():
                score += sum(1 for kw in lang_keywords if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", q))
            if score > best_score:
                best, best_score = article, score
        if not best:
            return {"found": False}
        answer = best["answer"].get(language, best["answer"]["en"]).format(window=self.tenant.refund_window_days)
        title = best["title"].get(language, best["title"]["en"])
        return {"found": True, "article_id": best["id"], "title": title, "answer": answer}

    def create_case(self, session: Session, summary: str, priority: str = "normal") -> dict:
        case_id = f"CASE-{1001 + len(self.store.cases)}"
        self.store.cases.append(
            {"case_id": case_id, "session_id": session.session_id, "summary": summary, "priority": priority}
        )
        return {"case_id": case_id, "priority": priority}

    def escalate_to_human(self, session: Session, reason: str, case_id: str | None = None) -> dict:
        return {
            "queue": self.tenant.escalation_queue,
            "sla": self.tenant.sla(session.language),
            "case_id": case_id,
            "reason": reason,
        }
