"""
Handlers for seller management (full CRUD).
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
from services.vendedores_service import VendedorService

logger = logging.getLogger(__name__)

# Conversation states
MENU, CREAR_NOMBRE, EDIT_NOMBRE, CONFIRM_DELETE = range(4)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Build the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="vend:create"),
            InlineKeyboardButton("📋 Listar", callback_data="vend:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="vend:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Render the sellers list."""
    from utils.telegram_helpers import reply_html
    
    vendedores = VendedorService.listar()
    
    if not vendedores:
        text = "👤 <b>Sellers</b>\n\nNo sellers are registered yet."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create", callback_data="vend:create")],
            [InlineKeyboardButton("⬅️ Back", callback_data="vend:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "👤 <b>Sellers</b>\n\nSelect an action for each item:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        vend_id = vend["id"]
        nombre = vend["name"]
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"vend:edit:{vend_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"vend:del:{vend_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="vend:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def vendedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for seller management."""
    from utils.telegram_helpers import reply_html
    
    # Clear any residual data from previous conversations
    keys_to_remove = [
        "vend_nombre", "vend_edit_id", "vend_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "👤 <b>Seller Management</b>\n\n"
        "Manage your sellers. Use the menu below."
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
    
    if data == "vend:create":
        await reply_html(
            update,
            "🆕 <b>New Seller</b>\n\nSend the seller <b>name</b>:"
        )
        return CREAR_NOMBRE
    
    if data == "vend:list":
        await _render_list(update, context)
        return MENU
    
    if data == "vend:back":
        return await vendedores_entry(update, context)
    
    if data == "vend:close":
        # Clear all conversation data
        keys_to_remove = [
            "vend_nombre", "vend_edit_id", "vend_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Closed.")
        return ConversationHandler.END
    
    # Per-item actions
    if data.startswith("vend:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        vend_id = int(data.split(":")[-1])
        context.user_data["vend_edit_id"] = vend_id
        vendedor = VendedorService.obtener_por_id(vend_id)
        if not vendedor:
            await reply_text(update, "❌ Seller not found.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Rename Seller</b>\n\n"
            f"Current: <code>{vendedor['name']}</code>\n"
            f"Send the <b>new name</b>:"
        )
        return EDIT_NOMBRE
    
    if data.startswith("vend:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        vend_id = int(data.split(":")[-1])
        context.user_data["vend_del_id"] = vend_id
        vendedor = VendedorService.obtener_por_id(vend_id)
        if not vendedor:
            await reply_text(update, "❌ Seller not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, delete", callback_data="vend:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="vend:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirm deletion</b>\n\n"
            f"You are about to delete: <code>{vendedor['name']}</code>\n"
            f"This action cannot be undone.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "vend:delok":
        from utils.telegram_helpers import reply_text
        
        vend_id = context.user_data.get("vend_del_id")
        if vend_id is None:
            await reply_text(update, "❌ No item selected for deletion.")
            await _render_list(update, context)
            return MENU
        try:
            VendedorService.delete(int(vend_id))
            # Clear delete ID
            context.user_data.pop("vend_del_id", None)
            # Show message, then updated list
            await reply_text(update, "🗑️ Seller deleted successfully.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error deleting seller: {e}", exc_info=True)
            await reply_text(update, "❌ Could not delete. Try again.")
            await _render_list(update, context)
        return MENU
    
    if data == "vend:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the name for creating a seller."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return CREAR_NOMBRE
    
    try:
        resultado = VendedorService.create(nombre)
        await reply_html(
            update,
            f"✅ <b>Created</b>\n\nSeller: <code>{nombre}</code>"
        )
        await reply_html(
            update,
            "What would you like to do now?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A seller with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creating seller: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while creating. Please try again.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the new name to edit a seller."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    vend_id = context.user_data.get("vend_edit_id")
    if vend_id is None:
        await reply_text(update, "❌ No seller is currently being edited.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ Name cannot be empty. Send a valid name.")
        return EDIT_NOMBRE
    
    try:
        VendedorService.update(int(vend_id), nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Updated</b>\n\nNew name: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("vend_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ A seller with that name already exists. Use another name.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error updating seller: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred while updating. Please try again.")
        return EDIT_NOMBRE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    from utils.telegram_helpers import reply_text
    
    # Clear all conversation data
    keys_to_remove = [
        "vend_nombre", "vend_edit_id", "vend_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
    return ConversationHandler.END


# Exportable ConversationHandler
vendedores_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("vendedores", vendedores_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^vend:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^vend:.*"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^vend:.*"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^vend:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="vendedores_conversation",
    persistent=False,
)

