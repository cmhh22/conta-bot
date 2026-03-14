"""
Handlers for cash box management (full CRUD).
"""
import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils.decorators import admin_only
from services.cajas_service import CajaService
from core.config import VALID_MONEDAS

logger = logging.getLogger(__name__)

# Conversation states
MENU, CREAR_NOMBRE, CREAR_DESCRIPCION, EDIT_MENU, EDIT_NOMBRE, EDIT_DESCRIPCION, CONFIRM_DELETE = range(7)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Build the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="caja:create"),
            InlineKeyboardButton("📋 Listar", callback_data="caja:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="caja:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the cash box list."""
    from utils.telegram_helpers import reply_html
    
    cajas = CajaService.listar()
    
    if not cajas:
        text = "💰 <b>Cash Boxes</b>\n\nNo cash boxes are registered yet."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create", callback_data="caja:create")],
            [InlineKeyboardButton("⬅️ Back", callback_data="caja:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "💰 <b>Cajas</b>\n\n"
    keyboard: List[List[InlineKeyboardButton]] = []
    for caja in cajas:
        caja_id = caja["id"]
        nombre = caja["nombre"]
        saldos = caja.get("saldos", {})
        
        # Format balances for display
        saldos_text = ""
        if saldos:
            saldos_list = []
            for moneda, monto in saldos.items():
                if monto != 0:
                    saldos_list.append(f"{monto:.2f} {moneda.upper()}")
            if saldos_list:
                saldos_text = " | " + " | ".join(saldos_list)
        else:
                saldos_text = " | No balance"
        
        text += f"<b>{nombre}</b>{saldos_text}\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"caja:edit:{caja_id}"),
            InlineKeyboardButton("📊 Detalles", callback_data=f"caja:detalles:{caja_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"caja:del:{caja_id}"),
        ])
    text += "\nSelect an action:"
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="caja:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def cajas_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for cash box management."""
    from utils.telegram_helpers import reply_html
    
    # Clear any residual data from previous conversations
    keys_to_remove = [
        "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "💰 <b>Cash Box Management</b>\n\n"
        "Manage your cash boxes. Use the menu below."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


@admin_only
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle menu callbacks."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "caja:create":
        await reply_html(
            update,
            "🆕 <b>New Cash Box</b>\n\nSend the cash box <b>name</b>:"
        )
        return CREAR_NOMBRE
    
    if data == "caja:list":
        await _render_list(update, context)
        return MENU
    
    if data == "caja:back":
        return await cajas_entry(update, context)
    
    if data == "caja:close":
        # Clear all conversation data
        keys_to_remove = [
            "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Closed.")
        return ConversationHandler.END
    
    # Per-item actions
    if data.startswith("caja:detalles:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Cash box not found.")
            return MENU
        
        saldos = caja.get("saldos", {})
        descripcion_text = caja.get('descripcion') or "No description"
        
        text = f"📊 <b>Cash Box Details</b>\n\n"
        text += f"Name: <code>{caja['nombre']}</code>\n"
        text += f"Description: {descripcion_text}\n\n"
        text += f"<b>Balances:</b>\n"
        
        if saldos:
            for moneda in VALID_MONEDAS:
                saldo = saldos.get(moneda, 0)
                text += f"• {moneda.upper()}: <b>{saldo:.2f}</b>\n"
        else:
            text += "No transactions recorded.\n"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit", callback_data=f"caja:edit:{caja_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="caja:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return MENU
    
    if data.startswith("caja:edit:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["caja_edit_id"] = caja_id
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Cash box not found.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Name", callback_data="caja:edit_nombre")],
            [InlineKeyboardButton("📝 Edit Description", callback_data="caja:edit_descripcion")],
            [InlineKeyboardButton("⬅️ Back", callback_data="caja:back")]
        ])
        descripcion_text = caja.get('descripcion') or "No description"
        await reply_html(
            update,
            f"✏️ <b>Edit Cash Box</b>\n\n"
            f"Name: <code>{caja['nombre']}</code>\n"
            f"Description: {descripcion_text}",
            reply_markup=kb
        )
        return EDIT_MENU
    
    if data == "caja:edit_nombre":
        caja_id = context.user_data.get("caja_edit_id")
        if not caja_id:
            await reply_text(update, "❌ No cash box is currently being edited.")
            return MENU
        caja = CajaService.obtener_por_id(caja_id)
        await reply_html(
            update,
            f"✏️ <b>Rename Cash Box</b>\n\n"
            f"Current: <code>{caja['nombre']}</code>\n"
            f"Send the <b>new name</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "caja:edit_descripcion":
        caja_id = context.user_data.get("caja_edit_id")
        if not caja_id:
            await reply_text(update, "❌ No cash box is currently being edited.")
            return MENU
        caja = CajaService.obtener_por_id(caja_id)
        await reply_html(
            update,
            f"📝 <b>Edit Description</b>\n\n"
            f"Cash box: <code>{caja['nombre']}</code>\n"
            f"Current description: {caja.get('descripcion') or 'No description'}\n\n"
            f"Send the <b>new description</b> (or 'none' to clear):"
        )
        return EDIT_DESCRIPCION
    
    if data.startswith("caja:del:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["caja_del_id"] = caja_id
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Cash box not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, delete", callback_data="caja:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="caja:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirm deletion</b>\n\n"
            f"You are about to delete: <code>{caja['nombre']}</code>\n"
            f"This action cannot be undone.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "caja:delok":
        caja_id = context.user_data.get("caja_del_id")
        if caja_id is None:
            await reply_text(update, "❌ No item selected for deletion.")
            await _render_list(update, context)
            return MENU
        try:
            CajaService.delete(int(caja_id))
            context.user_data.pop("caja_del_id", None)
            await reply_text(update, "🗑️ Cash box deleted successfully.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error deleting cash box: {e}", exc_info=True)
            await reply_text(update, "❌ Could not delete. Try again.")
            await _render_list(update, context)
        return MENU
    
    if data == "caja:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the name for creating a cash box."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return CREAR_NOMBRE
    
    context.user_data["caja_nombre"] = nombre
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n\n"
        f"Send the <b>description</b> (optional, or 'none' to skip):"
    )
    return CREAR_DESCRIPCION


@admin_only
async def create_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the description for creating a cash box."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_DESCRIPCION
    
    descripcion = (update.message.text or "").strip()
    nombre = context.user_data.get("caja_nombre")
    
    if not nombre:
        await reply_text(update, "❌ Error: incomplete data. Start again.")
        return ConversationHandler.END
    
    # If user writes an explicit empty marker, do not store description
    if descripcion.lower() in ('sin', 'none', 'no description'):
        descripcion = None
    
    try:
        resultado = CajaService.create(nombre, descripcion)
        await reply_html(
            update,
            f"✅ <b>Created</b>\n\nCash box: <code>{nombre}</code>"
        )
        context.user_data.pop("caja_nombre", None)
        context.user_data.pop("caja_descripcion", None)
        await reply_html(
            update,
            "What would you like to do now?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A cash box with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creating cash box: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while creating. Please try again.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the new name to edit a cash box."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    caja_id = context.user_data.get("caja_edit_id")
    if caja_id is None:
        await reply_text(update, "❌ No cash box is currently being edited.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return EDIT_NOMBRE
    
    try:
        caja = CajaService.obtener_por_id(caja_id)
        CajaService.update(int(caja_id), nuevo_nombre, caja.get('descripcion'))
        await reply_html(
            update,
            f"✅ <b>Updated</b>\n\nNew name: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("caja_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A cash box with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error updating cash box: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while updating. Please try again.")
        return EDIT_NOMBRE


@admin_only
async def edit_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the new description to edit a cash box."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    caja_id = context.user_data.get("caja_edit_id")
    if caja_id is None:
        await reply_text(update, "❌ No cash box is currently being edited.")
        return MENU
    
    nueva_descripcion = (update.message.text or "").strip()
    
    # If user writes an explicit empty marker, clear description
    if nueva_descripcion.lower() in ('sin', 'none', 'no description'):
        nueva_descripcion = None
    
    try:
        caja = CajaService.obtener_por_id(caja_id)
        CajaService.update(int(caja_id), caja['nombre'], nueva_descripcion)
        await reply_html(
            update,
            f"✅ <b>Updated</b>\n\nDescription updated."
        )
        context.user_data.pop("caja_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        await reply_text(update, f"❌ {e}")
        return EDIT_DESCRIPCION
    except Exception as e:
        logger.error(f"Error updating cash box: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while updating. Please try again.")
        return EDIT_DESCRIPCION


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    from utils.telegram_helpers import reply_text
    
    # Clear all conversation data
    keys_to_remove = [
        "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
    return ConversationHandler.END


# ConversationHandler exportable
cajas_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("cajas", cajas_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        CREAR_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_descripcion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja:(edit_nombre|edit_descripcion|back)"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        EDIT_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_descripcion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="cajas_conversation",
    persistent=False,
)

