"""
Handlers para el CRUD de cajas externas.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from services.cajas_externas_service import CajaExternaService
from database.repositories import TransferenciaExternaRepository
from database.connection import get_db_connection
from utils.decorators import admin_only
from utils.telegram_helpers import reply_html, reply_text

logger = logging.getLogger(__name__)

# Estados de la conversación
MENU, CREAR_NOMBRE, CREAR_UBICACION, CREAR_DESCRIPCION, CREAR_PORCENTAJE, EDIT_MENU, EDIT_NOMBRE, EDIT_UBICACION, EDIT_DESCRIPCION, EDIT_PORCENTAJE, CONFIRM_DELETE, VER_DETALLES = range(12)


@admin_only
async def cajas_externas_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para el CRUD de cajas externas."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar datos previos
    keys_to_remove = [
        "caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje",
        "caja_ext_edit_id", "caja_ext_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas_externas = CajaExternaService.listar()
    
    text = "🌍 <b>CAJAS EXTERNAS</b>\n\n"
    text += "Gestiona las cajas externas (fuera de Cuba, ej: USA).\n\n"
    
    if cajas_externas:
        text += "<b>Cajas externas registradas:</b>\n"
        for caja in cajas_externas:
            porcentaje = caja.get('porcentaje_envio', 0)
            text += f"  • <b>{caja['nombre']}</b> - {caja['ubicacion']}"
            if porcentaje > 0:
                text += f" ({porcentaje:.2f}% envío)"
            text += "\n"
    else:
        text += "<i>No hay cajas externas registradas.</i>\n"
    
    keyboard: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton("➕ Crear nueva", callback_data="caja_ext:create")],
    ]
    
    if cajas_externas:
        keyboard.append([InlineKeyboardButton("📊 Ver detalles", callback_data="caja_ext:ver_detalles")])
        keyboard.append([InlineKeyboardButton("✏️ Editar", callback_data="caja_ext:edit_menu")])
        keyboard.append([InlineKeyboardButton("🗑️ Eliminar", callback_data="caja_ext:delete_menu")])
    
    keyboard.append([InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")])
    
    await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del menú principal."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "caja_ext:back" or data == "caja_ext:close":
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    if data == "caja_ext:create":
        await reply_html(update, "📝 <b>Crear Nueva Caja Externa</b>\n\nEnvía el <b>nombre</b> de la caja externa:")
        return CREAR_NOMBRE
    
    if data == "caja_ext:ver_detalles":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No hay cajas externas para ver detalles.")
            return MENU
        
        text = "📊 <b>Ver Detalles de Caja Externa</b>\n\nSelecciona la caja externa:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:detalles:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return VER_DETALLES
    
    if data.startswith("caja_ext:detalles:"):
        caja_externa_id = int(data.split(":")[-1])
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        if not caja_externa:
            await reply_text(update, "❌ Caja externa no encontrada.")
            return MENU
        
        # Obtener transferencias de esta caja externa
        with get_db_connection() as conn:
            transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
        
        text = f"📊 <b>Detalles de Caja Externa</b>\n\n"
        text += f"<b>Nombre:</b> {caja_externa['nombre']}\n"
        text += f"<b>Ubicación:</b> {caja_externa['ubicacion']}\n"
        if caja_externa.get('descripcion'):
            text += f"<b>Descripción:</b> {caja_externa['descripcion']}\n"
        text += f"<b>Porcentaje Envío:</b> {caja_externa.get('porcentaje_envio', 0):.2f}%\n\n"
        
        if not transferencias:
            text += "<i>No hay transferencias registradas para esta caja externa.</i>"
        else:
            text += f"<b>Transferencias ({len(transferencias)}):</b>\n\n"
            
            # Agrupar por moneda y producto para mostrar totales
            totales_por_moneda = {}
            productos_transferidos = {}
            
            for transf in transferencias:
                moneda = transf['moneda']
                producto_codigo = transf['producto_codigo']
                producto_nombre = transf['producto_nombre']
                monto = transf['monto']
                monto_envio = transf['monto_envio']
                monto_recibido = transf['monto_recibido']
                fecha = transf['fecha']
                caja_origen = transf['caja_origen_nombre']
                
                # Acumular totales por moneda
                if moneda not in totales_por_moneda:
                    totales_por_moneda[moneda] = {
                        'total': 0,
                        'envio': 0,
                        'recibido': 0
                    }
                totales_por_moneda[moneda]['total'] += monto
                totales_por_moneda[moneda]['envio'] += monto_envio
                totales_por_moneda[moneda]['recibido'] += monto_recibido
                
                # Agrupar productos
                key_producto = f"{producto_codigo} - {producto_nombre}"
                if key_producto not in productos_transferidos:
                    productos_transferidos[key_producto] = {
                        'moneda': moneda,
                        'total': 0,
                        'cantidad_transferencias': 0
                    }
                productos_transferidos[key_producto]['total'] += monto
                productos_transferidos[key_producto]['cantidad_transferencias'] += 1
                
                # Mostrar cada transferencia
                fecha_str = fecha.split()[0] if fecha else "N/A"
                text += f"📦 <b>{producto_codigo}</b> - {producto_nombre}\n"
                text += f"   💰 Monto: {monto:.2f} {moneda.upper()}\n"
                text += f"   💸 Envío: {monto_envio:.2f} {moneda.upper()}\n"
                text += f"   💵 Recibido: {monto_recibido:.2f} {moneda.upper()}\n"
                text += f"   📦 Desde: {caja_origen}\n"
                text += f"   📅 Fecha: {fecha_str}\n\n"
            
            # Mostrar resumen por moneda
            text += "--- <b>RESUMEN POR MONEDA</b> ---\n"
            for moneda, totales in totales_por_moneda.items():
                text += f"\n<b>{moneda.upper()}:</b>\n"
                text += f"  Total Transferido: {totales['total']:,.2f} {moneda.upper()}\n"
                text += f"  Total Envío: {totales['envio']:,.2f} {moneda.upper()}\n"
                text += f"  Total Recibido: {totales['recibido']:,.2f} {moneda.upper()}\n"
            
            # Mostrar resumen por producto
            text += "\n--- <b>RESUMEN POR PRODUCTO</b> ---\n"
            for producto, datos in productos_transferidos.items():
                text += f"\n<b>{producto}</b> ({datos['cantidad_transferencias']} transferencias):\n"
                text += f"  Total: {datos['total']:,.2f} {datos['moneda'].upper()}\n"
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return VER_DETALLES
    
    if data == "caja_ext:edit_menu":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No hay cajas externas para editar.")
            return MENU
        
        text = "✏️ <b>Editar Caja Externa</b>\n\nSelecciona la caja externa a editar:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:edit:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_MENU
    
    if data == "caja_ext:delete_menu":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No hay cajas externas para eliminar.")
            return MENU
        
        text = "🗑️ <b>Eliminar Caja Externa</b>\n\nSelecciona la caja externa a eliminar:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:del:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
    
    if data.startswith("caja_ext:edit:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja externa no encontrada.")
            return MENU
        
        context.user_data["caja_ext_edit_id"] = caja_id
        
        text = f"✏️ <b>Editar Caja Externa</b>\n\n"
        text += f"<b>Nombre actual:</b> {caja['nombre']}\n"
        text += f"<b>Ubicación actual:</b> {caja['ubicacion']}\n"
        if caja.get('descripcion'):
            text += f"<b>Descripción actual:</b> {caja['descripcion']}\n"
        text += f"<b>Porcentaje envío actual:</b> {caja.get('porcentaje_envio', 0):.2f}%\n\n"
        text += "¿Qué deseas editar?"
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("📝 Nombre", callback_data="caja_ext:edit_nombre")],
            [InlineKeyboardButton("📍 Ubicación", callback_data="caja_ext:edit_ubicacion")],
            [InlineKeyboardButton("📄 Descripción", callback_data="caja_ext:edit_descripcion")],
            [InlineKeyboardButton("📊 Porcentaje Envío", callback_data="caja_ext:edit_porcentaje")],
            [InlineKeyboardButton("↩️ Volver", callback_data="caja_ext:back")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_MENU
    
    if data == "caja_ext:edit_nombre":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: ID de caja externa no encontrado.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Editar Nombre</b>\n\nNombre actual: <code>{caja['nombre']}</code>\n\nEnvía el nuevo nombre:")
        return EDIT_NOMBRE
    
    if data == "caja_ext:edit_ubicacion":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: ID de caja externa no encontrado.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Editar Ubicación</b>\n\nUbicación actual: <code>{caja['ubicacion']}</code>\n\nEnvía la nueva ubicación:")
        return EDIT_UBICACION
    
    if data == "caja_ext:edit_descripcion":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: ID de caja externa no encontrado.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Editar Descripción</b>\n\nDescripción actual: <code>{caja.get('descripcion') or 'Sin descripción'}</code>\n\nEnvía la nueva descripción (o 'skip' para eliminar):")
        return EDIT_DESCRIPCION
    
    if data == "caja_ext:edit_porcentaje":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: ID de caja externa no encontrado.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Editar Porcentaje de Envío</b>\n\nPorcentaje actual: <code>{caja.get('porcentaje_envio', 0):.2f}%</code>\n\nEnvía el nuevo porcentaje (0-100):")
        return EDIT_PORCENTAJE
    
    if data.startswith("caja_ext:del:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja externa no encontrada.")
            return MENU
        
        context.user_data["caja_ext_del_id"] = caja_id
        
        text = f"🗑️ <b>Confirmar Eliminación</b>\n\n"
        text += f"¿Estás seguro de eliminar la caja externa:\n"
        text += f"<b>{caja['nombre']}</b> - {caja['ubicacion']}?\n\n"
        text += "⚠️ Esta acción no se puede deshacer."
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("✅ Sí, eliminar", callback_data="caja_ext:delok")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="caja_ext:cancel")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
    
    if data == "caja_ext:delok":
        caja_id = context.user_data.get("caja_ext_del_id")
        if not caja_id:
            await reply_text(update, "❌ Error: ID de caja externa no encontrado.")
            return MENU
        
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja externa no encontrada.")
            return MENU
        
        try:
            CajaExternaService.eliminar(caja_id)
            await reply_html(
                update,
                f"✅ <b>Caja Externa Eliminada</b>\n\n"
                f"La caja externa <b>{caja['nombre']}</b> ha sido eliminada correctamente."
            )
            context.user_data.pop("caja_ext_del_id", None)
            return await cajas_externas_entry(update, context)
        except Exception as e:
            logger.error(f"Error eliminando caja externa: {e}", exc_info=True)
            await reply_text(update, f"❌ Error al eliminar la caja externa: {e}")
            return MENU
    
    if data == "caja_ext:cancel":
        await reply_text(update, "✅ Operación cancelada.")
        return await cajas_externas_entry(update, context)
    
    return MENU


# ========== CREAR CAJA EXTERNA ==========

async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre de la nueva caja externa."""
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía el nombre:")
        return CREAR_NOMBRE
    
    # Verificar si ya existe
    caja_existente = CajaExternaService.obtener_por_nombre(nombre)
    if caja_existente:
        await reply_text(update, f"❌ Ya existe una caja externa con el nombre '{nombre}'. Envía otro nombre:")
        return CREAR_NOMBRE
    
    context.user_data["caja_ext_nombre"] = nombre
    
    await reply_html(update, f"✅ Nombre: <code>{nombre}</code>\n\nEnvía la <b>ubicación</b> (ej: USA, Miami, etc.):")
    return CREAR_UBICACION


