"""Tenant configuration.

Each customer deployment is described by one JSON file in /tenants. Changing a
tenant's refund window, auto-approval limit, or escalation queue is a config
change, not a code change.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
DATA_DIR = PACKAGE_DIR / "data"
TENANTS_DIR = REPO_DIR / "tenants"
DEFAULT_TENANT_FILE = TENANTS_DIR / "northwind_outfitters.json"


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    brand_name: str
    refund_window_days: int = 30
    auto_refund_limit: float = 500.0
    supported_languages: tuple[str, ...] = ("en", "es")
    escalation_queue: str = "Tier 2 Support"
    escalation_sla: dict = field(default_factory=lambda: {"en": "4 business hours", "es": "4 horas hábiles"})
    max_verification_attempts: int = 3
    today: date = date(2026, 11, 2)

    def sla(self, language: str) -> str:
        return self.escalation_sla.get(language) or self.escalation_sla.get("en", "")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "TenantConfig":
        chosen = path or os.environ.get("SAFEDESK_TENANT") or DEFAULT_TENANT_FILE
        chosen = Path(chosen)
        if not chosen.is_absolute() and not chosen.exists():
            chosen = TENANTS_DIR / chosen
        raw = json.loads(chosen.read_text(encoding="utf-8"))
        today = os.environ.get("SAFEDESK_TODAY") or raw.get("today") or date.today().isoformat()
        return cls(
            tenant_id=raw["tenant_id"],
            brand_name=raw["brand_name"],
            refund_window_days=int(raw.get("refund_window_days", 30)),
            auto_refund_limit=float(raw.get("auto_refund_limit", 500.0)),
            supported_languages=tuple(raw.get("supported_languages", ["en", "es"])),
            escalation_queue=raw.get("escalation_queue", "Tier 2 Support"),
            escalation_sla=raw.get("escalation_sla", {"en": "4 business hours", "es": "4 horas hábiles"}),
            max_verification_attempts=int(raw.get("max_verification_attempts", 3)),
            today=date.fromisoformat(today),
        )
