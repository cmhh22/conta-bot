"""
Handlers para el main menu y navigation.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.decorators import admin_only
from utils.form_helpers import (
    create_main_menu_keyboard,
    create_contabilidad_menu_keyboard,
    create_inventario_menu_keyboard,
    create_reportes_menu_keyboard
)
from handlers.contabilidad_handlers import (
    balance_command, deudas_command, historial_command, exportar_command
)
from handlers.inventario_handlers import (
    stock_command, ganancia_command, stock_consignado_command
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start - Show el main menu."""
    # Verificar permisos pero no bloquear, solo mostrar mensaje diferente
    user_id = update.effective_user.id
    from core.config import ADMIN_USER_IDS
    
    if user_id not in ADMIN_USER_IDS:
        msg = (
            "👋 <b>Bienvenido</b>\n\n"
            "⛔ No tienes permisos para usar este bot.\n"
            "Contacta al administrador para obtener acceso."
        )
        await update.message.reply_html(msg)
        return
    
    msg = (
        "👋 <b>Bienvenido al Sistema de Management Financiera</b>\n\n"
        "Select aa opcion del menu para comenzar:"
    )
    await update.message.reply_html(msg, reply_markup=create_main_menu_keyboard())


@admin_only
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks del main menu."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    
    if data == "menu:main":
        msg = (
            "👋 <b>Main Menu</b>\n\n"
            "Select aa opcion:"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=create_main_menu_keyboard())
    
    elif data == "menu:contabilidad":
        msg = (
            "💰 <b>Contabilidad</b>\n\n"
            "Gestiona ingresos, gastos y movimientos de dinero:"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=create_contabilidad_menu_keyboard())
    
    elif data == "menu:inventario":
        msg = (
            "📦 <b>Inventario</b>\n\n"
            "Gestiona productos, stock y ventas:"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=create_inventario_menu_keyboard())
    
    elif data == "menu:reportes":
        msg = (
            "📊 <b>Reportes</b>\n\n"
            "Consulta reportes y estadisticas:"
        )
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=create_reportes_menu_keyboard())
    
    elif data == "menu:deudas":
        # Redirigir al comando de deudas
        await deudas_command(update, context)
    
    elif data == "menu:containeres":
        # Este callback es manejado por el ConversationHandler de containeres
        # que se registra antes de este handler, ayes que no deberia llegar aqui
        # pero por si acaso, respondemos al callback
        pass
    
    elif data == "menu:config":
        msg = (
            "⚙️ <b>Configuration</b>\n\n"
            "Opciones de configuration:\n\n"
            "• <code>/set_tasa 1 [tasa]</code> - Establecer tasa USD-CUP\n"
            "• <code>/balance</code> - Ver balance\n"
            "• <code>/historial [days]</code> - Ver historial"
        )
        kb = create_main_menu_keyboard()
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
    
    # Redirecciones desde submenus
    elif data == "cont:ingreso":
        from handlers.form_handlers import ingreso_form_entry
        await ingreso_form_entry(update, context)
    
    elif data == "cont:gasto":
        from handlers.form_handlers import gasto_form_entry
        await gasto_form_entry(update, context)
    
    elif data == "cont:balance":
        await balance_command(update, context)
    
    elif data == "inv:stock":
        await stock_command(update, context)
    
    elif data == "inv:ganancia":
        await ganancia_command(update, context)
    
    elif data == "rep:balance":
        await balance_command(update, context)
    
    elif data == "rep:historial":
        await historial_command(update, context)
    
    elif data == "rep:ganancia":
        await ganancia_command(update, context)
    
    elif data == "rep:exportar":
        await exportar_command(update, context)
    elif data.startswith("export:"):
        from handlers.contabilidad_handlers import export_callback
        await export_callback(update, context)


# Handlers exportables
# Excluir menu:containeres porque lo maneja el ConversationHandler
menu_query_handler = CallbackQueryHandler(menu_callback, pattern=r"^menu:(?!containeres$)")
contabilidad_query_handler = CallbackQueryHandler(menu_callback, pattern=r"^(cont|inv|rep|export):")

