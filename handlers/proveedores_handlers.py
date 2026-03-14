"""
Handlers for supplier management (full CRUD).
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
from services.proveedores_service import ProveedorService

logger = logging.getLogger(__name__)

# Conversation states
MENU, CREAR_NOMBRE, EDIT_NOMBRE, CONFIRM_DELETE = range(4)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Build the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="prov:create"),
            InlineKeyboardButton("📋 Listar", callback_data="prov:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="prov:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the suppliers list."""
    from utils.telegram_helpers import reply_html
    
    proveedores = ProveedorService.listar()
    
    if not proveedores:
        text = "👥 <b>Suppliers</b>\n\nNo suppliers are registered yet."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create", callback_data="prov:create")],
            [InlineKeyboardButton("⬅️ Back", callback_data="prov:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "👥 <b>Suppliers</b>\n\nSelect an action for each item:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for prov in proveedores:
        prov_id = prov["id"]
        nombre = prov["name"]
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"prov:edit:{prov_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"prov:del:{prov_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="prov:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def proveedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for supplier management."""
    from utils.telegram_helpers import reply_html
    
    # Clear any residual data from previous conversations
    keys_to_remove = [
        "prov_nombre", "prov_edit_id", "prov_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "👥 <b>Supplier Management</b>\n\n"
        "Manage your suppliers. Use the menu below."
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
    
    if data == "prov:create":
        await reply_html(
            update,
            "🆕 <b>New Supplier</b>\n\nSend the supplier <b>name</b>:"
        )
        return CREAR_NOMBRE
    
    if data == "prov:list":
        await _render_list(update, context)
        return MENU
    
    if data == "prov:back":
        return await proveedores_entry(update, context)
    
    if data == "prov:close":
        # Clear all conversation data
        keys_to_remove = [
            "prov_nombre", "prov_edit_id", "prov_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Closed.")
        return ConversationHandler.END
    
    # Per-item actions
    if data.startswith("prov:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        prov_id = int(data.split(":")[-1])
        context.user_data["prov_edit_id"] = prov_id
        proveedor = ProveedorService.obtener_por_id(prov_id)
        if not proveedor:
            await reply_text(update, "❌ Supplier not found.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Rename Supplier</b>\n\n"
            f"Current: <code>{proveedor['name']}</code>\n"
            f"Send the <b>new name</b>:"
        )
        return EDIT_NOMBRE
    
    if data.startswith("prov:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        prov_id = int(data.split(":")[-1])
        context.user_data["prov_del_id"] = prov_id
        proveedor = ProveedorService.obtener_por_id(prov_id)
        if not proveedor:
            await reply_text(update, "❌ Supplier not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, delete", callback_data="prov:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="prov:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirm deletion</b>\n\n"
            f"You are about to delete: <code>{proveedor['name']}</code>\n"
            f"This action cannot be undone.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "prov:delok":
        from utils.telegram_helpers import reply_text
        
        prov_id = context.user_data.get("prov_del_id")
        if prov_id is None:
            await reply_text(update, "❌ No item selected for deletion.")
            await _render_list(update, context)
            return MENU
        try:
            ProveedorService.delete(int(prov_id))
            # Clear delete ID
            context.user_data.pop("prov_del_id", None)
            # Show message, then updated list
            await reply_text(update, "🗑️ Supplier deleted successfully.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error deleting supplier: {e}", exc_info=True)
            await reply_text(update, "❌ Could not delete. Try again.")
            await _render_list(update, context)
        return MENU
    
    if data == "prov:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the name for creating a supplier."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return CREAR_NOMBRE
    
    try:
        resultado = ProveedorService.create(nombre)
        await reply_html(
            update,
            f"✅ <b>Created</b>\n\nSupplier: <code>{nombre}</code>"
        )
        await reply_html(
            update,
            "What would you like to do now?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A supplier with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creating supplier: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while creating. Please try again.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the new name to edit a supplier."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    prov_id = context.user_data.get("prov_edit_id")
    if prov_id is None:
        await reply_text(update, "❌ No supplier is currently being edited.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return EDIT_NOMBRE
    
    try:
        ProveedorService.update(int(prov_id), nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Updated</b>\n\nNew name: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("prov_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A supplier with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error updating supplier: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while updating. Please try again.")
        return EDIT_NOMBRE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    from utils.telegram_helpers import reply_text
    
    # Clear all conversation data
    keys_to_remove = [
        "prov_nombre", "prov_edit_id", "prov_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
    return ConversationHandler.END


# Exportable ConversationHandler
proveedores_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("proveedores", proveedores_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^prov:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prov:.*"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prov:.*"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^prov:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="proveedores_conversation",
    persistent=False,
)