async def crear_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la ubicación de la nueva caja externa."""
    if not update.message:
        return CREAR_UBICACION
    
    ubicacion = (update.message.text or "").strip()
    if not ubicacion:
        await reply_text(update, "❌ La ubicación no puede estar vacía. Envía la ubicación:")
        return CREAR_UBICACION
    
    context.user_data["caja_ext_ubicacion"] = ubicacion
    
    nombre = context.user_data.get("caja_ext_nombre")
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n"
        f"✅ Ubicación: <code>{ubicacion}</code>\n\n"
        f"Envía la <b>descripción</b> (opcional, envía 'skip' para omitir):"
    )
    return CREAR_DESCRIPCION


async def crear_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la descripción de la nueva caja externa."""
    if not update.message:
        return CREAR_DESCRIPCION
    
    descripcion = (update.message.text or "").strip()
    if descripcion.lower() == "skip" or not descripcion:
        descripcion = None
    else:
        context.user_data["caja_ext_descripcion"] = descripcion
    
    nombre = context.user_data.get("caja_ext_nombre")
    ubicacion = context.user_data.get("caja_ext_ubicacion")
    
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n"
        f"✅ Ubicación: <code>{ubicacion}</code>\n"
        f"✅ Descripción: <code>{descripcion or 'Sin descripción'}</code>\n\n"
        f"Envía el <b>porcentaje de envío</b> (0-100, ej: 5.5 para 5.5%):"
    )
    return CREAR_PORCENTAJE


