"""Policy engine: the rules live in code, not in a prompt.

Every tool call, whether it comes from the rule-based planner or from an LLM,
passes through PolicyEngine.check before it runs. That is what makes the agent
safe to point at a real account system: a model that is tricked into calling
issue_refund still cannot move money.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import TenantConfig
from .session import Session
from .store import Store, refund_eligibility

ACCOUNT_TOOLS = {"get_order_status", "check_refund_eligibility", "issue_refund", "update_email"}
HIGH_RISK_TOOLS = {"issue_refund", "update_email"}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = "allowed"
    route_to_human: bool = False


class PolicyEngine:
    def __init__(self, store: Store, tenant: TenantConfig):
        self.store = store
        self.tenant = tenant

    def check(self, tool: str, args: dict, session: Session) -> PolicyDecision:
        if tool == "verify_identity":
            if session.failed_verifications >= self.tenant.max_verification_attempts:
                return PolicyDecision(False, "verification_locked", route_to_human=True)
            return PolicyDecision(True)

        if tool in ACCOUNT_TOOLS:
            if not session.verified_customer_id:
                return PolicyDecision(False, "identity_not_verified")
            order_id = args.get("order_id")
            if order_id is not None:
                order = self.store.get_order(order_id)
                if order is None:
                    return PolicyDecision(False, "order_not_found")
                if order["customer_id"] != session.verified_customer_id:
                    return PolicyDecision(False, "order_not_owned_by_verified_customer")

        if tool in HIGH_RISK_TOOLS:
            level = session.risk_level
            if level == "high":
                return PolicyDecision(False, "social_engineering_risk", route_to_human=True)
            if tool == "update_email" and level == "medium":
                return PolicyDecision(False, "account_change_requires_human_review", route_to_human=True)

        if tool == "issue_refund":
            order = self.store.get_order(args.get("order_id"))
            if order is None:
                return PolicyDecision(False, "order_not_found")
            eligibility = refund_eligibility(order, self.tenant)
            if not eligibility["eligible"]:
                return PolicyDecision(False, eligibility["reason"])
            if eligibility["requires_human"]:
                return PolicyDecision(False, "amount_over_auto_limit", route_to_human=True)

        return PolicyDecision(True)
