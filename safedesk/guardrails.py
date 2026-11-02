"""Input guardrails: prompt injection, social engineering risk, and PII redaction.

These checks run before any planner (rule-based or LLM) sees the message. They
do not replace the policy engine; they feed it. A high-risk session cannot
complete a refund or account change no matter what the planner decides.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

INJECTION_PATTERNS = [
    r"ignore (all |any )?(of )?(the |your )?(previous|prior|above|earlier) (instructions|rules|messages)",
    r"disregard (your|the|all|any) (instructions|rules|policies|guidelines)",
    r"system prompt",
    r"developer mode",
    r"you are now (an? )?(admin|administrator|unrestricted|dan)",
    r"act as (an? )?(admin|administrator|supervisor|system)",
    r"reveal (your|the) (instructions|rules|prompt)",
    r"ignora (todas )?(las )?(instrucciones|reglas)",
    r"olvida (tus|las) (reglas|instrucciones)",
    r"modo desarrollador",
    r"prompt del sistema",
]

SOCIAL_ENGINEERING_SIGNALS: dict[str, list[str]] = {
    "impersonation": [
        "i'm the ceo", "i am the ceo", "i'm the owner of", "on behalf of", "my boss",
        "account owner", "from your fraud team", "from your security team", "i work for your company",
        "soy el gerente", "soy el dueño", "soy la dueña", "en nombre de", "mi jefe",
        "soy del equipo de fraude", "dueño de la cuenta", "dueña de la cuenta",
    ],
    "urgency": [
        "urgent", "urgently", "immediately", "right now", "asap", "emergency",
        "urgente", "inmediatamente", "ahora mismo", "emergencia",
    ],
    "verification_bypass": [
        "skip verification", "skip the verification", "no need to verify", "don't verify",
        "do not verify", "without verifying", "without verification", "bypass",
        "sin verificar", "sin verificación", "salta la verificación", "no hace falta verificar",
    ],
    "payout_redirect": [
        "different card", "another card", "another account", "different account", "gift card",
        "send the refund to", "send it to my", "wire", "crypto", "bitcoin",
        "otra tarjeta", "otra cuenta", "tarjeta de regalo", "envía el reembolso a", "transferencia",
    ],
    "synthetic_media": [
        "voice note", "voice message", "voice memo", "recording of", "listen to my voice",
        "video proves", "deepfake", "nota de voz", "mensaje de voz", "grabación", "escucha mi voz",
    ],
}

SECURITY_DENIAL_REASONS = {
    "social_engineering_risk",
    "account_change_requires_human_review",
    "verification_locked",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{8,}\d")


@dataclass
class RiskAssessment:
    categories: list[str] = field(default_factory=list)
    matches: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        return len(self.categories)

    @property
    def level(self) -> str:
        return risk_level(self.categories)


def risk_level(categories) -> str:
    categories = set(categories)
    if "verification_bypass" in categories or len(categories) >= 2:
        return "high"
    if len(categories) == 1:
        return "medium"
    return "low"


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def detect_prompt_injection(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in INJECTION_PATTERNS if re.search(p, lowered)]


def assess_social_engineering(text: str) -> RiskAssessment:
    lowered = text.lower().replace("’", "'")
    assessment = RiskAssessment()
    for category, phrases in SOCIAL_ENGINEERING_SIGNALS.items():
        hits = [p for p in phrases if _contains(lowered, p)]
        if hits:
            assessment.categories.append(category)
            assessment.matches.extend(hits)
    return assessment


def _mask_email(match: re.Match) -> str:
    local, _, domain = match.group(0).partition("@")
    return f"{local[:1]}***@{domain}"


def redact(text: str) -> str:
    """Mask emails, card numbers, and phone numbers before anything is logged."""
    if not isinstance(text, str):
        return text
    text = CARD_RE.sub(lambda m: "<card ****" + re.sub(r"\D", "", m.group(0))[-4:] + ">", text)
    text = EMAIL_RE.sub(_mask_email, text)
    text = PHONE_RE.sub("<phone>", text)
    return text


def redact_obj(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    return obj
