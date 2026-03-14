"""
Handlers para gestión de cajas (CRUD completo).
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

# Estados de la conversación
MENU, CREAR_NOMBRE, CREAR_DESCRIPCION, EDIT_MENU, EDIT_NOMBRE, EDIT_DESCRIPCION, CONFIRM_DELETE = range(7)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="caja:create"),
            InlineKeyboardButton("📋 Listar", callback_data="caja:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="caja:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de cajas."""
    from utils.telegram_helpers import reply_html
    
    cajas = CajaService.listar()
    
    if not cajas:
        text = "💰 <b>Cajas</b>\n\nAún no hay cajas registradas."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="caja:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="caja:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "💰 <b>Cajas</b>\n\n"
    keyboard: List[List[InlineKeyboardButton]] = []
    for caja in cajas:
        caja_id = caja["id"]
        nombre = caja["nombre"]
        saldos = caja.get("saldos", {})
        
        # Formatear saldos para mostrar
        saldos_text = ""
        if saldos:
            saldos_list = []
            for moneda, monto in saldos.items():
                if monto != 0:
                    saldos_list.append(f"{monto:.2f} {moneda.upper()}")
            if saldos_list:
                saldos_text = " | " + " | ".join(saldos_list)
        else:
            saldos_text = " | Sin saldo"
        
        text += f"<b>{nombre}</b>{saldos_text}\n"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {nombre}", callback_data=f"caja:edit:{caja_id}"),
            InlineKeyboardButton("📊 Detalles", callback_data=f"caja:detalles:{caja_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"caja:del:{caja_id}"),
        ])
    text += "\nSelecciona una acción:"
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="caja:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def cajas_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de cajas."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "💰 <b>Gestión de Cajas</b>\n\n"
        "Administra tus cajas. Usa el menú de abajo."
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
    
    if data == "caja:create":
        await reply_html(
            update,
            "🆕 <b>Nueva Caja</b>\n\nEnvía el <b>nombre</b> de la caja:"
        )
        return CREAR_NOMBRE
    
    if data == "caja:list":
        await _render_list(update, context)
        return MENU
    
    if data == "caja:back":
        return await cajas_entry(update, context)
    
    if data == "caja:close":
        # Limpiar todos los datos de la conversación
        keys_to_remove = [
            "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("caja:detalles:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja no encontrada.")
            return MENU
        
        saldos = caja.get("saldos", {})
        descripcion_text = caja.get('descripcion') or "Sin descripción"
        
        text = f"📊 <b>Detalles de Caja</b>\n\n"
        text += f"Nombre: <code>{caja['nombre']}</code>\n"
        text += f"Descripción: {descripcion_text}\n\n"
        text += f"<b>Saldos:</b>\n"
        
        if saldos:
            for moneda in VALID_MONEDAS:
                saldo = saldos.get(moneda, 0)
                text += f"• {moneda.upper()}: <b>{saldo:.2f}</b>\n"
        else:
            text += "Sin movimientos registrados.\n"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Editar", callback_data=f"caja:edit:{caja_id}")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="caja:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return MENU
    
    if data.startswith("caja:edit:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["caja_edit_id"] = caja_id
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja no encontrada.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Editar Nombre", callback_data="caja:edit_nombre")],
            [InlineKeyboardButton("📝 Editar Descripción", callback_data="caja:edit_descripcion")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="caja:back")]
        ])
        descripcion_text = caja.get('descripcion') or "Sin descripción"
        await reply_html(
            update,
            f"✏️ <b>Editar Caja</b>\n\n"
            f"Nombre: <code>{caja['nombre']}</code>\n"
            f"Descripción: {descripcion_text}",
            reply_markup=kb
        )
        return EDIT_MENU
    
    if data == "caja:edit_nombre":
        caja_id = context.user_data.get("caja_edit_id")
        if not caja_id:
            await reply_text(update, "❌ No hay caja en edición.")
            return MENU
        caja = CajaService.obtener_por_id(caja_id)
        await reply_html(
            update,
            f"✏️ <b>Renombrar Caja</b>\n\n"
            f"Actual: <code>{caja['nombre']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "caja:edit_descripcion":
        caja_id = context.user_data.get("caja_edit_id")
        if not caja_id:
            await reply_text(update, "❌ No hay caja en edición.")
            return MENU
        caja = CajaService.obtener_por_id(caja_id)
        await reply_html(
            update,
            f"📝 <b>Editar Descripción</b>\n\n"
            f"Caja: <code>{caja['nombre']}</code>\n"
            f"Descripción actual: {caja.get('descripcion') or 'Sin descripción'}\n\n"
            f"Envía la <b>nueva descripción</b> (o 'sin' para quitar):"
        )
        return EDIT_DESCRIPCION
    
    if data.startswith("caja:del:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["caja_del_id"] = caja_id
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja no encontrada.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="caja:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="caja:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{caja['nombre']}</code>\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "caja:delok":
        caja_id = context.user_data.get("caja_del_id")
        if caja_id is None:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        try:
            CajaService.eliminar(int(caja_id))
            context.user_data.pop("caja_del_id", None)
            await reply_text(update, "🗑️ Caja eliminada correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando caja: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "caja:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para crear una caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    context.user_data["caja_nombre"] = nombre
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n\n"
        f"Envía la <b>descripción</b> (opcional, o 'sin' para omitir):"
    )
    return CREAR_DESCRIPCION


@admin_only
async def crear_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la descripción para crear una caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_DESCRIPCION
    
    descripcion = (update.message.text or "").strip()
    nombre = context.user_data.get("caja_nombre")
    
    if not nombre:
        await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    # Si el usuario escribe 'sin', no guardar descripción
    if descripcion.lower() == 'sin':
        descripcion = None
    
    try:
        resultado = CajaService.crear(nombre, descripcion)
        await reply_html(
            update,
            f"✅ <b>Creado</b>\n\nCaja: <code>{nombre}</code>"
        )
        context.user_data.pop("caja_nombre", None)
        context.user_data.pop("caja_descripcion", None)
        await reply_html(
            update,
            "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe una caja con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return CREAR_NOMBRE
    except Exception as e:
        logger.error(f"Error creando caja: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        return CREAR_NOMBRE


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar una caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    caja_id = context.user_data.get("caja_edit_id")
    if caja_id is None:
        await reply_text(update, "❌ No hay caja en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        caja = CajaService.obtener_por_id(caja_id)
        CajaService.actualizar(int(caja_id), nuevo_nombre, caja.get('descripcion'))
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("caja_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe una caja con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando caja: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


@admin_only
async def edit_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la nueva descripción para editar una caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    caja_id = context.user_data.get("caja_edit_id")
    if caja_id is None:
        await reply_text(update, "❌ No hay caja en edición.")
        return MENU
    
    nueva_descripcion = (update.message.text or "").strip()
    
    # Si el usuario escribe 'sin', quitar descripción
    if nueva_descripcion.lower() == 'sin':
        nueva_descripcion = None
    
    try:
        caja = CajaService.obtener_por_id(caja_id)
        CajaService.actualizar(int(caja_id), caja['nombre'], nueva_descripcion)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nDescripción actualizada."
        )
        context.user_data.pop("caja_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        await reply_text(update, f"❌ {e}")
        return EDIT_DESCRIPCION
    except Exception as e:
        logger.error(f"Error actualizando caja: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_DESCRIPCION


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "caja_nombre", "caja_descripcion", "caja_edit_id", "caja_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
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
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja:.*"),
        ],
        CREAR_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_descripcion_receive),
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