async def crear_porcentaje_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el porcentaje de envío y crea la caja externa."""
    if not update.message:
        return CREAR_PORCENTAJE
    
    try:
        porcentaje = float((update.message.text or "").strip())
        if porcentaje < 0 or porcentaje > 100:
            await reply_text(update, "❌ El porcentaje debe estar entre 0 y 100. Envía el porcentaje:")
            return CREAR_PORCENTAJE
    except ValueError:
        await reply_text(update, "❌ Porcentaje inválido. Envía un número entre 0 y 100:")
        return CREAR_PORCENTAJE
    
    nombre = context.user_data.get("caja_ext_nombre")
    ubicacion = context.user_data.get("caja_ext_ubicacion")
    descripcion = context.user_data.get("caja_ext_descripcion")
    
    try:
        caja = CajaExternaService.crear(nombre, ubicacion, descripcion, porcentaje)
        await reply_html(
            update,
            f"✅ <b>Caja Externa Creada</b>\n\n"
            f"<b>Nombre:</b> {caja['nombre']}\n"
            f"<b>Ubicación:</b> {caja['ubicacion']}\n"
            f"<b>Descripción:</b> {caja['descripcion'] or 'Sin descripción'}\n"
            f"<b>Porcentaje Envío:</b> {caja['porcentaje_envio']:.2f}%"
        )
        
        # Limpiar datos
        keys_to_remove = ["caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error creando caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error al crear la caja externa: {e}")
        return CREAR_PORCENTAJE


# ========== EDITAR CAJA EXTERNA ==========

async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar."""
    if not update.message:
        return EDIT_NOMBRE
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía el nuevo nombre:")
        return EDIT_NOMBRE
    
    # Verificar si ya existe otro con ese nombre
    caja_existente = CajaExternaService.obtener_por_nombre(nuevo_nombre)
    caja_id = context.user_data.get("caja_ext_edit_id")
    if caja_existente and caja_existente['id'] != caja_id:
        await reply_text(update, f"❌ Ya existe otra caja externa con el nombre '{nuevo_nombre}'. Envía otro nombre:")
        return EDIT_NOMBRE
    
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa no encontrada.")
        return MENU
    
    try:
        CajaExternaService.actualizar(
            caja_id, nuevo_nombre, caja['ubicacion'],
            caja.get('descripcion'), caja.get('porcentaje_envio')
        )
        await reply_html(
            update,
            f"✅ <b>Nombre Actualizado</b>\n\n"
            f"El nombre de la caja externa ha sido cambiado a: <b>{nuevo_nombre}</b>"
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error actualizando nombre de caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error al actualizar: {e}")
        return EDIT_NOMBRE


async def edit_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la nueva ubicación para editar."""
    if not update.message:
        return EDIT_UBICACION
    
    nueva_ubicacion = (update.message.text or "").strip()
    if not nueva_ubicacion:
        await reply_text(update, "❌ La ubicación no puede estar vacía. Envía la nueva ubicación:")
        return EDIT_UBICACION
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa no encontrada.")
        return MENU
    
    try:
        CajaExternaService.actualizar(
            caja_id, caja['nombre'], nueva_ubicacion,
            caja.get('descripcion'), caja.get('porcentaje_envio')
        )
        await reply_html(
            update,
            f"✅ <b>Ubicación Actualizada</b>\n\n"
            f"La ubicación de la caja externa ha sido cambiada a: <b>{nueva_ubicacion}</b>"
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error actualizando ubicación de caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error al actualizar: {e}")
        return EDIT_UBICACION


async def edit_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la nueva descripción para editar."""
    if not update.message:
        return EDIT_DESCRIPCION
    
    nueva_descripcion = (update.message.text or "").strip()
    if nueva_descripcion.lower() == "skip" or not nueva_descripcion:
        nueva_descripcion = None
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa no encontrada.")
        return MENU
    
    try:
        CajaExternaService.actualizar(
            caja_id, caja['nombre'], caja['ubicacion'],
            nueva_descripcion, caja.get('porcentaje_envio')
        )
        await reply_html(
            update,
            f"✅ <b>Descripción Actualizada</b>\n\n"
            f"La descripción de la caja externa ha sido actualizada."
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error actualizando descripción de caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error al actualizar: {e}")
        return EDIT_DESCRIPCION


async def edit_porcentaje_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo porcentaje de envío para editar."""
    if not update.message:
        return EDIT_PORCENTAJE
    
    try:
        nuevo_porcentaje = float((update.message.text or "").strip())
        if nuevo_porcentaje < 0 or nuevo_porcentaje > 100:
            await reply_text(update, "❌ El porcentaje debe estar entre 0 y 100. Envía el porcentaje:")
            return EDIT_PORCENTAJE
    except ValueError:
        await reply_text(update, "❌ Porcentaje inválido. Envía un número entre 0 y 100:")
        return EDIT_PORCENTAJE
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa no encontrada.")
        return MENU
    
    try:
        CajaExternaService.actualizar(
            caja_id, caja['nombre'], caja['ubicacion'],
            caja.get('descripcion'), nuevo_porcentaje
        )
        await reply_html(
            update,
            f"✅ <b>Porcentaje de Envío Actualizado</b>\n\n"
            f"El porcentaje de envío ha sido cambiado a: <b>{nuevo_porcentaje:.2f}%</b>"
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error actualizando porcentaje de caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error al actualizar: {e}")
        return EDIT_PORCENTAJE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje",
        "caja_ext_edit_id", "caja_ext_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
cajas_externas_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("cajas_externas", cajas_externas_entry),
        CommandHandler("caja_externa", cajas_externas_entry),  # Alias en singular
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|close|cancel)$"),
        ],
        CREAR_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_ubicacion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        CREAR_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_descripcion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        CREAR_PORCENTAJE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_porcentaje_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(edit:.*|edit_nombre|edit_ubicacion|edit_descripcion|edit_porcentaje|back|cancel)$"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        EDIT_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_ubicacion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        EDIT_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_descripcion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        EDIT_PORCENTAJE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_porcentaje_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(delok|cancel)$"),
        ],
        VER_DETALLES: [
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(detalles:.*|back)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="cajas_externas_conversation",
    persistent=False,
)

