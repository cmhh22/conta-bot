"""
Handler del chatbot - Procesa mensajes de texto libre y los convierte en actions.
Soporta dialogos multi-turno con memoria conversational y enriquecimiento IA.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.decorators import admin_only
from ai.intent_parser import IntentParser, IntentType
from ai.action_executor import ActionExecutor
from ai.openai_service import OpenAIService
from ai.conversation_memory import ConversationMemory
from core.config import USE_OPENAI

logger = logging.getLogger(__name__)


@admin_only
async def chatbot_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa mensajes de texto libre con IA, memoria conversational y dialogos multi-turno."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text.startswith("/"):
        return

    processing_msg = await update.message.reply_text("🤔 Procesando tu solicitud...")

    try:
        # Registrar mensaje del usuario en memoria
        ConversationMemory.add_user_message(user_id, text)

        intent = None
        params = {}
        ai_message = None

        if USE_OPENAI and OpenAIService.is_available():
            # Obtener contexto conversational
            history = ConversationMemory.get_history(user_id, limit=8)
            context_summary = ConversationMemory.get_context_summary(user_id)

            openai_result = await OpenAIService.parse_intent(
                text,
                conversation_history=history,
                context_summary=context_summary,
            )
            if openai_result:
                intent_str = openai_result.get("intent", "unknown")
                try:
                    intent = IntentType(intent_str)
                except ValueError:
                    intent = IntentType.UNKNOWN
                params = openai_result.get("params", {})
                ai_message = openai_result.get("ai_message")
                logger.info(f"OpenAI FC: intent={intent.value}, params={params}")
            else:
                intent, params = IntentParser.parse_intent(text)
                logger.info(f"Fallback reglas: intent={intent.value}")
        else:
            intent, params = IntentParser.parse_intent(text)
            logger.info(f"Parser reglas: intent={intent.value}, params={params}")

        # Handler clarificacion (multi-turno)
        if intent == IntentType.CLARIFICATION:
            pregunta = params.get("pregunta", ai_message or "Podrias darme mas detalles?")
            await processing_msg.delete()
            await update.message.reply_html(f"🤔 {pregunta}")
            ConversationMemory.add_assistant_message(user_id, pregunta, intent="clarification")
            return

        # Handler saludo con respuesta IA personalizada
        if intent == IntentType.GREETING and ai_message:
            await processing_msg.delete()
            await update.message.reply_html(ai_message)
            ConversationMemory.add_assistant_message(user_id, ai_message, intent="greeting", success=True)
            return

        # Ejecutar action
        result = await ActionExecutor.execute_intent(intent, params, user_id)

        await processing_msg.delete()

        response_text = result["message"]

        # Enriquecer respuestas de analisis con IA si esta disponible
        if (
            intent == IntentType.ANALISIS_FINANCIERO
            and result.get("success")
            and USE_OPENAI
            and OpenAIService.is_available()
        ):
            ai_insight = await OpenAIService.enrich_response(response_text, text)
            if ai_insight:
                response_text += f"\n\n🧠 <b>Insight IA:</b>\n{ai_insight}"

        await update.message.reply_html(response_text)

        # Guardar respuesta en memoria
        ConversationMemory.add_assistant_message(
            user_id,
            response_text[:200],  # Truncar para no llenar memoria
            intent=intent.value,
            success=result.get("success", False),
        )

    except Exception as e:
        logger.error(f"Error en chatbot handler: {e}", exc_info=True)
        try:
            await processing_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            "❌ An error occurred al procesar tu mensaje. "
            "Intenta reformular tu solicitud o usa los comandos disponibles."
        )


# Handler exportable
chatbot_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    chatbot_message_handler,
)

