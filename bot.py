"""
Bot principal de Telegram para management financiera.
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

# Configuration de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def cancel_active_conversations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancela cualquier conversacion activa cuando se ejecuta un comando."""
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
    
    # Si el comando actual inicia una conversacion o es cancel/start, no cancelar
    if command in conversation_commands:
        return
    
    # Cancel todas las conversaciones activas
    from telegram.ext import ConversationHandler
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Obtener todos los ConversationHandlers de la aplicacion
    # Los handlers estan en diferentes grupos, necesitamos buscar en todos
    cancelled = False
    for group in context.application.handlers.values():
        for handler in group:
            if isinstance(handler, ConversationHandler):
                # Check whether there is an active conversation for this user
                # The 'conversations' attribute may not be directly available
                # Access it safely
                try:
                    key = (chat_id, user_id)
                    # Try to access conversations safely
                    if hasattr(handler, 'conversations') and handler.conversations.get(key) is not None:
                        # Cancel the conversation
                        handler.conversations.pop(key, None)
                        handler_name = getattr(handler, 'name', 'unknown')
                        logger.info(f"Conversation '{handler_name}' canceled for user {user_id} when executing /{command}")
                        cancelled = True
                except (AttributeError, TypeError):
                    # If conversations cannot be accessed, continue
                    # This can happen in some versions of python-telegram-bot
                    pass
    
    # Notify the user only once
    if cancelled:
        try:
            await update.message.reply_text(
                f"✅ Previous operation canceled. Running command /{command}..."
            )
        except Exception:
            pass  # Si no se puede enviar el mensaje, continuar


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle global bot errors."""
    error = context.error
    logger.error(f"Exception while handling an update: {error}", exc_info=error)
    
    # Handle network errors specifically
    if isinstance(error, NetworkError):
        logger.warning(f"Network error detected: {error}")
        # The bot will retry automatically; only log
        return
    
    if isinstance(error, TimedOut):
        logger.warning(f"Timeout detected: {error}")
        return
    
    if isinstance(error, RetryAfter):
        logger.warning(f"Rate limit detected: {error}. Waiting {error.retry_after} seconds")
        return
    
    # Authentication/authorization errors
    if isinstance(error, Forbidden):
        # Forbidden can happen due to invalid token or blocked bot
        error_msg = str(error).lower()
        if "unauthorized" in error_msg or "invalid token" in error_msg or "token" in error_msg:
            logger.error(f"Authentication error: {error}. Verify TOKEN is valid.")
        else:
            logger.warning(f"Bot blocked by user or missing permissions: {error}")
        return
    
    if isinstance(error, BadRequest):
        logger.warning(f"Invalid request to Telegram API: {error}")
        return
    
    # General connection errors
    if isinstance(error, (ConnectionError, OSError)):
        logger.warning(f"Connection error: {error}. The bot will retry automatically.")
        return
    
    # Other Telegram errors
    if isinstance(error, TelegramError):
        logger.warning(f"Telegram error: {error}")
        # Try notifying the user if update is valid
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An error occurred while processing your request. "
                    "Please try again in a few moments."
                )
            except Exception:
                logger.error("Could not send error message to user")
        return
    
    # For other errors, try notifying the user if update is valid
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An error occurred while processing your request. "
                "Please try again in a few moments."
            )
        except Exception:
            # If message cannot be sent, log only
            logger.error("Could not send error message to user")


def main() -> None:
    """Main function that starts the bot."""
    # Initialize database
    initialize_database()
    
    # Initialize OpenAI if configured
    from ai.openai_service import OpenAIService
    if OpenAIService.initialize():
        logger.info("🤖 OpenAI enabled - Using advanced AI for natural language processing")
    else:
        logger.info("📝 Using basic rule-based parser for natural language processing")
    
    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Define environment variable "
            "TELEGRAM_BOT_TOKEN or create config_secret.py with TOKEN and ADMIN_USER_IDS."
        )
    
    # Configure bot command menu
    async def post_init(app: Application) -> None:
        """Configure bot commands after initialization."""
        commands = [
            BotCommand("start", "Main bot menu"),
            BotCommand("contenedores", "Container management"),
            BotCommand("proveedores", "Supplier management"),
            BotCommand("vendedores", "Seller management"),
            BotCommand("almacenes", "Warehouse management"),
            BotCommand("productos", "Product management"),
            BotCommand("cajas", "Cash box management"),
            BotCommand("cajas_externas", "External cash box management (USA)"),
            BotCommand("mover_producto", "Move products from container to warehouse"),
            BotCommand("mover_almacen", "Move products between warehouses"),
            BotCommand("consignar_almacen", "Consign products from warehouse to seller"),
            BotCommand("mover_consignacion", "Move consignment from one seller to another"),
            BotCommand("pagar_consignacion", "Pay seller consignment"),
            BotCommand("agregar_producto_contenedor", "Add products to a container"),
            BotCommand("productos_contenedor", "View products in a container"),
            BotCommand("inventario_almacen", "View warehouse inventory"),
            BotCommand("resumen_logistica", "View logistics summary"),
            BotCommand("balance", "View balances for all cash boxes"),
            BotCommand("ingreso", "Record incoming cash"),
            BotCommand("gasto", "Record outgoing cash"),
            BotCommand("traspaso", "Transfer between cash boxes (interactive)"),
            BotCommand("cambio", "Transfer between cash boxes"),
            BotCommand("cambio_moneda", "Convert currency inside one cash box"),
            BotCommand("transferencia_externa", "Transfer money to external cash box (USA)"),
            BotCommand("deuda_proveedor", "Generate supplier debt"),
            BotCommand("pago_proveedor", "Pay supplier debt (interactive)"),
            BotCommand("pago_prov", "Pay supplier debt (interactive)"),
            BotCommand("deudas", "View pending debt status"),
            BotCommand("historial", "View transaction history"),
            BotCommand("stock", "View current inventory"),
            BotCommand("venta", "Record a sale"),
            BotCommand("entrada", "Record product intake"),
            BotCommand("ganancia", "View profit report"),
            BotCommand("exportar", "Export transactions to CSV"),
        ]
        await app.bot.set_my_commands(commands)
        logger.info("Comandos del bot configurados correctamente")
    
    # Create aplicacion con post_init
    application = Application.builder().token(TOKEN).post_init(post_init).build()
    
    # Agregar error handler global para manejar errores de red y otros errores
    application.add_error_handler(error_handler)
    
    # Handler para cancelar conversaciones activas cuando se ejecuta un comando
    # Debe ir ANTES de los ConversationHandlers para que se ejecute primero
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(filters.COMMAND, cancel_active_conversations), group=-1)
    
    # --- MENU PRINCIPAL Y NAVEGACION ---
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
    
    # --- MENU Y NAVEGACION (despues de ConversationHandlers) ---
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
    
    # Logistica
    application.add_handler(CommandHandler("productos_contenedor", productos_contenedor_command))
    application.add_handler(CommandHandler("inventario_almacen", inventario_almacen_command))
    application.add_handler(CallbackQueryHandler(inventario_almacen_callback, pattern=r"^inv_alm:\d+$"))
    application.add_handler(CommandHandler("resumen_logistica", resumen_logistica_command))
    
    # --- CHATBOT DE IA (debe ir al final para no interferir con comandos) ---
    application.add_handler(chatbot_handler)
    
    logger.info("Bot iniciado correctamente. Presiona CTRL+C para detenerlo.")
    logger.info("🤖 Chatbot de IA activado - Los usuarios pueden escribir en lenguaje natural")
    
    # Configure polling con mejor manejo de errores
    try:
        application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,  # Ignorar actualizaciones pendientes al iniciar
            close_loop=False  # No cerrar el loop al detener
        )
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error critico al ejecutar el bot: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
