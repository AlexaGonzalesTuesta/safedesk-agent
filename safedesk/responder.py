"""Bilingual reply templates for the rule-based planner.

Keeping replies as templates (instead of free text) in rules mode makes every
answer deterministic and testable. In Claude mode the model writes the reply,
but the same tools and policy engine produce the facts.
"""
from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hi! I'm the {brand} support assistant. I can track orders, handle refunds, update account details, and answer policy questions. How can I help?",
        "es": "¡Hola! Soy el asistente de soporte de {brand}. Puedo rastrear pedidos, gestionar reembolsos, actualizar datos de la cuenta y responder preguntas sobre nuestras políticas. ¿En qué te ayudo?",
    },
    "fallback": {
        "en": "I can help with orders, refunds, account email changes, and store policies. Could you tell me a bit more about what you need?",
        "es": "Puedo ayudarte con pedidos, reembolsos, cambios de correo en tu cuenta y políticas de la tienda. ¿Me cuentas un poco más sobre lo que necesitas?",
    },
    "ask_verification": {
        "en": "I can help with that. To protect your account, please share {missing}.",
        "es": "Con gusto te ayudo. Para proteger tu cuenta, compárteme {missing}.",
    },
    "missing_order": {"en": "your order number (like A1234)", "es": "tu número de pedido (por ejemplo A1234)"},
    "missing_email": {"en": "the email on your account", "es": "el correo de tu cuenta"},
    "joiner": {"en": " and ", "es": " y "},
    "ask_order": {
        "en": "Which order is this about? Please share the order number (like A1234).",
        "es": "¿Sobre qué pedido es? Compárteme el número de pedido (por ejemplo A1234).",
    },
    "ask_new_email": {
        "en": "Thanks {name}, you're verified. What new email address should I put on the account?",
        "es": "Gracias, {name}, ya estás verificado. ¿Qué nuevo correo quieres registrar en la cuenta?",
    },
    "verification_failed": {
        "en": "I couldn't verify that order number and email together. Please double-check both and try again.",
        "es": "No pude verificar ese número de pedido junto con ese correo. Revisa ambos datos e inténtalo de nuevo.",
    },
    "verified": {
        "en": "Thanks {name}, you're verified. What can I help you with on your account?",
        "es": "Gracias, {name}, ya estás verificado. ¿En qué te ayudo con tu cuenta?",
    },
    "status_shipped": {
        "en": "Order {order_id} has shipped with {carrier} and is expected to arrive on {eta}. Items: {items}.",
        "es": "El pedido {order_id} fue enviado con {carrier} y debería llegar el {eta}. Artículos: {items}.",
    },
    "status_delivered": {
        "en": "Order {order_id} was delivered on {delivered_on}. Items: {items}.",
        "es": "El pedido {order_id} fue entregado el {delivered_on}. Artículos: {items}.",
    },
    "status_processing": {
        "en": "Order {order_id} is still being prepared and should ship by {eta}. Items: {items}.",
        "es": "El pedido {order_id} todavía está en preparación y debería enviarse a más tardar el {eta}. Artículos: {items}.",
    },
    "status_refunded": {
        "en": "Order {order_id} has been refunded.",
        "es": "El pedido {order_id} ya fue reembolsado.",
    },
    "refund_issued": {
        "en": "Done. I issued a refund of ${amount:.2f} for order {order_id} (reference {refund_id}). It should reach your original payment method in 5 to 10 business days.",
        "es": "Listo. Emití un reembolso de ${amount:.2f} para el pedido {order_id} (referencia {refund_id}). Debería llegar a tu método de pago original en 5 a 10 días hábiles.",
    },
    "refund_not_delivered": {
        "en": "Order {order_id} hasn't been delivered yet, so it isn't eligible for a refund. Once it arrives you'll have {window} days to request one.",
        "es": "El pedido {order_id} todavía no ha sido entregado, así que aún no aplica para reembolso. Cuando llegue tendrás {window} días para solicitarlo.",
    },
    "refund_outside_window": {
        "en": "Order {order_id} was delivered {days} days ago, which is outside our {window}-day refund window, so I can't refund it automatically.",
        "es": "El pedido {order_id} se entregó hace {days} días, fuera de nuestro plazo de reembolso de {window} días, así que no puedo reembolsarlo automáticamente.",
    },
    "refund_final_sale": {
        "en": "Order {order_id} was a final sale item, so it isn't eligible for a refund under our policy.",
        "es": "El pedido {order_id} fue una venta final, así que no aplica para reembolso según nuestra política.",
    },
    "refund_already_refunded": {
        "en": "Order {order_id} has already been refunded.",
        "es": "El pedido {order_id} ya fue reembolsado.",
    },
    "refund_needs_human": {
        "en": "This refund (${amount:.2f}) is above the amount I can approve on my own, so I opened case {case_id} and sent it to our {queue} team. A specialist will follow up within {sla}.",
        "es": "Este reembolso (${amount:.2f}) supera el monto que puedo aprobar por mi cuenta, así que abrí el caso {case_id} y lo envié a nuestro equipo {queue}. Un especialista te contactará en {sla}.",
    },
    "security_hold": {
        "en": "For your security, I can't complete that request in this chat. I opened case {case_id} and a specialist on our {queue} team will verify it directly with the account owner within {sla}.",
        "es": "Por tu seguridad, no puedo completar esa solicitud en este chat. Abrí el caso {case_id} y un especialista de nuestro equipo {queue} la verificará directamente con el titular de la cuenta en {sla}.",
    },
    "escalated": {
        "en": "I've connected you with a human specialist. Your case number is {case_id}, and someone from our {queue} team will reach out within {sla}.",
        "es": "Te conecté con un especialista humano. Tu número de caso es {case_id} y alguien de nuestro equipo {queue} te contactará en {sla}.",
    },
    "email_updated": {
        "en": "Your account email has been updated to {new_email}. We sent a confirmation to your previous address in case this wasn't you.",
        "es": "Actualizamos el correo de tu cuenta a {new_email}. Enviamos una confirmación a tu correo anterior por si no fuiste tú.",
    },
    "invalid_email": {
        "en": "That doesn't look like a valid email address. Could you send it again?",
        "es": "Ese correo no parece válido. ¿Me lo envías de nuevo?",
    },
    "kb_none": {
        "en": "I couldn't find a policy article on that. Would you like me to connect you with a specialist?",
        "es": "No encontré un artículo de política sobre eso. ¿Quieres que te conecte con un especialista?",
    },
    "injection": {
        "en": "I can't change how I work or share my internal instructions. I'm happy to help with orders, refunds, account changes, or store policies.",
        "es": "No puedo cambiar cómo funciono ni compartir mis instrucciones internas. Con gusto te ayudo con pedidos, reembolsos, cambios en tu cuenta o políticas de la tienda.",
    },
    "lockout": {
        "en": "There have been too many unsuccessful verification attempts, so I've paused account access in this chat. I opened case {case_id} and a specialist will help you verify within {sla}.",
        "es": "Hubo demasiados intentos de verificación fallidos, así que pausé el acceso a la cuenta en este chat. Abrí el caso {case_id} y un especialista te ayudará a verificar tu identidad en {sla}.",
    },
    "order_not_owned": {
        "en": "That order isn't linked to the account you verified, so I can't share its details. If you think this is a mistake, I can connect you with a specialist.",
        "es": "Ese pedido no está vinculado a la cuenta que verificaste, así que no puedo mostrar sus datos. Si crees que es un error, puedo conectarte con un especialista.",
    },
    "order_not_found": {
        "en": "I couldn't find an order with that number. Could you double-check it?",
        "es": "No encontré un pedido con ese número. ¿Puedes revisarlo?",
    },
}


def render(key: str, language: str, **values) -> str:
    variants = TEMPLATES[key]
    template = variants.get(language) or variants["en"]
    return template.format(**values)
