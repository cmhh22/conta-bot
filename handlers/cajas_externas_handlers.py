"""
Handlers for external cash box CRUD.
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

# Conversation states
MENU, CREAR_NOMBRE, CREAR_UBICACION, CREAR_DESCRIPCION, CREAR_PORCENTAJE, EDIT_MENU, EDIT_NOMBRE, EDIT_UBICACION, EDIT_DESCRIPCION, EDIT_PORCENTAJE, CONFIRM_DELETE, VER_DETALLES = range(12)


@admin_only
async def cajas_externas_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for external cash box CRUD."""
    from utils.telegram_helpers import reply_html
    
    # Clear previous data
    keys_to_remove = [
        "caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje",
        "caja_ext_edit_id", "caja_ext_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas_externas = CajaExternaService.listar()
    
    text = "🌍 <b>CAJAS EXTERNAS</b>\n\n"
    text += "Manage external cash boxes (outside Cuba, e.g., USA).\n\n"
    
    if cajas_externas:
        text += "<b>Registered external cash boxes:</b>\n"
        for caja in cajas_externas:
            porcentaje = caja.get('porcentaje_envio', 0)
            text += f"  • <b>{caja['nombre']}</b> - {caja['ubicacion']}"
            if porcentaje > 0:
                text += f" ({porcentaje:.2f}% shipping)"
            text += "\n"
    else:
        text += "<i>No external cash boxes are registered.</i>\n"
    
    keyboard: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton("➕ Create nueva", callback_data="caja_ext:create")],
    ]
    
    if cajas_externas:
        keyboard.append([InlineKeyboardButton("📊 View details", callback_data="caja_ext:ver_detalles")])
        keyboard.append([InlineKeyboardButton("✏️ Edit", callback_data="caja_ext:edit_menu")])
        keyboard.append([InlineKeyboardButton("🗑️ Delete", callback_data="caja_ext:delete_menu")])
    
    keyboard.append([InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")])
    
    await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu callbacks."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "caja_ext:back" or data == "caja_ext:close":
        await reply_text(update, "✅ Operation canceled.")
        return ConversationHandler.END
    
    if data == "caja_ext:create":
        await reply_html(update, "📝 <b>Create New External Cash Box</b>\n\nSend the external cash box <b>name</b>:")
        return CREAR_NOMBRE
    
    if data == "caja_ext:ver_detalles":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No external cash boxes available to view details.")
            return MENU
        
        text = "📊 <b>View External Cash Box Details</b>\n\nSelect the external cash box:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:detalles:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return VER_DETALLES
    
    if data.startswith("caja_ext:detalles:"):
        caja_externa_id = int(data.split(":")[-1])
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        if not caja_externa:
            await reply_text(update, "❌ External cash box not found.")
            return MENU
        
        # Get transfers for this external cash box
        with get_db_connection() as conn:
            transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
        
        text = f"📊 <b>External Cash Box Details</b>\n\n"
        text += f"<b>Name:</b> {caja_externa['nombre']}\n"
        text += f"<b>Location:</b> {caja_externa['ubicacion']}\n"
        if caja_externa.get('descripcion'):
            text += f"<b>Description:</b> {caja_externa['descripcion']}\n"
        text += f"<b>Shipping Percentage:</b> {caja_externa.get('porcentaje_envio', 0):.2f}%\n\n"
        
        if not transferencias:
            text += "<i>No transfers are registered for this external cash box.</i>"
        else:
            text += f"<b>Transfers ({len(transferencias)}):</b>\n\n"
            
            # Group by currency and product to display totals
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
                caja_source = transf['caja_source_nombre']
                
                # Accumulate totals by currency
                if moneda not in totales_por_moneda:
                    totales_por_moneda[moneda] = {
                        'total': 0,
                        'envio': 0,
                        'recibido': 0
                    }
                totales_por_moneda[moneda]['total'] += monto
                totales_por_moneda[moneda]['envio'] += monto_envio
                totales_por_moneda[moneda]['recibido'] += monto_recibido
                
                # Group products
                key_producto = f"{producto_codigo} - {producto_nombre}"
                if key_producto not in productos_transferidos:
                    productos_transferidos[key_producto] = {
                        'moneda': moneda,
                        'total': 0,
                        'cantidad_transferencias': 0
                    }
                productos_transferidos[key_producto]['total'] += monto
                productos_transferidos[key_producto]['cantidad_transferencias'] += 1
                
                # Show each transfer
                fecha_str = fecha.split()[0] if fecha else "N/A"
                text += f"📦 <b>{producto_codigo}</b> - {producto_nombre}\n"
                text += f"   💰 Monto: {monto:.2f} {moneda.upper()}\n"
                text += f"   💸 Shipping: {monto_envio:.2f} {moneda.upper()}\n"
                text += f"   💵 Received: {monto_recibido:.2f} {moneda.upper()}\n"
                text += f"   📦 From: {caja_source}\n"
                text += f"   📅 Date: {fecha_str}\n\n"
            
            # Show summary by currency
            text += "--- <b>SUMMARY BY CURRENCY</b> ---\n"
            for moneda, totales in totales_por_moneda.items():
                text += f"\n<b>{moneda.upper()}:</b>\n"
                text += f"  Total Transferred: {totales['total']:,.2f} {moneda.upper()}\n"
                text += f"  Total Shipping: {totales['envio']:,.2f} {moneda.upper()}\n"
                text += f"  Total Received: {totales['recibido']:,.2f} {moneda.upper()}\n"
            
            # Show summary by product
            text += "\n--- <b>SUMMARY BY PRODUCT</b> ---\n"
            for producto, datos in productos_transferidos.items():
                text += f"\n<b>{producto}</b> ({datos['cantidad_transferencias']} transfers):\n"
                text += f"  Total: {datos['total']:,.2f} {datos['moneda'].upper()}\n"
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return VER_DETALLES
    
    if data == "caja_ext:edit_menu":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No external cash boxes available to edit.")
            return MENU
        
        text = "✏️ <b>Edit External Cash Box</b>\n\nSelect the external cash box to edit:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:edit:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_MENU
    
    if data == "caja_ext:delete_menu":
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No external cash boxes available to delete.")
            return MENU
        
        text = "🗑️ <b>Delete External Cash Box</b>\n\nSelect the external cash box to delete:"
        keyboard: list[list[InlineKeyboardButton]] = []
        for caja in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"{caja['nombre']} - {caja['ubicacion']}",
                    callback_data=f"caja_ext:del:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")])
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
    
    if data.startswith("caja_ext:edit:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ External cash box not found.")
            return MENU
        
        context.user_data["caja_ext_edit_id"] = caja_id
        
        text = f"✏️ <b>Edit External Cash Box</b>\n\n"
        text += f"<b>Current name:</b> {caja['nombre']}\n"
        text += f"<b>Current location:</b> {caja['ubicacion']}\n"
        if caja.get('descripcion'):
            text += f"<b>Current description:</b> {caja['descripcion']}\n"
        text += f"<b>Current shipping percentage:</b> {caja.get('porcentaje_envio', 0):.2f}%\n\n"
        text += "What do you want to edit?"
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("📝 Name", callback_data="caja_ext:edit_nombre")],
            [InlineKeyboardButton("📍 Location", callback_data="caja_ext:edit_ubicacion")],
            [InlineKeyboardButton("📄 Description", callback_data="caja_ext:edit_descripcion")],
            [InlineKeyboardButton("📊 Shipping Percentage", callback_data="caja_ext:edit_porcentaje")],
            [InlineKeyboardButton("↩️ Back", callback_data="caja_ext:back")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return EDIT_MENU
    
    if data == "caja_ext:edit_nombre":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: external cash box ID not found.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Edit Name</b>\n\nCurrent name: <code>{caja['nombre']}</code>\n\nSend the new name:")
        return EDIT_NOMBRE
    
    if data == "caja_ext:edit_ubicacion":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: external cash box ID not found.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Edit Location</b>\n\nCurrent location: <code>{caja['ubicacion']}</code>\n\nSend the new location:")
        return EDIT_UBICACION
    
    if data == "caja_ext:edit_descripcion":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: external cash box ID not found.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Edit Description</b>\n\nCurrent description: <code>{caja.get('descripcion') or 'No description'}</code>\n\nSend the new description (or 'skip' to clear):")
        return EDIT_DESCRIPCION
    
    if data == "caja_ext:edit_porcentaje":
        caja_id = context.user_data.get("caja_ext_edit_id")
        if not caja_id:
            await reply_text(update, "❌ Error: external cash box ID not found.")
            return MENU
        caja = CajaExternaService.obtener_por_id(caja_id)
        await reply_html(update, f"✏️ <b>Edit Shipping Percentage</b>\n\nCurrent percentage: <code>{caja.get('porcentaje_envio', 0):.2f}%</code>\n\nSend the new percentage (0-100):")
        return EDIT_PORCENTAJE
    
    if data.startswith("caja_ext:del:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ External cash box not found.")
            return MENU
        
        context.user_data["caja_ext_del_id"] = caja_id
        
        text = f"🗑️ <b>Confirm Deletion</b>\n\n"
        text += f"Are you sure you want to delete the external cash box:\n"
        text += f"<b>{caja['nombre']}</b> - {caja['ubicacion']}?\n\n"
        text += "⚠️ This action cannot be undone."
        
        keyboard: list[list[InlineKeyboardButton]] = [
            [InlineKeyboardButton("✅ Yes, delete", callback_data="caja_ext:delok")],
            [InlineKeyboardButton("❌ Cancel", callback_data="caja_ext:cancel")],
        ]
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return CONFIRM_DELETE
    
    if data == "caja_ext:delok":
        caja_id = context.user_data.get("caja_ext_del_id")
        if not caja_id:
            await reply_text(update, "❌ Error: external cash box ID not found.")
            return MENU
        
        caja = CajaExternaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ External cash box not found.")
            return MENU
        
        try:
            CajaExternaService.delete(caja_id)
            await reply_html(
                update,
                f"✅ <b>External Cash Box Deleted</b>\n\n"
                f"External cash box <b>{caja['nombre']}</b> was deleted successfully."
            )
            context.user_data.pop("caja_ext_del_id", None)
            return await cajas_externas_entry(update, context)
        except Exception as e:
            logger.error(f"Error deleting external cash box: {e}", exc_info=True)
            await reply_text(update, f"❌ Error deleting external cash box: {e}")
            return MENU
    
    if data == "caja_ext:cancel":
        await reply_text(update, "✅ Operation canceled.")
        return await cajas_externas_entry(update, context)
    
    return MENU


# ========== CREAR CAJA EXTERNA ==========

async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the name of the new external cash box."""
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ Name cannot be empty. Send the name:")
        return CREAR_NOMBRE
    
    # Check whether it already exists
    caja_existente = CajaExternaService.obtener_por_nombre(nombre)
    if caja_existente:
        await reply_text(update, f"❌ An external cash box named '{nombre}' already exists. Send another name:")
        return CREAR_NOMBRE
    
    context.user_data["caja_ext_nombre"] = nombre
    
    await reply_html(update, f"✅ Name: <code>{nombre}</code>\n\nSend the <b>location</b> (e.g., USA, Miami, etc.):")
    return CREAR_UBICACION


async def create_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the location of the new external cash box."""
    if not update.message:
        return CREAR_UBICACION
    
    ubicacion = (update.message.text or "").strip()
    if not ubicacion:
        await reply_text(update, "❌ Location cannot be empty. Send the location:")
        return CREAR_UBICACION
    
    context.user_data["caja_ext_ubicacion"] = ubicacion
    
    nombre = context.user_data.get("caja_ext_nombre")
    await reply_html(
        update,
        f"✅ Name: <code>{nombre}</code>\n"
        f"✅ Location: <code>{ubicacion}</code>\n\n"
        f"Send the <b>description</b> (optional, send 'skip' to omit):"
    )
    return CREAR_DESCRIPCION


async def create_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the description of the new external cash box."""
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
        f"✅ Name: <code>{nombre}</code>\n"
        f"✅ Location: <code>{ubicacion}</code>\n"
        f"✅ Description: <code>{descripcion or 'No description'}</code>\n\n"
        f"Send the <b>shipping percentage</b> (0-100, e.g., 5.5 for 5.5%):"
    )
    return CREAR_PORCENTAJE


async def create_porcentaje_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive shipping percentage and create the external cash box."""
    if not update.message:
        return CREAR_PORCENTAJE
    
    try:
        porcentaje = float((update.message.text or "").strip())
        if porcentaje < 0 or porcentaje > 100:
            await reply_text(update, "❌ Percentage must be between 0 and 100. Send the percentage:")
            return CREAR_PORCENTAJE
    except ValueError:
        await reply_text(update, "❌ Invalid percentage. Send a number between 0 and 100:")
        return CREAR_PORCENTAJE
    
    nombre = context.user_data.get("caja_ext_nombre")
    ubicacion = context.user_data.get("caja_ext_ubicacion")
    descripcion = context.user_data.get("caja_ext_descripcion")
    
    try:
        caja = CajaExternaService.create(nombre, ubicacion, descripcion, porcentaje)
        await reply_html(
            update,
            f"✅ <b>Caja Externa Creada</b>\n\n"
            f"<b>Name:</b> {caja['nombre']}\n"
            f"<b>Location:</b> {caja['ubicacion']}\n"
            f"<b>Description:</b> {caja['descripcion'] or 'No description'}\n"
            f"<b>Shipping Percentage:</b> {caja['porcentaje_envio']:.2f}%"
        )
        
        # Limpiar datos
        keys_to_remove = ["caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error creando caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error while create la caja externa: {e}")
        return CREAR_PORCENTAJE


# ========== EDITAR CAJA EXTERNA ==========

async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar."""
    if not update.message:
        return EDIT_NOMBRE
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ Name cannot be empty. Send the new name:")
        return EDIT_NOMBRE
    
    # Verificar si ya existe otro con ese nombre
    caja_existente = CajaExternaService.obtener_por_nombre(nuevo_nombre)
    caja_id = context.user_data.get("caja_ext_edit_id")
    if caja_existente and caja_existente['id'] != caja_id:
        await reply_text(update, f"❌ Another external cash box with name '{nuevo_nombre}' already exists. Send another name:")
        return EDIT_NOMBRE
    
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa not found.")
        return MENU
    
    try:
        CajaExternaService.update(
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
        await reply_text(update, f"❌ Error while update: {e}")
        return EDIT_NOMBRE


async def edit_ubicacion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new location for editing."""
    if not update.message:
        return EDIT_UBICACION
    
    nueva_ubicacion = (update.message.text or "").strip()
    if not nueva_ubicacion:
        await reply_text(update, "❌ Location cannot be empty. Send the new location:")
        return EDIT_UBICACION
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa not found.")
        return MENU
    
    try:
        CajaExternaService.update(
            caja_id, caja['nombre'], nueva_ubicacion,
            caja.get('descripcion'), caja.get('porcentaje_envio')
        )
        await reply_html(
            update,
            f"✅ <b>Location Updated</b>\n\n"
            f"External cash box location changed to: <b>{nueva_ubicacion}</b>"
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error updating external cash box location: {e}", exc_info=True)
        await reply_text(update, f"❌ Error while update: {e}")
        return EDIT_UBICACION


async def edit_descripcion_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new description for editing."""
    if not update.message:
        return EDIT_DESCRIPCION
    
    nueva_descripcion = (update.message.text or "").strip()
    if nueva_descripcion.lower() == "skip" or not nueva_descripcion:
        nueva_descripcion = None
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa not found.")
        return MENU
    
    try:
        CajaExternaService.update(
            caja_id, caja['nombre'], caja['ubicacion'],
            nueva_descripcion, caja.get('porcentaje_envio')
        )
        await reply_html(
            update,
            f"✅ <b>Description Updated</b>\n\n"
            f"External cash box description has been updated."
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error updating external cash box description: {e}", exc_info=True)
        await reply_text(update, f"❌ Error while update: {e}")
        return EDIT_DESCRIPCION


async def edit_porcentaje_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new shipping percentage for editing."""
    if not update.message:
        return EDIT_PORCENTAJE
    
    try:
        nuevo_porcentaje = float((update.message.text or "").strip())
        if nuevo_porcentaje < 0 or nuevo_porcentaje > 100:
            await reply_text(update, "❌ Percentage must be between 0 and 100. Send the percentage:")
            return EDIT_PORCENTAJE
    except ValueError:
        await reply_text(update, "❌ Invalid percentage. Send a number between 0 and 100:")
        return EDIT_PORCENTAJE
    
    caja_id = context.user_data.get("caja_ext_edit_id")
    caja = CajaExternaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja externa not found.")
        return MENU
    
    try:
        CajaExternaService.update(
            caja_id, caja['nombre'], caja['ubicacion'],
            caja.get('descripcion'), nuevo_porcentaje
        )
        await reply_html(
            update,
            f"✅ <b>Shipping Percentage Updated</b>\n\n"
            f"Shipping percentage changed to: <b>{nuevo_porcentaje:.2f}%</b>"
        )
        context.user_data.pop("caja_ext_edit_id", None)
        return await cajas_externas_entry(update, context)
    except Exception as e:
        logger.error(f"Error actualizando porcentaje de caja externa: {e}", exc_info=True)
        await reply_text(update, f"❌ Error while update: {e}")
        return EDIT_PORCENTAJE


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation."""
    from utils.telegram_helpers import reply_text
    
    # Clear all conversation data
    keys_to_remove = [
        "caja_ext_nombre", "caja_ext_ubicacion", "caja_ext_descripcion", "caja_ext_porcentaje",
        "caja_ext_edit_id", "caja_ext_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
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
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|close|cancel)$"),
        ],
        CREAR_UBICACION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_ubicacion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        CREAR_DESCRIPCION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_descripcion_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^caja_ext:(back|cancel)$"),
        ],
        CREAR_PORCENTAJE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_porcentaje_receive),
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

