"""
Handlers para management de warehousees (CRUD completo).
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
from services.warehousees_service import (
    create, listar, obtener_por_id, update, delete
)
from services.logistics_service import obtener_inventario_warehouse

logger = logging.getLogger(__name__)

# Estados de la conversation
MENU, CREAR_NOMBRE, CREAR_UBICACION, EDIT_MENU, EDIT_NOMBRE, EDIT_UBICACION, CONFIRM_DELETE = range(7)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del main menu."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="alm:create"),
            InlineKeyboardButton("📋 Listar", callback_data="alm:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="alm:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de warehousees."""
    from utils.telegram_helpers import reply_html
    
    warehousees = listar()
    
    if not warehousees:
        text = "🏢 <b>Warehousees</b>\n\nStill no hay warehousees recordeds."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create", callback_data="alm:create")],
            [InlineKeyboardButton("⬅️ Back", callback_data="alm:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "🏢 <b>Warehousees</b>\n\nSelect aa action para cada item:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in warehousees:
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
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="alm:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def warehousees_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la management de warehousees."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversationes anteriores
    keys_to_remove = [
        "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "🏢 <b>Management de Warehousees</b>\n\n"
        "Administra tus warehousees. Usa el menu de abajo."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


@admin_only
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del menu."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "alm:create":
        await reply_html(
            update,
            "🆕 <b>Nuevo Warehouse</b>\n\nSend el <b>nombre</b> del warehouse:"
        )
        return CREAR_NOMBRE
    
    if data == "alm:list":
        await _render_list(update, context)
        return MENU
    
    if data == "alm:back":
        return await warehousees_entry(update, context)
    
    if data == "alm:close":
        # Limpiar todos los datos de la conversation
        keys_to_remove = [
            "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Closed.")
        return ConversationHandler.END
    
    # Actions por item
    if data.startswith("alm:edit:"):
        alm_id = int(data.split(":")[-1])
        context.user_data["alm_edit_id"] = alm_id
        warehouse = obtener_por_id(alm_id)
        if not warehouse:
            await reply_text(update, "❌ Warehouse not found.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Nombre", callback_data="alm:edit_nombre")],
            [InlineKeyboardButton("📍 Location", callback_data="alm:edit_ubicacion")],
            [InlineKeyboardButton("📦 Ver Inventario", callback_data="alm:inventario")],
            [InlineKeyboardButton("⬅️ Back", callback_data="alm:back")]
        ])
        await reply_html(
            update,
            f"✏️ <b>Warehouse: {warehouse['nombre']}</b>\n\n"
            f"Nombre: <code>{warehouse['nombre']}</code>\n"
            f"Location: <code>{warehouse.get('ubicacion', 'N/A')}</code>\n\n"
            f"Que deseas hacer?",
            reply_markup=kb
        )
        return EDIT_MENU
    
    if data == "alm:edit_nombre":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No warehouse en edicion.")
            return MENU
        warehouse = obtener_por_id(alm_id)
        if not warehouse:
            await reply_text(update, "❌ Warehouse not found.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Renombrar Warehouse</b>\n\n"
            f"Actual: <code>{warehouse['nombre']}</code>\n"
            f"Send el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "alm:edit_ubicacion":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No warehouse en edicion.")
            return MENU
        warehouse = obtener_por_id(alm_id)
        if not warehouse:
            await reply_text(update, "❌ Warehouse not found.")
            return MENU
        await reply_html(
            update,
            f"📍 <b>Update Location</b>\n\n"
            f"Actual: <code>{warehouse.get('ubicacion', 'N/A')}</code>\n"
            f"Send la <b>nueva location</b> (o 'sin location' para delete):"
        )
        return EDIT_UBICACION
    
    if data == "alm:inventario":
        alm_id = context.user_data.get("alm_edit_id")
        if alm_id is None:
            await reply_text(update, "❌ No warehouse selectdo.")
            return MENU
        warehouse = obtener_por_id(alm_id)
        if not warehouse:
            await reply_text(update, "❌ Warehouse not found.")
            return MENU
        
        try:
            inventario = obtener_inventario_warehouse(alm_id)
            
            if not inventario:
                text = f"📦 <b>Inventario: {warehouse['nombre']}</b>\n\nEste warehouse no tiene productos en inventario."
            else:
                text = f"📦 <b>Inventario: {warehouse['nombre']}</b>\n\n"
                for item in inventario:
                    text += (
                        f"• <b>{item['producto_nombre']}</b> ({item['producto_codigo']})\n"
                        f"  Cantidad: {item['cantidad']}\n\n"
                    )
            
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data=f"alm:edit:{alm_id}")]
            ])
            await reply_html(update, text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Error obteniendo inventario: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
        return MENU
    
    if data.startswith("alm:del:"):
        alm_id = int(data.split(":")[-1])
        context.user_data["alm_del_id"] = alm_id
        warehouse = obtener_por_id(alm_id)
        if not warehouse:
            await reply_text(update, "❌ Warehouse not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, borrar", callback_data="alm:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="alm:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar deletion</b>\n\n"
            f"Vas a borrar: <code>{warehouse['nombre']}</code>\n"
            f"Esta action no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "alm:delok":
        alm_id = context.user_data.get("alm_del_id")
        if alm_id is None:
            await reply_text(update, "❌ No elemento para delete.")
            await _render_list(update, context)
            return MENU
        try:
            delete(int(alm_id))
            context.user_data.pop("alm_del_id", None)
            await reply_text(update, "🗑️ Warehouse deleted correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando warehouse: {e}", exc_info=True)
            await reply_text(update, "❌ Could not delete. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "alm:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para create un warehouse."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar empty. Send un nombre valid.")
        return CREAR_NOMBRE
    
    context.user_data["alm_nombre"] = nombre
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n\n"
        f"Send la <b>location</b> del warehouse (opcional, o escribe 'sin location' para omitir):"
    )
    return CREAR_UBICACION


@admin_only
async def create_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the location and create the warehouse."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_UBICACION
    
    nombre = context.user_data.get("alm_nombre")
    if not nombre:
        await reply_text(update, "❌ Error: name not found. Start again.")
        return await warehousees_entry(update, context)
    
    ubicacion = (update.message.text or "").strip()
    if ubicacion.lower() in ["no location", "sin ubicacion", "n/a", "na"]:
        ubicacion = None
    
    try:
        resultado = create(nombre, ubicacion)
        await reply_html(
            update,
            f"✅ <b>Creado</b>\n\n"
            f"Warehouse: <code>{resultado['nombre']}</code>\n"
            f"Location: <code>{resultado.get('ubicacion', 'N/A')}</code>"
        )
        context.user_data.pop("alm_nombre", None)
        await reply_html(
            update,
            "What would you like to do now?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un warehouse con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creando warehouse: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al create. Try again.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un warehouse."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    alm_id = context.user_data.get("alm_edit_id")
    if alm_id is None:
        await reply_text(update, "❌ No warehouse en edicion.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar empty. Send un nombre valid.")
        return EDIT_NOMBRE
    
    try:
        update(int(alm_id), nuevo_nombre=nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("alm_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un warehouse con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando warehouse: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al update. Try again.")
        return EDIT_NOMBRE


@admin_only
async def edit_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la nueva location para editar un warehouse."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    alm_id = context.user_data.get("alm_edit_id")
    if alm_id is None:
        await reply_text(update, "❌ No warehouse en edicion.")
        return MENU
    
    nueva_ubicacion = (update.message.text or "").strip()
    if nueva_ubicacion.lower() in ["sin location", "sin ubicacion", "n/a", "na"]:
        nueva_ubicacion = None
    
    try:
        update(int(alm_id), nueva_ubicacion=nueva_ubicacion)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNueva location: <code>{nueva_ubicacion or 'N/A'}</code>"
        )
        context.user_data.pop("alm_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        await reply_text(update, f"❌ {e}")
        return EDIT_UBICACION
    except Exception as e:
        logger.error(f"Error actualizando warehouse: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al update. Try again.")
        return EDIT_UBICACION


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operation actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversation
    keys_to_remove = [
        "alm_nombre", "alm_ubicacion", "alm_edit_id", "alm_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
    return ConversationHandler.END


# ConversationHandler exportable
warehousees_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("warehousees", warehousees_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^alm:.*"),
        ],
        CREAR_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_ubicacion_receive),
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
    name="warehousees_conversation",
    persistent=False,
)

