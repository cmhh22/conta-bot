"""
Handlers para gestión de proveedores (CRUD completo).
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

# Estados de la conversación
MENU, CREAR_NOMBRE, EDIT_NOMBRE, CONFIRM_DELETE = range(4)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="prov:create"),
            InlineKeyboardButton("📋 Listar", callback_data="prov:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="prov:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de proveedores."""
    from utils.telegram_helpers import reply_html
    
    proveedores = ProveedorService.listar()
    
    if not proveedores:
        text = "👥 <b>Proveedores</b>\n\nAún no hay proveedores registrados."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="prov:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="prov:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "👥 <b>Proveedores</b>\n\nSelecciona una acción para cada ítem:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for prov in proveedores:
        prov_id = prov["id"]
        nombre = prov["name"]
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"prov:edit:{prov_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"prov:del:{prov_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="prov:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def proveedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de proveedores."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "prov_nombre", "prov_edit_id", "prov_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "👥 <b>Gestión de Proveedores</b>\n\n"
        "Administra tus proveedores. Usa el menú de abajo."
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
    
    if data == "prov:create":
        await reply_html(
            update,
            "🆕 <b>Nuevo Proveedor</b>\n\nEnvía el <b>nombre</b> del proveedor:"
        )
        return CREAR_NOMBRE
    
    if data == "prov:list":
        await _render_list(update, context)
        return MENU
    
    if data == "prov:back":
        return await proveedores_entry(update, context)
    
    if data == "prov:close":
        # Limpiar todos los datos de la conversación
        keys_to_remove = [
            "prov_nombre", "prov_edit_id", "prov_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("prov:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        prov_id = int(data.split(":")[-1])
        context.user_data["prov_edit_id"] = prov_id
        proveedor = ProveedorService.obtener_por_id(prov_id)
        if not proveedor:
            await reply_text(update, "❌ Proveedor no encontrado.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Renombrar Proveedor</b>\n\n"
            f"Actual: <code>{proveedor['name']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data.startswith("prov:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        prov_id = int(data.split(":")[-1])
        context.user_data["prov_del_id"] = prov_id
        proveedor = ProveedorService.obtener_por_id(prov_id)
        if not proveedor:
            await reply_text(update, "❌ Proveedor no encontrado.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="prov:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="prov:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{proveedor['name']}</code>\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "prov:delok":
        from utils.telegram_helpers import reply_text
        
        prov_id = context.user_data.get("prov_del_id")
        if prov_id is None:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        try:
            ProveedorService.eliminar(int(prov_id))
            # Limpiar el ID de eliminación
            context.user_data.pop("prov_del_id", None)
            # Mostrar mensaje y luego la lista actualizada
            await reply_text(update, "🗑️ Proveedor eliminado correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando proveedor: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "prov:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para crear un proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    try:
        resultado = ProveedorService.crear(nombre)
        await reply_html(
            update,
            f"✅ <b>Creado</b>\n\nProveedor: <code>{nombre}</code>"
        )
        await reply_html(
            update,
            "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un proveedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creando proveedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    prov_id = context.user_data.get("prov_edit_id")
    if prov_id is None:
        await reply_text(update, "❌ No hay proveedor en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        ProveedorService.actualizar(int(prov_id), nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("prov_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un proveedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando proveedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "prov_nombre", "prov_edit_id", "prov_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
proveedores_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("proveedores", proveedores_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^prov:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
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

