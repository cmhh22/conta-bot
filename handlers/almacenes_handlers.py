"""
Handlers para gestión de almacenes (CRUD completo).
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
from services.almacenes_service import (
    crear, listar, obtener_por_id, actualizar, eliminar
)
from services.logistica_service import obtener_inventario_almacen

logger = logging.getLogger(__name__)

# Estados de la conversación
MENU, CREAR_NOMBRE, CREAR_UBICACION, EDIT_MENU, EDIT_NOMBRE, EDIT_UBICACION, CONFIRM_DELETE = range(7)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="alm:create"),
            InlineKeyboardButton("📋 Listar", callback_data="alm:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="alm:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de almacenes."""
    from utils.telegram_helpers import reply_html
    
    almacenes = listar()
    
    if not almacenes:
        text = "🏢 <b>Almacenes</b>\n\nAún no hay almacenes registrados."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="alm:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="alm:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "🏢 <b>Almacenes</b>\n\nSelecciona una acción para cada ítem:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in almacenes:
        alm_id = alm["id"]
        nombre = alm["nombre"]
        ubicacion = alm.get("ubicacion", "")
        
        display_name = nombre
        if ubicacion:
            display_name += f" ({ubicacion})"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {display_name[:40]}", callback_data=f"alm:edit:{alm_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"alm:del:{alm_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="alm:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def almacenes_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de almacenes."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "🏢 <b>Gestión de Almacenes</b>\n\n"
        "Administra tus almacenes. Usa el menú de abajo."
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
    
    if data == "alm:create":
        await reply_html(
            update,
            "🆕 <b>Nuevo Almacén</b>\n\nEnvía el <b>nombre</b> del almacén:"
        )
        return CREAR_NOMBRE
    
    if data == "alm:list":
        await _render_list(update, context)
        return MENU
    
    if data == "alm:back":
        return await almacenes_entry(update, context)
    
    if data == "alm:close":
        # Limpiar todos los datos de la conversación
        keys_to_remove = [
            "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("alm:edit:"):
        alm_id = int(data.split(":")[-1])
        context.user_data["alm_edit_id"] = alm_id
        almacen = obtener_por_id(alm_id)
        if not almacen:
            await reply_text(update, "❌ Almacén no encontrado.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Nombre", callback_data="alm:edit_nombre")],
            [InlineKeyboardButton("📍 Ubicación", callback_data="alm:edit_ubicacion")],
            [InlineKeyboardButton("📦 Ver Inventario", callback_data="alm:inventario")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="alm:back")]
        ])
        await reply_html(
            update,
            f"✏️ <b>Almacén: {almacen['nombre']}</b>\n\n"
            f"Nombre: <code>{almacen['nombre']}</code>\n"
            f"Ubicación: <code>{almacen.get('ubicacion', 'N/A')}</code>\n\n"
            f"¿Qué deseas hacer?",
            reply_markup=kb
        )
        return EDIT_MENU
    
    if data == "alm:edit_nombre":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No hay almacén en edición.")
            return MENU
        almacen = obtener_por_id(alm_id)
        if not almacen:
            await reply_text(update, "❌ Almacén no encontrado.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Renombrar Almacén</b>\n\n"
            f"Actual: <code>{almacen['nombre']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "alm:edit_ubicacion":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No hay almacén en edición.")
            return MENU
        almacen = obtener_por_id(alm_id)
        if not almacen:
            await reply_text(update, "❌ Almacén no encontrado.")
            return MENU
        await reply_html(
            update,
            f"📍 <b>Actualizar Ubicación</b>\n\n"
            f"Actual: <code>{almacen.get('ubicacion', 'N/A')}</code>\n"
            f"Envía la <b>nueva ubicación</b> (o 'sin ubicación' para eliminar):"
        )
        return EDIT_UBICACION
    
    if data == "alm:inventario":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No hay almacén seleccionado.")
            return MENU
        almacen = obtener_por_id(alm_id)
        if not almacen:
            await reply_text(update, "❌ Almacén no encontrado.")
            return MENU
        
        try:
            inventario = obtener_inventario_almacen(alm_id)
            
            if not inventario:
                text = f"📦 <b>Inventario: {almacen['nombre']}</b>\n\nEste almacén no tiene productos en inventario."
            else:
                text = f"📦 <b>Inventario: {almacen['nombre']}</b>\n\n"
                for item in inventario:
                    text += (
                        f"• <b>{item['producto_nombre']}</b> ({item['producto_codigo']})\n"
                        f"  Cantidad: {item['cantidad']}\n\n"
                    )
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver", callback_data=f"alm:edit:{alm_id}")]
            ])
            await reply_html(update, text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Error obteniendo inventario: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
        return MENU
    
    if data.startswith("alm:del:"):
        alm_id = int(data.split(":")[-1])
        context.user_data["alm_del_id"] = alm_id
        almacen = obtener_por_id(alm_id)
        if not almacen:
            await reply_text(update, "❌ Almacén no encontrado.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="alm:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="alm:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{almacen['nombre']}</code>\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "alm:delok":
        alm_id = context.user_data.get("alm_del_id")
        if alm_id is None:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        try:
            eliminar(int(alm_id))
            context.user_data.pop("alm_del_id", None)
            await reply_text(update, "🗑️ Almacén eliminado correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando almacén: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "alm:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para crear un almacén."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    context.user_data["alm_nombre"] = nombre
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n\n"
        f"Envía la <b>ubicación</b> del almacén (opcional, o escribe 'sin ubicación' para omitir):"
    )
    return CREAR_UBICACION


@admin_only
async def crear_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la ubicación y crea el almacén."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_UBICACION
    
    nombre = context.user_data.get("alm_nombre")
    if not nombre:
        await reply_text(update, "❌ Error: no se encontró el nombre. Empieza de nuevo.")
        return await almacenes_entry(update, context)
    
    ubicacion = (update.message.text or "").strip()
    if ubicacion.lower() in ["sin ubicación", "sin ubicacion", "n/a", "na"]:
        ubicacion = None
    
    try:
        resultado = crear(nombre, ubicacion)
        await reply_html(
            update,
            f"✅ <b>Creado</b>\n\n"
            f"Almacén: <code>{resultado['nombre']}</code>\n"
            f"Ubicación: <code>{resultado.get('ubicacion', 'N/A')}</code>"
        )
        context.user_data.pop("alm_nombre", None)
        await reply_html(
            update,
            "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un almacén con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creando almacén: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un almacén."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    alm_id = context.user_data.get("alm_edit_id")
    if alm_id is None:
        await reply_text(update, "❌ No hay almacén en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        actualizar(int(alm_id), nuevo_nombre=nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("alm_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un almacén con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando almacén: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


@admin_only
async def edit_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la nueva ubicación para editar un almacén."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    alm_id = context.user_data.get("alm_edit_id")
    if alm_id is None:
        await reply_text(update, "❌ No hay almacén en edición.")
        return MENU
    
    nueva_ubicacion = (update.message.text or "").strip()
    if nueva_ubicacion.lower() in ["sin ubicación", "sin ubicacion", "n/a", "na"]:
        nueva_ubicacion = None
    
    try:
        actualizar(int(alm_id), nueva_ubicacion=nueva_ubicacion)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNueva ubicación: <code>{nueva_ubicacion or 'N/A'}</code>"
        )
        context.user_data.pop("alm_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        await reply_text(update, f"❌ {e}")
        return EDIT_UBICACION
    except Exception as e:
        logger.error(f"Error actualizando almacén: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_UBICACION


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
almacenes_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("almacenes", almacenes_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        CREAR_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_ubicacion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^alm:(edit_nombre|edit_ubicacion|inventario|back)$"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        EDIT_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_ubicacion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^alm:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="almacenes_conversation",
    persistent=False,
)

