"""SafeDesk: a bilingual customer-service agent with code-enforced guardrails."""
from .agent import AgentReply, SupportAgent
from .config import TenantConfig
from .session import Session
from .store import Store

__all__ = ["SupportAgent", "AgentReply", "TenantConfig", "Session", "Store"]
__version__ = "0.1.0"
