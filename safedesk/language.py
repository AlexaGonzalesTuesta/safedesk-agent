"""Lightweight English / Spanish detection with no external dependencies."""
from __future__ import annotations

import re

ES_MARKERS = {
    "hola", "quiero", "pedido", "dónde", "donde", "está", "esta", "mi", "mis", "reembolso", "reembolsa",
    "gracias", "por", "favor", "correo", "cuándo", "cuando", "necesito", "ayuda", "envío", "envio",
    "devolución", "devolucion", "devoluciones", "cambiar", "el", "la", "las", "los", "del", "de", "que",
    "es", "una", "un", "con", "para", "soy", "tengo", "llega", "cuál", "cual", "su", "tu", "y", "hablar",
    "persona", "cuenta", "nuevo", "nueva", "política", "politica", "garantía", "contraseña", "buenos",
    "días", "dias", "puedes", "puede", "estado", "muéstrame", "instrucciones", "anteriores", "ahora",
}
EN_MARKERS = {
    "the", "my", "is", "where", "order", "refund", "please", "i", "want", "need", "help", "email",
    "change", "to", "with", "for", "when", "thanks", "hello", "hi", "am", "have", "arrive", "status",
    "what", "your", "can", "you", "it", "of", "and", "about", "how", "does", "do", "this", "that",
    "track", "return", "policy", "talk", "human", "new", "write", "me",
}
ACCENT_CHARS = set("¿¡ñáéíóú")


def detect_language(text: str, default: str = "en") -> str:
    words = re.findall(r"[a-záéíóúñü']+", text.lower())
    es = sum(1 for w in words if w in ES_MARKERS)
    en = sum(1 for w in words if w in EN_MARKERS)
    if any(ch in ACCENT_CHARS for ch in text.lower()):
        es += 2
    if es > en:
        return "es"
    if en > es:
        return "en"
    return default
