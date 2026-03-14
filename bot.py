"""
Bot principal de Telegram para gestión financiera.
"""
import logging
from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import (
    NetworkError, TimedOut, RetryAfter, TelegramError, 
    Forbidden, BadRequest
)
from core.config import TOKEN
from database.init_db import initialize_database
from handlers.contabilidad_handlers import (
    set_tasa_command, ingreso_command, gasto_command, balance_command,
    cambio_command, pago_proveedor_command, pago_vendedor_command,
    deudas_command, historial_command, exportar_command,
)
from handlers.inventario_handlers import (
    entrada_command, stock_command, venta_command, ganancia_command,
    consignar_command, stock_consignado_command
)
from handlers.contenedores_handlers import contenedores_conv_handler
from handlers.proveedores_handlers import proveedores_conv_handler
from handlers.vendedores_handlers import vendedores_conv_handler
from handlers.almacenes_handlers import almacenes_conv_handler
from handlers.productos_handlers import productos_conv_handler
from handlers.cajas_handlers import cajas_conv_handler
from handlers.cajas_externas_handlers import cajas_externas_conv_handler
from handlers.logistica_handlers import (
    productos_contenedor_command,
    inventario_almacen_command,
    inventario_almacen_callback,
    mover_producto_conv_handler,
    agregar_producto_conv_handler,
    mover_almacen_conv_handler,
    consignar_almacen_conv_handler,
    mover_consignacion_conv_handler,
    pagar_consignacion_conv_handler,
    resumen_logistica_command,
)
from handlers.menu_handlers import start_command, menu_callback, menu_query_handler, contabilidad_query_handler
from handlers.form_handlers import ingreso_conv_handler, gasto_conv_handler, traspaso_conv_handler, deuda_proveedor_conv_handler, cambio_moneda_conv_handler, transferencia_externa_conv_handler, pago_proveedor_conv_handler
from ai.chatbot_handler import chatbot_handler

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def cancel_active_conversations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancela cualquier conversación activa cuando se ejecuta un comando."""
    if not update.message or not update.message.text:
        return
    
    # Solo procesar comandos (que empiezan con /)
    if not update.message.text.startswith('/'):
        return
    
    # Obtener el nombre del comando
    command = update.message.text.split()[0].replace('/', '').lower()
    
    # Lista de comandos que inician conversaciones (no cancelar si es el mismo comando)
    conversation_commands = [
        'ingreso', 'gasto', 'traspaso', 'deuda_proveedor', 'cambio_moneda', 'pago_proveedor', 'pago_prov',
        'contenedores', 'proveedores', 'vendedores', 'almacenes', 'productos', 'cajas',
        'mover_producto', 'agregar_producto_contenedor', 'mover_almacen',
        'consignar_almacen', 'mover_consignacion', 'pagar_consignacion', 'start', 'cancel'
    ]
    
    # Si el comando actual inicia una conversación o es cancel/start, no cancelar
    if command in conversation_commands:
        return
    
    # Cancelar todas las conversaciones activas
    from telegram.ext import ConversationHandler
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Obtener todos los ConversationHandlers de la aplicación
    # Los handlers están en diferentes grupos, necesitamos buscar en todos
    cancelled = False
    for group in context.application.handlers.values():
        for handler in group:
            if isinstance(handler, ConversationHandler):
                # Verificar si hay una conversación activa para este usuario
                # El atributo 'conversations' puede no estar disponible directamente
                # Intentamos acceder de forma segura
                try:
                    key = (chat_id, user_id)
                    # Intentar acceder a las conversaciones de forma segura
                    if hasattr(handler, 'conversations') and handler.conversations.get(key) is not None:
                        # Cancelar la conversación
                        handler.conversations.pop(key, None)
                        handler_name = getattr(handler, 'name', 'unknown')
                        logger.info(f"Conversación '{handler_name}' cancelada para usuario {user_id} al ejecutar comando /{command}")
                        cancelled = True
                except (AttributeError, TypeError):
                    # Si no se puede acceder a las conversaciones, simplemente continuar
                    # Esto puede ocurrir en algunas versiones de python-telegram-bot
                    pass
    
    # Notificar al usuario solo una vez
    if cancelled:
        try:
            await update.message.reply_text(
                f"✅ Operación anterior cancelada. Ejecutando comando /{command}..."
            )
        except Exception:
            pass  # Si no se puede enviar el mensaje, continuar


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja errores globales del bot."""
    error = context.error
    logger.error(f"Exception while handling an update: {error}", exc_info=error)
    
    # Manejar errores de red específicamente
    if isinstance(error, NetworkError):
        logger.warning(f"Error de red detectado: {error}")
        # El bot reintentará automáticamente, solo logueamos
        return
    
    if isinstance(error, TimedOut):
        logger.warning(f"Timeout detectado: {error}")
        return
    
    if isinstance(error, RetryAfter):
        logger.warning(f"Rate limit detectado: {error}. Esperando {error.retry_after} segundos")
        return
    
    # Errores de autenticación/autorización
    if isinstance(error, Forbidden):
        # Forbidden puede ser por token inválido o bot bloqueado
        error_msg = str(error).lower()
        if "unauthorized" in error_msg or "invalid token" in error_msg or "token" in error_msg:
            logger.error(f"Error de autenticación: {error}. Verifica que el TOKEN sea válido.")
        else:
            logger.warning(f"Bot bloqueado por usuario o sin permisos: {error}")
        return
    
    if isinstance(error, BadRequest):
        logger.warning(f"Petición inválida a la API de Telegram: {error}")
        return
    
    # Errores de conexión generales
    if isinstance(error, (ConnectionError, OSError)):
        logger.warning(f"Error de conexión: {error}. El bot reintentará automáticamente.")
        return
    
    # Para otros errores de Telegram
    if isinstance(error, TelegramError):
        logger.warning(f"Error de Telegram: {error}")
        # Para otros errores, intentar notificar al usuario si hay un update válido
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Ocurrió un error al procesar tu solicitud. "
                    "Por favor, intenta nuevamente en unos momentos."
                )
            except Exception:
                logger.error("No se pudo enviar mensaje de error al usuario")
        return
    
    # Para otros errores, intentar notificar al usuario si hay un update válido
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error al procesar tu solicitud. "
                "Por favor, intenta nuevamente en unos momentos."
            )
        except Exception:
            # Si no podemos enviar el mensaje, solo logueamos
            logger.error("No se pudo enviar mensaje de error al usuario")


