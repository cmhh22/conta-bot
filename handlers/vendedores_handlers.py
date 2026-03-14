"""
Handlers para gestión de vendedores (CRUD completo).
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

# Estados de la conversación
MENU, CREAR_NOMBRE, EDIT_NOMBRE, CONFIRM_DELETE = range(4)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="vend:create"),
            InlineKeyboardButton("📋 Listar", callback_data="vend:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="vend:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de vendedores."""
    from utils.telegram_helpers import reply_html
    
    vendedores = VendedorService.listar()
    
    if not vendedores:
        text = "👤 <b>Vendedores</b>\n\nAún no hay vendedores registrados."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="vend:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="vend:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "👤 <b>Vendedores</b>\n\nSelecciona una acción para cada ítem:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        vend_id = vend["id"]
        nombre = vend["name"]
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"vend:edit:{vend_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"vend:del:{vend_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="vend:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def vendedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de vendedores."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "vend_nombre", "vend_edit_id", "vend_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "👤 <b>Gestión de Vendedores</b>\n\n"
        "Administra tus vendedores. Usa el menú de abajo."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


@admin_only
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del menú."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "vend:create":
        await reply_html(
            update,
            "🆕 <b>Nuevo Vendedor</b>\n\nEnvía el <b>nombre</b> del vendedor:"
        )
        return CREAR_NOMBRE
    
    if data == "vend:list":
        await _render_list(update, context)
        return MENU
    
    if data == "vend:back":
        return await vendedores_entry(update, context)
    
    if data == "vend:close":
        # Limpiar todos los datos de la conversación
        keys_to_remove = [
            "vend_nombre", "vend_edit_id", "vend_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("vend:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        vend_id = int(data.split(":")[-1])
        context.user_data["vend_edit_id"] = vend_id
        vendedor = VendedorService.obtener_por_id(vend_id)
        if not vendedor:
            await reply_text(update, "❌ Vendedor no encontrado.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Renombrar Vendedor</b>\n\n"
            f"Actual: <code>{vendedor['name']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data.startswith("vend:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        vend_id = int(data.split(":")[-1])
        context.user_data["vend_del_id"] = vend_id
        vendedor = VendedorService.obtener_por_id(vend_id)
        if not vendedor:
            await reply_text(update, "❌ Vendedor no encontrado.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="vend:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="vend:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{vendedor['name']}</code>\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "vend:delok":
        from utils.telegram_helpers import reply_text
        
        vend_id = context.user_data.get("vend_del_id")
        if vend_id is None:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        try:
            VendedorService.eliminar(int(vend_id))
            # Limpiar el ID de eliminación
            context.user_data.pop("vend_del_id", None)
            # Mostrar mensaje y luego la lista actualizada
            await reply_text(update, "🗑️ Vendedor eliminado correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando vendedor: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "vend:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para crear un vendedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    try:
        resultado = VendedorService.crear(nombre)
        await reply_html(
            update,
            f"✅ <b>Creado</b>\n\nVendedor: <code>{nombre}</code>"
        )
        await reply_html(
            update,
            "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un vendedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creando vendedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un vendedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    vend_id = context.user_data.get("vend_edit_id")
    if vend_id is None:
        await reply_text(update, "❌ No hay vendedor en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        VendedorService.actualizar(int(vend_id), nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("vend_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un vendedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando vendedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "vend_nombre", "vend_edit_id", "vend_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
vendedores_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("vendedores", vendedores_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^vend:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
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

