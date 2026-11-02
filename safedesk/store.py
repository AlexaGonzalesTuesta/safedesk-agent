"""In-memory data store that stands in for a CRM / order system.

Every Store instance loads a fresh copy of the seed data, so evals and tests
never leak state into each other.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .config import DATA_DIR, TenantConfig


class Store:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.customers = {c["customer_id"]: c for c in self._load(data_dir / "customers.json")}
        self.orders = {o["order_id"]: o for o in self._load(data_dir / "orders.json")}
        self.kb = self._load(data_dir / "kb.json")
        self.refunds: list[dict] = []
        self.cases: list[dict] = []
        self.email_changes: list[dict] = []

    @staticmethod
    def _load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def get_order(self, order_id: str | None) -> dict | None:
        if not order_id:
            return None
        return self.orders.get(order_id.strip().upper())

    def get_customer(self, customer_id: str | None) -> dict | None:
        if not customer_id:
            return None
        return self.customers.get(customer_id)


def refund_eligibility(order: dict, tenant: TenantConfig) -> dict:
    """Single source of truth for refund rules. Used by the tool and the policy engine."""
    amount = round(sum(item["price"] for item in order["items"]), 2)
    result = {
        "order_id": order["order_id"],
        "amount": amount,
        "eligible": False,
        "reason": "",
        "days_since_delivery": None,
        "requires_human": False,
        "window_days": tenant.refund_window_days,
    }
    if order.get("refunded"):
        result["reason"] = "already_refunded"
        return result
    if order["status"] != "delivered" or not order.get("delivered_on"):
        result["reason"] = "not_delivered"
        return result
    if order.get("final_sale"):
        result["reason"] = "final_sale"
        return result
    days = (tenant.today - date.fromisoformat(order["delivered_on"])).days
    result["days_since_delivery"] = days
    if days > tenant.refund_window_days:
        result["reason"] = "outside_window"
        return result
    result["eligible"] = True
    result["reason"] = "eligible"
    result["requires_human"] = amount > tenant.auto_refund_limit
    return result