def main() -> None:
    """Función principal que inicia el bot."""
    # Inicializar base de datos
    initialize_database()
    
    # Inicializar OpenAI si está configurado
    from ai.openai_service import OpenAIService
    if OpenAIService.initialize():
        logger.info("🤖 OpenAI activado - Usando IA avanzada para procesamiento de lenguaje natural")
    else:
        logger.info("📝 Usando parser de reglas básico para procesamiento de lenguaje natural")
    
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN no está configurado. Define la variable de entorno "
            "TELEGRAM_BOT_TOKEN o crea un archivo config_secret.py con TOKEN y ADMIN_USER_IDS."
        )
    
    # Configurar menú de comandos del bot
    async def post_init(app: Application) -> None:
        """Configura los comandos del bot después de la inicialización."""
        commands = [
            BotCommand("start", "Menú principal del bot"),
            BotCommand("contenedores", "Gestión de contenedores"),
            BotCommand("proveedores", "Gestión de proveedores"),
            BotCommand("vendedores", "Gestión de vendedores"),
            BotCommand("almacenes", "Gestión de almacenes"),
            BotCommand("productos", "Gestión de productos"),
            BotCommand("cajas", "Gestión de cajas"),
            BotCommand("cajas_externas", "Gestionar cajas externas (USA)"),
            BotCommand("mover_producto", "Mover productos de contenedor a almacén"),
            BotCommand("mover_almacen", "Mover productos entre almacenes"),
            BotCommand("consignar_almacen", "Consignar productos desde almacén a vendedor"),
            BotCommand("mover_consignacion", "Mover consignación de un vendedor a otro"),
            BotCommand("pagar_consignacion", "Pagar consignación de un vendedor"),
            BotCommand("agregar_producto_contenedor", "Agregar productos a un contenedor"),
            BotCommand("productos_contenedor", "Ver productos de un contenedor"),
            BotCommand("inventario_almacen", "Ver inventario de un almacén"),
            BotCommand("resumen_logistica", "Ver resumen de logística"),
            BotCommand("balance", "Ver saldos de todas las cajas"),
            BotCommand("ingreso", "Registrar entrada de dinero"),
            BotCommand("gasto", "Registrar salida de dinero"),
            BotCommand("traspaso", "Traspaso entre cajas (interactivo)"),
            BotCommand("cambio", "Traspaso entre cajas"),
            BotCommand("cambio_moneda", "Cambiar moneda dentro de una caja"),
            BotCommand("transferencia_externa", "Transferir dinero a caja externa (USA)"),
            BotCommand("deuda_proveedor", "Generar deuda con proveedor"),
            BotCommand("pago_proveedor", "Pagar deuda a proveedor (interactivo)"),
            BotCommand("pago_prov", "Pagar deuda a proveedor (interactivo)"),
            BotCommand("deudas", "Ver estado de deudas pendientes"),
            BotCommand("historial", "Ver historial de movimientos"),
            BotCommand("stock", "Ver inventario actual"),
            BotCommand("venta", "Registrar una venta"),
            BotCommand("entrada", "Registrar entrada de mercancía"),
            BotCommand("ganancia", "Ver reporte de ganancias"),
            BotCommand("exportar", "Exportar movimientos a CSV"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("Comandos del bot configurados correctamente")
    
    # Crear aplicación con post_init
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Agregar error handler global para manejar errores de red y otros errores
    application.add_error_handler(error_handler)
    
    # Handler para cancelar conversaciones activas cuando se ejecuta un comando
    # Debe ir ANTES de los ConversationHandlers para que se ejecute primero
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.COMMAND, cancel_active_conversations), group=-1)
    
    # --- MENÚ PRINCIPAL Y NAVEGACIÓN ---
    application.add_handler(CommandHandler("start", start_command))
    
    # --- CONTENEDORES, PROVEEDORES Y ALMACENES (deben ir antes del menu_query_handler) ---
    application.add_handler(contenedores_conv_handler)
    application.add_handler(proveedores_conv_handler)
    application.add_handler(vendedores_conv_handler)
    application.add_handler(almacenes_conv_handler)
    application.add_handler(productos_conv_handler)
    application.add_handler(cajas_conv_handler)
    application.add_handler(cajas_externas_conv_handler)
    application.add_handler(mover_producto_conv_handler)
    application.add_handler(agregar_producto_conv_handler)
    application.add_handler(mover_almacen_conv_handler)
    application.add_handler(consignar_almacen_conv_handler)
    application.add_handler(mover_consignacion_conv_handler)
    application.add_handler(pagar_consignacion_conv_handler)
    
    # --- MENÚ Y NAVEGACIÓN (después de ConversationHandlers) ---
    application.add_handler(menu_query_handler)
    application.add_handler(contabilidad_query_handler)
    
    # --- FORMULARIOS INTERACTIVOS ---
    application.add_handler(ingreso_conv_handler)
    application.add_handler(gasto_conv_handler)
    application.add_handler(traspaso_conv_handler)
    application.add_handler(deuda_proveedor_conv_handler)
    application.add_handler(cambio_moneda_conv_handler)
    application.add_handler(transferencia_externa_conv_handler)
    application.add_handler(pago_proveedor_conv_handler)
    
    # --- REGISTRO DE MANEJADORES (comandos tradicionales - compatibilidad) ---
    # Contabilidad
    application.add_handler(CommandHandler("set_tasa", set_tasa_command))
    # Nota: /ingreso y /gasto ahora se manejan completamente por sus ConversationHandlers
    # application.add_handler(CommandHandler("gasto", gasto_command))  # Deshabilitado - usa gasto_conv_handler
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("cambio", cambio_command))
    application.add_handler(CommandHandler("pago_vendedor", pago_vendedor_command))
    # application.add_handler(CommandHandler("pago_proveedor", pago_proveedor_command))  # Deshabilitado - usa pago_proveedor_conv_handler
    application.add_handler(CommandHandler("deudas", deudas_command))
    application.add_handler(CommandHandler("historial", historial_command))
    application.add_handler(CommandHandler("exportar", exportar_command))
    
    # Inventario
    application.add_handler(CommandHandler("entrada", entrada_command))
    application.add_handler(CommandHandler("stock", stock_command))
    application.add_handler(CommandHandler("venta", venta_command))
    application.add_handler(CommandHandler("ganancia", ganancia_command))
    application.add_handler(CommandHandler("consignar", consignar_command))
    application.add_handler(CommandHandler("stock_consignado", stock_consignado_command))
    
    # Logística
    application.add_handler(CommandHandler("productos_contenedor", productos_contenedor_command))
    application.add_handler(CommandHandler("inventario_almacen", inventario_almacen_command))
    application.add_handler(CallbackQueryHandler(inventario_almacen_callback, pattern=r"^inv_alm:\d+$"))
    application.add_handler(CommandHandler("resumen_logistica", resumen_logistica_command))
    
    # --- CHATBOT DE IA (debe ir al final para no interferir con comandos) ---
    application.add_handler(chatbot_handler)
    
    logger.info("Bot iniciado correctamente. Presiona CTRL+C para detenerlo.")
    logger.info("🤖 Chatbot de IA activado - Los usuarios pueden escribir en lenguaje natural")
    
    # Configurar polling con mejor manejo de errores
    try:
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,  # Ignorar actualizaciones pendientes al iniciar
            close_loop=False  # No cerrar el loop al detener
        )
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error crítico al ejecutar el bot: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
