import logging
from typing import Dict, Any, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from settings import ADMIN_USER_IDS
from .db_utils import get_db_connection, ContainerManager

logger = logging.getLogger(__name__)

# Estados de la conversacion
MENU, CREAR_NOMBRE, EDIT_NOMBRE, CONFIRM_DELETE = range(4)

# Helpers UI

def _main_menu_kb() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="cont:create"),
            InlineKeyboardButton("📋 Listar", callback_data="cont:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="cont:close")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def _ensure_admin(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        # depending on entry type
        if update.message:
            await update.message.reply_text("⛔ No tienes permiso.")
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("⛔ No tienes permiso.")
        return False
    return True

# Render listado con botones de editar/delete
async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_db_connection() as conn:
        rows = ContainerManager.listar(conn)
    if not rows:
        text = "📦 <b>Contenedores</b>\n\nStill no hay contenedores registrados."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("➕ Create", callback_data="cont:create")],
                                   [InlineKeyboardButton("⬅️ Back", callback_data="cont:back")]])
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_html(text, reply_markup=kb)
        return

    text = "📦 <b>Contenedores</b>\n\nSelect una action para cada item:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for r in rows:
        cont_id = r["id"]
        nombre = r["nombre"]
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"cont:edit:{cont_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"cont:del:{cont_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cont:back")])
    kb = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await update.message.reply_html(text, reply_markup=kb)

# Entry point
async def contenedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _ensure_admin(update):
        return ConversationHandler.END
    msg = (
        "🧰 <b>Management de Contenedores</b>\n\n"
        "Administra tus contenedores. Usa el menu de abajo."
    )
    if update.message:
        await update.message.reply_html(msg, reply_markup=_main_menu_kb())
    else:
        await update.callback_query.edit_message_text(msg, parse_mode="HTML", reply_markup=_main_menu_kb())
    return MENU

# Manejo de botones del menu
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _ensure_admin(update):
        return ConversationHandler.END
    q = update.callback_query
    await q.answer()
    data = q.data or ""

    if data == "cont:create":
        await q.edit_message_text(
            "🆕 <b>Nuevo Contenedor</b>\n\nSend el <b>nombre</b> para el contenedor:", parse_mode="HTML"
        )
        return CREAR_NOMBRE

    if data == "cont:list":
        await _render_list(update, context)
        return MENU

    if data == "cont:back":
        return await contenedores_entry(update, context)

    if data == "cont:close":
        await q.edit_message_text("✅ Closed.")
        return ConversationHandler.END

    # Actions por item
    if data.startswith("cont:edit:"):
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_edit_id"] = cont_id
        with get_db_connection() as conn:
            row = ContainerManager.get_by_id(conn, cont_id)
        if not row:
            await q.edit_message_text("❌ Contenedor not found.")
            return MENU
        await q.edit_message_text(
            f"✏️ <b>Renombrar Contenedor</b>\n\nActual: <code>{row['nombre']}</code>\nSend el <b>nuevo nombre</b>:",
            parse_mode="HTML",
        )
        return EDIT_NOMBRE

    if data.startswith("cont:del:"):
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_del_id"] = cont_id
        with get_db_connection() as conn:
            row = ContainerManager.get_by_id(conn, cont_id)
        if not row:
            await q.edit_message_text("❌ Contenedor not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, borrar", callback_data="cont:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="cont:cancel")]
        ])
        await q.edit_message_text(
            f"⚠️ <b>Confirmar deletion</b>\n\nVas a borrar: <code>{row['nombre']}</code>\nEsta action no se puede deshacer.",
            parse_mode="HTML",
            reply_markup=kb,
        )
        return CONFIRM_DELETE

    if data == "cont:delok":
        cont_id = context.user_data.get("cont_del_id")
        if cont_id is None:
            await q.edit_message_text("❌ No elemento para delete.")
            return MENU
        try:
            with get_db_connection() as conn:
                ContainerManager.delete(conn, int(cont_id))
            await q.edit_message_text("🗑️ Contenedor deleted correctamente.")
        except Exception as e:
            logger.error("Error eliminando contenedor: %s", e)
            await q.edit_message_text("❌ No se pudo delete. Intenta de nuevo.")
        return MENU

    if data == "cont:cancel":
        await _render_list(update, context)
        return MENU

    # Default
    return MENU

# Recibir nombre para create
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _ensure_admin(update):
        return ConversationHandler.END
    nombre = (update.message.text or "").strip()
    if not nombre:
        await update.message.reply_text("❌ El nombre no puede estar empty. Send un nombre valid.")
        return CREAR_NOMBRE
    try:
        with get_db_connection() as conn:
            _new_id = ContainerManager.create(conn, nombre)
        await update.message.reply_html(
            f"✅ <b>Creado</b>\n\nContenedor: <code>{nombre}</code>")
        # Back al menu
        await update.message.reply_html(
            "What would you like to do now?", reply_markup=_main_menu_kb()
        )
        return MENU
    except Exception as e:
        msg = str(e)
        if "UNIQUE constraint failed" in msg or "UNIQUE" in msg:
            await update.message.reply_text("⚠️ Ya existe un contenedor con ese nombre. Usa otro nombre.")
            return CREAR_NOMBRE
        logger.error("Error creando contenedor: %s", e)
        await update.message.reply_text("❌ An error occurred al create. Try again.")
        return CREAR_NOMBRE

# Recibir nuevo nombre para editar
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _ensure_admin(update):
        return ConversationHandler.END
    cont_id = context.user_data.get("cont_edit_id")
    if cont_id is None:
        await update.message.reply_text("❌ No contenedor en edicion.")
        return MENU
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await update.message.reply_text("❌ El nombre no puede estar empty. Send un nombre valid.")
        return EDIT_NOMBRE
    try:
        with get_db_connection() as conn:
            ContainerManager.update(conn, int(cont_id), nuevo_nombre)
        await update.message.reply_html(
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>")
        # limpiar estado
        context.user_data.pop("cont_edit_id", None)
        # mostrar lista de nuevo
        await _render_list(update, context)
        return MENU
    except Exception as e:
        msg = str(e)
        if "UNIQUE constraint failed" in msg or "UNIQUE" in msg:
            await update.message.reply_text("⚠️ Ya existe un contenedor con ese nombre. Usa otro nombre.")
            return EDIT_NOMBRE
        logger.error("Error actualizando contenedor: %s", e)
        await update.message.reply_text("❌ An error occurred al update. Try again.")
        return EDIT_NOMBRE

# Cancelacion por mensaje (si el usuario escribe /cancel por ejemplo)
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("✅ Operation cancelada.")
    return ConversationHandler.END

# ConversationHandler exportable
contenedores_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("contenedores", contenedores_entry)],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:.*"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:.*"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="contenedores_conversation",
    persistent=False,
)
