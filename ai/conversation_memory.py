"""
Sistema de memoria conversacional para el chatbot.
Mantiene contexto de conversaciones por usuario con ventana deslizante.
"""
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_HISTORY_PER_USER = 20
MEMORY_TTL_SECONDS = 3600  # 1 hora de inactividad limpia la memoria


@dataclass
class Message:
    role: str  # "user" o "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)
    intent: Optional[str] = None
    success: Optional[bool] = None


class ConversationMemory:
    """Memoria de conversación por usuario con ventana deslizante."""

    _conversations: Dict[int, List[Message]] = defaultdict(list)
    _last_activity: Dict[int, float] = {}

    @classmethod
    def add_user_message(cls, user_id: int, text: str) -> None:
        cls._cleanup_stale(user_id)
        cls._conversations[user_id].append(Message(role="user", content=text))
        cls._trim(user_id)
        cls._last_activity[user_id] = time.time()

    @classmethod
    def add_assistant_message(
        cls, user_id: int, text: str, intent: Optional[str] = None, success: Optional[bool] = None
    ) -> None:
        cls._cleanup_stale(user_id)
        cls._conversations[user_id].append(
            Message(role="assistant", content=text, intent=intent, success=success)
        )
        cls._trim(user_id)
        cls._last_activity[user_id] = time.time()

    @classmethod
    def get_history(cls, user_id: int, limit: int = 10) -> List[Dict]:
        """Retorna historial como lista de dicts compatibles con OpenAI messages."""
        cls._cleanup_stale(user_id)
        messages = cls._conversations.get(user_id, [])[-limit:]
        return [{"role": m.role, "content": m.content} for m in messages]

    @classmethod
    def get_last_intent(cls, user_id: int) -> Optional[str]:
        """Retorna la última intención detectada para contexto."""
        messages = cls._conversations.get(user_id, [])
        for msg in reversed(messages):
            if msg.intent:
                return msg.intent
        return None

    @classmethod
    def get_context_summary(cls, user_id: int) -> str:
        """Genera un resumen de contexto para el prompt del sistema."""
        messages = cls._conversations.get(user_id, [])
        if not messages:
            return ""

        recent = messages[-6:]
        recent_intents = [m.intent for m in recent if m.intent]
        failed = [m for m in recent if m.success is False]

        parts = []
        if recent_intents:
            parts.append(f"Intenciones recientes del usuario: {', '.join(recent_intents)}")
        if failed:
            parts.append(
                f"El usuario tuvo {len(failed)} operación(es) fallida(s) recientemente, "
                "podría necesitar ayuda adicional."
            )
        return "\n".join(parts)

    @classmethod
    def clear(cls, user_id: int) -> None:
        cls._conversations.pop(user_id, None)
        cls._last_activity.pop(user_id, None)

    @classmethod
    def _trim(cls, user_id: int) -> None:
        if len(cls._conversations[user_id]) > MAX_HISTORY_PER_USER:
            cls._conversations[user_id] = cls._conversations[user_id][-MAX_HISTORY_PER_USER:]

    @classmethod
    def _cleanup_stale(cls, user_id: int) -> None:
        last = cls._last_activity.get(user_id, 0)
        if last and (time.time() - last) > MEMORY_TTL_SECONDS:
            cls.clear(user_id)
