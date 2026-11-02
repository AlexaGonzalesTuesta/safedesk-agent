"""Conversation state for one customer chat."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .guardrails import risk_level


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    language: str = "en"
    turn: int = 0
    verified_customer_id: str | None = None
    failed_verifications: int = 0
    pending_intent: str | None = None
    pending_order_id: str | None = None
    pending_email: str | None = None
    pending_new_email: str | None = None
    last_order_id: str | None = None
    risk_categories: set[str] = field(default_factory=set)
    injection_attempts: int = 0
    llm_messages: list[dict] = field(default_factory=list)

    @property
    def risk_level(self) -> str:
        return risk_level(self.risk_categories)

    def clear_pending(self) -> None:
        self.pending_intent = None
        self.pending_order_id = None
        self.pending_email = None
        self.pending_new_email = None

    def public_state(self) -> dict:
        return {
            "session_id": self.session_id,
            "language": self.language,
            "turn": self.turn,
            "verified": self.verified_customer_id is not None,
            "failed_verifications": self.failed_verifications,
            "risk_level": self.risk_level,
            "risk_categories": sorted(self.risk_categories),
            "injection_attempts": self.injection_attempts,
            "pending_intent": self.pending_intent,
        }
