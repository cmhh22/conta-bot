"""
Servicio de OpenAI para procesamiento de lenguaje natural avanzado.
Utiliza Function Calling para deteccion precisa de intenciones y
memoria conversational para dialogos multi-turno.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from core.config import OPENAI_API_KEY, USE_OPENAI

logger = logging.getLogger(__name__)

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI no esta instalado. Ejecuta: pip install openai")


class OpenAIService:
    """Servicio para interactuar con OpenAI API usando Function Calling."""

    _client: Optional["AsyncOpenAI"] = None
    _model: str = "gpt-4o-mini"

    @classmethod
    def initialize(cls) -> bool:
        """Inicializa el cliente async de OpenAI."""
        if not USE_OPENAI or not OPENAI_API_KEY:
            return False
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI no disponible. Instala con: pip install openai")
            return False
        try:
            cls._client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            logger.info("Cliente async de OpenAI inicializado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error inicializando OpenAI: {e}")
            return False

    @classmethod
    def is_available(cls) -> bool:
        return cls._client is not None

    # ------------------------------------------------------------------
    # Function Calling – deteccion de intenciones
    # ------------------------------------------------------------------
    @classmethod
    async def parse_intent(
        cls,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        context_summary: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Usa OpenAI Function Calling para detectar la intencion del usuario.

        Returns:
            Dict con 'intent', 'params' y opcionalmente 'ai_message'
        """
        if not cls._client:
            return None

        from ai.function_schemas import AVAILABLE_FUNCTIONS, FUNCTION_TO_INTENT, SYSTEM_PROMPT

        try:
            # Construir mensajes con contexto conversational
            messages: List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

            if context_summary:
                messages.append({
                    "role": "system",
                    "content": f"Contexto del usuario:\n{context_summary}",
                })

            # Anadir historial de conversation (ultimos mensajes)
            if conversation_history:
                messages.extend(conversation_history[-8:])

            messages.append({"role": "user", "content": user_message})

            response = await cls._client.chat.completions.create(
                model=cls._model,
                messages=messages,
                tools=AVAILABLE_FUNCTIONS,
                tool_choice="required",
                temperature=0.3,
                max_tokens=300,
            )

            choice = response.choices[0]

            # Procesar function call
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                intent = FUNCTION_TO_INTENT.get(function_name, "unknown")

                # Mapear argumentos de container a sub-intenciones
                if function_name == "gestionar_container":
                    accion = arguments.pop("accion", "listar")
                    accion_map = {
                        "create": "container_create",
                        "listar": "container_listar",
                        "editar": "container_editar",
                        "delete": "container_delete",
                    }
                    intent = accion_map.get(accion, "containeres")

                logger.info(f"OpenAI Function Call: {function_name} → intent={intent}, args={arguments}")

                return {
                    "intent": intent,
                    "params": arguments,
                    "function_name": function_name,
                    "ai_message": choice.message.content,
                }

            # Si no hay function call pero hay contenido de texto
            if choice.message.content:
                return {
                    "intent": "greeting",
                    "params": {"mensaje": choice.message.content},
                    "ai_message": choice.message.content,
                }

            return None

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando argumentos de OpenAI: {e}")
            return None
        except Exception as e:
            logger.error(f"Error en OpenAI API: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Generacion de respuestas enriquecidas con IA
    # ------------------------------------------------------------------
    @classmethod
    async def enrich_response(cls, raw_data: str, user_question: str) -> Optional[str]:
        """
        Toma datos crudos del sistema y genera una respuesta natural enriquecida.
        Usado para el asesor financiero para dar insights mas profundos.
        """
        if not cls._client:
            return None

        try:
            response = await cls._client.chat.completions.create(
                model=cls._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Eres un asesor financiero experto. Analiza los datos proporcionados "
                            "y genera insights accionables en espanol. "
                            "Usa formato HTML compatible con Telegram (solo <b>, <i>, <code>). "
                            "Se conciso y directo. Maximo 500 caracteres."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Pregunta: {user_question}\n\nDatos:\n{raw_data}",
                    },
                ],
                temperature=0.5,
                max_tokens=250,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error en enrich_response: {e}")
            return None

