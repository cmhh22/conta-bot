"""
Handlers con formularios interactivos para comandos principales.
"""
import logging
from typing import Optional, List
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
from utils.validators import (
    validate_monto, validate_moneda, validate_cantidad, ValidationError
)
from services.cajas_service import CajaService
from utils.form_helpers import (
    create_moneda_keyboard, create_yes_no_keyboard,
    create_back_keyboard, create_contabilidad_menu_keyboard,
    create_caja_keyboard
)
from services.contabilidad_service import ContabilidadService, DeudaService
from services.proveedores_service import ProveedorService
from core.config import VALID_MONEDAS
from services.inventario_service import InventarioService
from services.cajas_externas_service import CajaExternaService
from database.repositories import ProductoRepository, DeudaRepository, DeudaProductoRepository, TransferenciaExternaRepository, MovimientoRepository
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


async def _cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversacion actual cuando se ejecuta cualquier comando."""
    from utils.telegram_helpers import reply_text
    await reply_text(update, "✅ Operation cancelada.")
    return ConversationHandler.END


# ==================== FORMULARIO DE INGRESO ====================
INGRESO_CAJA, INGRESO_MONTO, INGRESO_MONEDA, INGRESO_CONFIRM = range(4)


@admin_only
async def ingreso_form_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario de ingreso. Tambien maneja el formato con argumentos."""
    from utils.telegram_helpers import reply_html, reply_text
    
    # Si hay argumentos, procesar como comando tradicional
    if context.args and len(context.args) == 3:
        try:
            monto = validate_monto(context.args[0])
            moneda = validate_moneda(context.args[1])
            caja_nombre = context.args[2].lower().strip()
            caja = CajaService.obtener_por_nombre(caja_nombre)
            if not caja:
                await reply_text(update, f"❌ Caja '{caja_nombre}' not found. Usa /cajas para ver las cajas disponibles.")
                return ConversationHandler.END
            caja_id = caja['id']
            user_id = update.effective_user.id
            
            ContabilidadService.registrar_ingreso(monto, moneda, caja_id, user_id)
            
            await reply_html(
                update,
                f"✅ <b>Ingreso registrado!</b>\n\n"
                f"<b>Monto:</b> {monto:.2f} {moneda.upper()}\n"
                f"<b>Caja:</b> {caja['nombre'].upper()}"
            )
            return ConversationHandler.END
        except (ValueError, ValidationError) as e:
            await reply_html(
                update,
                f"<b>Error:</b> {e}\n"
                "Uso correcto: <code>/ingreso [monto] [moneda] [caja]</code>\n"
                "Ejemplo: <code>/ingreso 100 usd cfg</code>"
            )
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error inesperado en /ingreso: {e}", exc_info=True)
            await reply_text(update, "An error occurred inesperado.")
            return ConversationHandler.END
    
    # Limpiar datos previos
    keys_to_remove = ["ingreso_caja_id", "ingreso_monto", "ingreso_moneda"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas = CajaService.listar()
    if not cajas:
        await reply_text(update, "❌ No cajas disponibles. Crea una primero con /cajas")
        return ConversationHandler.END
    
    text = "➕ <b>Nuevo Ingreso</b>\n\nSelect la <b>caja</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for caja in cajas:
        saldos_text = ""
        saldos = caja.get("saldos", {})
        if saldos:
            saldos_list = [f"{monto:.2f} {moneda.upper()}" for moneda, monto in saldos.items() if monto != 0]
            if saldos_list:
                saldos_text = f" ({', '.join(saldos_list)})"
        
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {caja['nombre']}{saldos_text}",
                callback_data=f"ingreso:caja:{caja['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="ingreso:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return INGRESO_CAJA


async def ingreso_caja_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if data == "ingreso:cancel":
        keys_to_remove = ["ingreso_caja_id", "ingreso_monto", "ingreso_moneda"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("ingreso:caja:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["ingreso_caja_id"] = caja_id
        
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja not found.")
            return ConversationHandler.END
        
        await reply_html(
            update,
            f"📦 <b>Caja:</b> {caja['nombre']}\n\n"
            f"Send el <b>monto</b> a ingresar:"
        )
        return INGRESO_MONTO
    
    return INGRESO_CAJA


async def ingreso_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto del ingreso."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return INGRESO_MONTO
    
    try:
        monto = validate_monto(update.message.text)
        context.user_data["ingreso_monto"] = monto
        
        caja_id = context.user_data.get("ingreso_caja_id")
        if not caja_id:
            await reply_text(update, "❌ Error: Caja no selectda. Empieza de nuevo.")
            return ConversationHandler.END
        
        caja = CajaService.obtener_por_id(caja_id)
        
        await reply_html(
            update,
            f"📦 <b>Caja:</b> {caja['nombre']}\n"
            f"💰 <b>Monto:</b> {monto:.2f}\n\n"
            f"Select la <b>moneda</b>:",
            reply_markup=create_moneda_keyboard("ingreso_moneda")
        )
        return INGRESO_MONEDA
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un monto valid:")
        return INGRESO_MONTO


async def ingreso_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    # Mapear de vuelta a formato correcto
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    context.user_data["ingreso_moneda"] = moneda
    
    caja_id = context.user_data.get("ingreso_caja_id")
    monto = context.user_data.get("ingreso_monto")
    
    if not caja_id or not monto:
        await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    caja = CajaService.obtener_por_id(caja_id)
    
    # Mostrar confirmacion
    msg = (
        f"✅ <b>Confirmar Ingreso</b>\n\n"
        f"📦 <b>Caja:</b> {caja['nombre']}\n"
        f"💰 <b>Monto:</b> {monto:.2f} {moneda.upper()}\n\n"
        f"Confirmar este ingreso?"
    )
    await reply_html(update, msg, reply_markup=create_yes_no_keyboard("ingreso_confirm"))
    return INGRESO_CONFIRM




async def ingreso_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el ingreso."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Ingreso cancelado.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            monto = context.user_data.get("ingreso_monto")
            moneda = context.user_data.get("ingreso_moneda")
            caja_id = context.user_data.get("ingreso_caja_id")
            user_id = update.effective_user.id
            
            if not caja_id:
                await reply_text(update, "❌ Error: Caja no selectda.")
                return ConversationHandler.END
            
            caja = CajaService.obtener_por_id(caja_id)
            ContabilidadService.registrar_ingreso(monto, moneda, caja_id, user_id)
            
            await reply_html(
                update,
                f"✅ <b>Ingreso registrado!</b>\n\n"
                f"💰 Monto: <b>{monto:.2f} {moneda.upper()}</b>\n"
                f"📦 Caja: <b>{caja['nombre'].upper()}</b>"
            )
            
            # Limpiar datos
            context.user_data.pop("ingreso_monto", None)
            context.user_data.pop("ingreso_moneda", None)
            context.user_data.pop("ingreso_caja_id", None)
            
        except Exception as e:
            logger.error(f"Error registrando ingreso: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al registrar el ingreso.")
    
    return ConversationHandler.END


# ConversationHandler para ingreso
ingreso_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("ingreso", ingreso_form_entry)],
    states={
        INGRESO_CAJA: [
            CallbackQueryHandler(ingreso_caja_callback, pattern=r"^ingreso:(caja:|cancel)"),
        ],
        INGRESO_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ingreso_monto_receive),
            CallbackQueryHandler(ingreso_caja_callback, pattern=r"^ingreso:.*"),
        ],
        INGRESO_MONEDA: [
            CallbackQueryHandler(ingreso_moneda_callback, pattern=r"^ingreso_moneda:"),
        ],
        INGRESO_CONFIRM: [
            CallbackQueryHandler(ingreso_confirm_callback, pattern=r"^ingreso_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        # Cualquier otro comando cancela la conversacion
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="ingreso_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE GASTO ====================
GASTO_MONEDA, GASTO_CAJA, GASTO_DESC, GASTO_CONFIRM = range(4)


@admin_only
async def gasto_form_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario de gasto."""
    from utils.telegram_helpers import reply_html
    
    await reply_html(
        update,
        "➖ <b>Nuevo Gasto</b>\n\n"
        "Send el <b>monto</b> a gastar:",
        reply_markup=create_back_keyboard("gasto")
    )
    return GASTO_MONEDA


async def gasto_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto del gasto."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return GASTO_MONEDA
    
    try:
        monto = validate_monto(update.message.text)
        context.user_data["gasto_monto"] = monto
        
        await reply_html(
            update,
            f"💰 Monto: <b>{monto:.2f}</b>\n\n"
            "Select la <b>moneda</b>:",
            reply_markup=create_moneda_keyboard("gasto_moneda")
        )
        return GASTO_CAJA
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un monto valid:", reply_markup=create_back_keyboard("gasto"))
        return GASTO_MONEDA


async def gasto_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    context.user_data["gasto_moneda"] = moneda
    
    await reply_html(
        update,
        f"💰 Monto: <b>{context.user_data['gasto_monto']:.2f}</b>\n"
        f"💵 Moneda: <b>{moneda.upper()}</b>\n\n"
        "Select la <b>caja</b>:",
        reply_markup=create_caja_keyboard("gasto_caja")
    )
    return GASTO_DESC


async def gasto_caja_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    caja_id = int(data.split(":")[-1])
    caja = CajaService.obtener_por_id(caja_id)
    if not caja:
        await reply_text(update, "❌ Caja not found.")
        return ConversationHandler.END
    
    context.user_data["gasto_caja_id"] = caja_id
    
    await reply_html(
        update,
        f"💰 Monto: <b>{context.user_data['gasto_monto']:.2f} {context.user_data['gasto_moneda'].upper()}</b>\n"
        f"📦 Caja: <b>{caja['nombre'].upper()}</b>\n\n"
        "Send la <b>description</b> del gasto:",
        reply_markup=create_back_keyboard("gasto")
    )
    return GASTO_CONFIRM


async def gasto_desc_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la description y muestra confirmacion."""
    from utils.telegram_helpers import reply_html
    
    if not update.message:
        return GASTO_CONFIRM
    
    descripcion = update.message.text.strip()
    context.user_data["gasto_descripcion"] = descripcion
    
    monto = context.user_data.get("gasto_monto")
    moneda = context.user_data.get("gasto_moneda")
    caja_id = context.user_data.get("gasto_caja_id")
    
    caja = CajaService.obtener_por_id(caja_id) if caja_id else None
    caja_nombre = caja['nombre'] if caja else "N/A"
    
    msg = (
        f"✅ <b>Confirmar Gasto</b>\n\n"
        f"💰 Monto: <b>{monto:.2f} {moneda.upper()}</b>\n"
        f"📦 Caja: <b>{caja_nombre.upper()}</b>\n"
        f"📝 Description: <b>{descripcion}</b>\n\n"
        f"Confirmar este gasto?"
    )
    await reply_html(update, msg, reply_markup=create_yes_no_keyboard("gasto_confirm"))
    return ConversationHandler.END


async def gasto_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el gasto."""
    from utils.telegram_helpers import reply_html, reply_text
    
    query = update.callback_query
    if query:
        await query.answer()
    data = (query.data if query else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Gasto cancelado.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            monto = context.user_data.get("gasto_monto")
            moneda = context.user_data.get("gasto_moneda")
            caja_id = context.user_data.get("gasto_caja_id")
            descripcion = context.user_data.get("gasto_descripcion")
            user_id = update.effective_user.id
            
            if not caja_id:
                await reply_text(update, "❌ Error: Caja no selectda.")
                return ConversationHandler.END
            
            caja = CajaService.obtener_por_id(caja_id)
            ContabilidadService.registrar_gasto(monto, moneda, caja_id, user_id, descripcion)
            
            await reply_html(
                update,
                f"💸 <b>Gasto Registrado!</b>\n\n"
                f"💰 Monto: <b>-{monto:.2f} {moneda.upper()}</b>\n"
                f"📦 Caja: <b>{caja['nombre'].upper()}</b>\n"
                f"📝 Description: <b>{descripcion}</b>"
            )
            
            # Limpiar datos
            for key in ["gasto_monto", "gasto_moneda", "gasto_caja_id", "gasto_descripcion"]:
                context.user_data.pop(key, None)
            
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
        except Exception as e:
            logger.error(f"Error registrando gasto: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al registrar el gasto.")
    
    return ConversationHandler.END


# ConversationHandler para gasto
gasto_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("gasto", gasto_form_entry)],
    states={
        GASTO_MONEDA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, gasto_monto_receive),
        ],
        GASTO_CAJA: [
            CallbackQueryHandler(gasto_moneda_callback, pattern=r"^gasto_moneda:"),
        ],
        GASTO_DESC: [
            CallbackQueryHandler(gasto_caja_callback, pattern=r"^gasto_caja:"),
        ],
        GASTO_CONFIRM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, gasto_desc_receive),
            CallbackQueryHandler(gasto_confirm_callback, pattern=r"^gasto_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        # Cualquier otro comando cancela la conversacion
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="gasto_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE TRASPASO ENTRE CAJAS ====================
TRASPASO_CAJA_ORIGEN, TRASPASO_MONEDA_ORIGEN, TRASPASO_MONTO, TRASPASO_CAJA_DESTINO, TRASPASO_MONEDA_DESTINO, TRASPASO_MOTIVO, TRASPASO_CONFIRM = range(7)


@admin_only
async def traspaso_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario de traspaso entre cajas."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar datos previos
    keys_to_remove = [
        "traspaso_caja_origen_id", "traspaso_moneda_origen", "traspaso_monto",
        "traspaso_caja_destino_id", "traspaso_moneda_destino", "traspaso_motivo"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas = CajaService.listar()
    if not cajas:
        await reply_html(update, "❌ No cajas disponibles. Crea una primero.")
        return ConversationHandler.END
    
    text = "🔄 <b>Traspaso entre Cajas</b>\n\nSelect la <b>caja de origen</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for caja in cajas:
        saldos_text = ""
        saldos = caja.get("saldos", {})
        if saldos:
            saldos_list = [f"{monto:.2f} {moneda.upper()}" for moneda, monto in saldos.items() if monto != 0]
            if saldos_list:
                saldos_text = f" ({', '.join(saldos_list)})"
        
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {caja['nombre']}{saldos_text}",
                callback_data=f"traspaso:caja_origen:{caja['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="traspaso:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return TRASPASO_CAJA_ORIGEN


async def traspaso_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del formulario de traspaso."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "traspaso:cancel":
        keys_to_remove = [
            "traspaso_caja_origen_id", "traspaso_moneda_origen", "traspaso_monto",
            "traspaso_caja_destino_id", "traspaso_moneda_destino", "traspaso_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("traspaso:caja_origen:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["traspaso_caja_origen_id"] = caja_id
        
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja not found.")
            return ConversationHandler.END
        
        saldos = caja.get("saldos", {})
        if not saldos or all(s == 0 for s in saldos.values()):
            await reply_text(update, f"❌ La caja {caja['nombre']} no tiene saldo disponible.")
            return ConversationHandler.END
        
        text = f"📦 <b>Caja Origen:</b> {caja['nombre']}\n\n"
        text += f"<b>Saldos disponibles:</b>\n"
        for moneda in VALID_MONEDAS:
            saldo = saldos.get(moneda, 0)
            if saldo > 0:
                text += f"• {moneda.upper()}: <b>{saldo:.2f}</b>\n"
        text += "\nSelect la <b>moneda de origen</b>:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            saldo = saldos.get(moneda, 0)
            if saldo > 0:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{moneda.upper()} (Disponible: {saldo:.2f})",
                        callback_data=f"traspaso:moneda_origen:{moneda}"
                    )
                ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="traspaso:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return TRASPASO_MONEDA_ORIGEN
    
    if data.startswith("traspaso:moneda_origen:"):
        moneda = data.split(":")[-1]
        context.user_data["traspaso_moneda_origen"] = moneda
        
        caja_id = context.user_data.get("traspaso_caja_origen_id")
        caja = CajaService.obtener_por_id(caja_id)
        saldos = caja.get("saldos", {})
        saldo_disponible = saldos.get(moneda, 0)
        
        await reply_html(
            update,
            f"📦 <b>Caja Origen:</b> {caja['nombre']}\n"
            f"💵 <b>Moneda:</b> {moneda.upper()}\n"
            f"💰 <b>Disponible:</b> {saldo_disponible:.2f}\n\n"
            f"Send el <b>monto</b> a transferir:"
        )
        return TRASPASO_MONTO
    
    if data.startswith("traspaso:caja_destino:"):
        caja_id = int(data.split(":")[-1])
        caja_origen_id = context.user_data.get("traspaso_caja_origen_id")
        
        if caja_id == caja_origen_id:
            await reply_text(update, "❌ La caja destino no puede ser la misma que la de origen.")
            return TRASPASO_CAJA_DESTINO
        
        context.user_data["traspaso_caja_destino_id"] = caja_id
        
        caja_destino = CajaService.obtener_por_id(caja_id)
        text = f"📦 <b>Caja Destino:</b> {caja_destino['nombre']}\n\n"
        text += f"Select la <b>moneda de destino</b>:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"traspaso:moneda_destino:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="traspaso:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return TRASPASO_MONEDA_DESTINO
    
    if data.startswith("traspaso:moneda_destino:"):
        moneda = data.split(":")[-1]
        context.user_data["traspaso_moneda_destino"] = moneda
        
        caja_origen_id = context.user_data.get("traspaso_caja_origen_id")
        moneda_origen = context.user_data.get("traspaso_moneda_origen")
        monto = context.user_data.get("traspaso_monto")
        caja_destino_id = context.user_data.get("traspaso_caja_destino_id")
        
        if caja_origen_id == caja_destino_id and moneda_origen == moneda:
            await reply_text(update, "❌ Las cajas y monedas de origen y destino no pueden ser iguales.")
            return TRASPASO_MONEDA_DESTINO
        
        caja_origen = CajaService.obtener_por_id(caja_origen_id)
        caja_destino = CajaService.obtener_por_id(caja_destino_id)
        
        # Calcular monto destino
        from utils.currency import convert_currency
        if moneda_origen == moneda:
            monto_destino = monto
        else:
            monto_destino = convert_currency(monto, moneda_origen, moneda)
        
        text = f"🔄 <b>Resumen del Traspaso</b>\n\n"
        text += f"<b>Origen:</b> {caja_origen['nombre']}\n"
        text += f"• Monto: <b>{monto:.2f} {moneda_origen.upper()}</b>\n\n"
        text += f"<b>Destino:</b> {caja_destino['nombre']}\n"
        text += f"• Monto: <b>{monto_destino:.2f} {moneda.upper()}</b>\n\n"
        text += f"Send el <b>motivo</b> del traspaso:"
        
        await reply_html(update, text)
        return TRASPASO_MOTIVO
    
    if data == "traspaso:back":
        # Back al paso anterior segun el estado actual
        if context.user_data.get("traspaso_motivo"):
            context.user_data.pop("traspaso_motivo", None)
            return TRASPASO_MONEDA_DESTINO
        elif context.user_data.get("traspaso_moneda_destino"):
            context.user_data.pop("traspaso_moneda_destino", None)
            return TRASPASO_CAJA_DESTINO
        elif context.user_data.get("traspaso_caja_destino_id"):
            context.user_data.pop("traspaso_caja_destino_id", None)
            return TRASPASO_MONTO
        elif context.user_data.get("traspaso_monto"):
            context.user_data.pop("traspaso_monto", None)
            return TRASPASO_MONEDA_ORIGEN
        elif context.user_data.get("traspaso_moneda_origen"):
            context.user_data.pop("traspaso_moneda_origen", None)
            return TRASPASO_CAJA_ORIGEN
        else:
            return await traspaso_entry(update, context)
    
    return TRASPASO_CAJA_ORIGEN


async def traspaso_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto a transferir."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return TRASPASO_MONTO
    
    try:
        monto = validate_monto(update.message.text)
        context.user_data["traspaso_monto"] = monto
        
        caja_id = context.user_data.get("traspaso_caja_origen_id")
        moneda = context.user_data.get("traspaso_moneda_origen")
        
        if not caja_id or not moneda:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        caja = CajaService.obtener_por_id(caja_id)
        saldos = caja.get("saldos", {})
        saldo_disponible = saldos.get(moneda, 0)
        
        if monto > saldo_disponible:
            await reply_text(
                update,
                f"❌ Saldo insuficiente. Disponible: {saldo_disponible:.2f} {moneda.upper()}"
            )
            return TRASPASO_MONTO
        
        # Mostrar cajas disponibles para destino
        cajas = CajaService.listar()
        cajas_destino = [c for c in cajas if c['id'] != caja_id]
        
        if not cajas_destino:
            await reply_text(update, "❌ No otras cajas disponibles para destino.")
            return ConversationHandler.END
        
        text = f"✅ Monto: <b>{monto:.2f} {moneda.upper()}</b>\n\n"
        text += f"Select la <b>caja de destino</b>:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for caja_dest in cajas_destino:
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {caja_dest['nombre']}",
                    callback_data=f"traspaso:caja_destino:{caja_dest['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="traspaso:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return TRASPASO_CAJA_DESTINO
    except ValidationError as e:
        await reply_text(update, f"❌ {e}")
        return TRASPASO_MONTO


async def traspaso_motivo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el motivo y muestra confirmacion."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return TRASPASO_MOTIVO
    
    motivo = (update.message.text or "").strip()
    if not motivo:
        await reply_text(update, "❌ El motivo no puede estar empty.")
        return TRASPASO_MOTIVO
    
    context.user_data["traspaso_motivo"] = motivo
    
    caja_origen_id = context.user_data.get("traspaso_caja_origen_id")
    moneda_origen = context.user_data.get("traspaso_moneda_origen")
    monto = context.user_data.get("traspaso_monto")
    caja_destino_id = context.user_data.get("traspaso_caja_destino_id")
    moneda_destino = context.user_data.get("traspaso_moneda_destino")
    
    if not all([caja_origen_id, moneda_origen, monto, caja_destino_id, moneda_destino]):
        await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    caja_origen = CajaService.obtener_por_id(caja_origen_id)
    caja_destino = CajaService.obtener_por_id(caja_destino_id)
    
    # Calcular monto destino
    from utils.currency import convert_currency
    if moneda_origen == moneda_destino:
        monto_destino = monto
    else:
        monto_destino = convert_currency(monto, moneda_origen, moneda_destino)
    
    text = f"✅ <b>Confirmar Traspaso</b>\n\n"
    text += f"<b>Origen:</b> {caja_origen['nombre']}\n"
    text += f"• Monto: <b>-{monto:.2f} {moneda_origen.upper()}</b>\n\n"
    text += f"<b>Destino:</b> {caja_destino['nombre']}\n"
    text += f"• Monto: <b>+{monto_destino:.2f} {moneda_destino.upper()}</b>\n\n"
    text += f"<b>Motivo:</b> {motivo}\n\n"
    text += f"Confirmar este traspaso?"
    
    await reply_html(update, text, reply_markup=create_yes_no_keyboard("traspaso_confirm"))
    return TRASPASO_CONFIRM


async def traspaso_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el traspaso."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Traspaso cancelado.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            caja_origen_id = context.user_data.get("traspaso_caja_origen_id")
            moneda_origen = context.user_data.get("traspaso_moneda_origen")
            monto = context.user_data.get("traspaso_monto")
            caja_destino_id = context.user_data.get("traspaso_caja_destino_id")
            moneda_destino = context.user_data.get("traspaso_moneda_destino")
            motivo = context.user_data.get("traspaso_motivo")
            user_id = update.effective_user.id
            
            if not all([caja_origen_id, moneda_origen, monto, caja_destino_id, moneda_destino, motivo]):
                await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
                return ConversationHandler.END
            
            resultado = ContabilidadService.registrar_traspaso(
                monto, moneda_origen, caja_origen_id, moneda_destino, caja_destino_id, user_id, motivo
            )
            
            caja_origen = CajaService.obtener_por_id(caja_origen_id)
            caja_destino = CajaService.obtener_por_id(caja_destino_id)
            
            await reply_html(
                update,
                f"✅ <b>Traspaso Registrado!</b>\n\n"
                f"<b>Origen:</b> {caja_origen['nombre']}\n"
                f"• Monto: <b>-{resultado['monto_origen']:.2f} {resultado['moneda_origen'].upper()}</b>\n\n"
                f"<b>Destino:</b> {caja_destino['nombre']}\n"
                f"• Monto: <b>+{resultado['monto_destino']:.2f} {resultado['moneda_destino'].upper()}</b>\n\n"
                f"<b>Motivo:</b> {motivo}"
            )
            
            # Limpiar datos
            keys_to_remove = [
                "traspaso_caja_origen_id", "traspaso_moneda_origen", "traspaso_monto",
                "traspaso_caja_destino_id", "traspaso_moneda_destino", "traspaso_motivo"
            ]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
        except Exception as e:
            logger.error(f"Error registrando traspaso: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al registrar el traspaso.")
    
    return ConversationHandler.END


# ConversationHandler para traspaso
traspaso_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("traspaso", traspaso_entry),
    ],
    states={
        TRASPASO_CAJA_ORIGEN: [
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:(caja_origen:|cancel)"),
        ],
        TRASPASO_MONEDA_ORIGEN: [
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:(moneda_origen:|back)"),
        ],
        TRASPASO_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, traspaso_monto_receive),
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:.*"),
        ],
        TRASPASO_CAJA_DESTINO: [
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:(caja_destino:|back)"),
        ],
        TRASPASO_MONEDA_DESTINO: [
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:(moneda_destino:|back)"),
        ],
        TRASPASO_MOTIVO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, traspaso_motivo_receive),
            CallbackQueryHandler(traspaso_callback, pattern=r"^traspaso:.*"),
        ],
        TRASPASO_CONFIRM: [
            CallbackQueryHandler(traspaso_confirm_callback, pattern=r"^traspaso_confirm:.*"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        # Cualquier otro comando cancela la conversacion
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="traspaso_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE DEUDA CON PROVEEDOR ====================
DEUDA_PROV_PROVEEDOR, DEUDA_PROV_PRODUCTO, DEUDA_PROV_CANTIDAD, DEUDA_PROV_COSTO, DEUDA_PROV_MONEDA, DEUDA_PROV_CONFIRM = range(6)


@admin_only
async def deuda_proveedor_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario para generar deuda con proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    # Limpiar datos previos
    keys_to_remove = ["deuda_prov_proveedor_id", "deuda_prov_producto_codigo", "deuda_prov_cantidad", "deuda_prov_costo", "deuda_prov_moneda"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    proveedores = ProveedorService.listar()
    if not proveedores:
        await reply_text(update, "❌ No proveedores disponibles. Crea uno primero con /proveedores")
        return ConversationHandler.END
    
    text = "💳 <b>Generar Deuda con Proveedor</b>\n\n"
    text += "Select el <b>proveedor</b>:"
    
    keyboard: List[List[InlineKeyboardButton]] = []
    for prov in proveedores:
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {prov['name']}",
                callback_data=f"deuda_prov:proveedor:{prov['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="deuda_prov:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return DEUDA_PROV_PROVEEDOR


async def deuda_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "deuda_prov:cancel":
        keys_to_remove = ["deuda_prov_proveedor_id", "deuda_prov_producto_codigo", "deuda_prov_cantidad", "deuda_prov_costo", "deuda_prov_moneda"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("deuda_prov:proveedor:"):
        proveedor_id = int(data.split(":")[-1])
        context.user_data["deuda_prov_proveedor_id"] = proveedor_id
        
        proveedor = ProveedorService.obtener_por_id(proveedor_id)
        if not proveedor:
            await reply_text(update, "❌ Proveedor not found.")
            return ConversationHandler.END
        
        # Mostrar productos disponibles
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_todos(conn)
        
        if not productos:
            await reply_html(
                update,
                f"🏢 <b>Proveedor:</b> {proveedor['name']}\n\n"
                f"Send el <b>codigo del producto</b> (o crea uno nuevo con /productos):"
            )
        else:
            text = f"🏢 <b>Proveedor:</b> {proveedor['name']}\n\n"
            text += "Select el <b>producto</b> o send un codigo nuevo:"
            
            keyboard: List[List[InlineKeyboardButton]] = []
            for prod in productos[:20]:  # Limitar a 20 productos
                keyboard.append([
                    InlineKeyboardButton(
                        f"📦 {prod['codigo']} - {prod['nombre']}",
                        callback_data=f"deuda_prov:producto:{prod['codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("➕ Create nuevo producto", callback_data="deuda_prov:create_producto")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return DEUDA_PROV_PRODUCTO
        
        return DEUDA_PROV_PRODUCTO
    
    return DEUDA_PROV_PROVEEDOR


async def deuda_proveedor_producto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el codigo del producto."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return DEUDA_PROV_PRODUCTO
    
    codigo = (update.message.text or "").strip().upper()
    if not codigo:
        await reply_text(update, "❌ El codigo no puede estar empty.")
        return DEUDA_PROV_PRODUCTO
    
    # Verificar si el producto existe
    with get_db_connection() as conn:
        producto = ProductoRepository.obtener_por_codigo(conn, codigo)
    
    if not producto:
        await reply_text(update, f"❌ Producto '{codigo}' not found. Crealo primero con /productos o select uno de la lista.")
        return DEUDA_PROV_PRODUCTO
    
    context.user_data["deuda_prov_producto_codigo"] = codigo
    
    proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
    proveedor = ProveedorService.obtener_por_id(proveedor_id)
    
    await reply_html(
        update,
        f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
        f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n\n"
        f"Send la <b>cantidad</b>:"
    )
    return DEUDA_PROV_CANTIDAD


async def deuda_proveedor_producto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de producto desde botones."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "deuda_prov:create_producto":
        await reply_text(update, "📝 Crea el producto primero con /productos y luego vuelve a /deuda_proveedor")
        return ConversationHandler.END
    
    if data.startswith("deuda_prov:producto:"):
        codigo = data.split(":")[-1]
        context.user_data["deuda_prov_producto_codigo"] = codigo
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto not found.")
            return ConversationHandler.END
        
        proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
        proveedor = ProveedorService.obtener_por_id(proveedor_id)
        
        await reply_html(
            update,
            f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n\n"
            f"Send la <b>cantidad</b>:"
        )
        return DEUDA_PROV_CANTIDAD
    
    return DEUDA_PROV_PRODUCTO


async def deuda_proveedor_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return DEUDA_PROV_CANTIDAD
    
    try:
        cantidad = validate_cantidad(update.message.text)
        context.user_data["deuda_prov_cantidad"] = cantidad
        
        proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
        producto_codigo = context.user_data.get("deuda_prov_producto_codigo")
        
        if not proveedor_id or not producto_codigo:
            await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        proveedor = ProveedorService.obtener_por_id(proveedor_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
            f"📊 <b>Cantidad:</b> {cantidad}\n\n"
            f"Send el <b>costo unitario</b>:"
        )
        return DEUDA_PROV_COSTO
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend una cantidad valid:")
        return DEUDA_PROV_CANTIDAD


async def deuda_proveedor_costo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el costo unitario."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return DEUDA_PROV_COSTO
    
    try:
        costo = validate_monto(update.message.text)
        context.user_data["deuda_prov_costo"] = costo
        
        proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
        producto_codigo = context.user_data.get("deuda_prov_producto_codigo")
        cantidad = context.user_data.get("deuda_prov_cantidad")
        
        if not all([proveedor_id, producto_codigo, cantidad]):
            await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        proveedor = ProveedorService.obtener_por_id(proveedor_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        monto_total = cantidad * costo
        
        await reply_html(
            update,
            f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
            f"📊 <b>Cantidad:</b> {cantidad}\n"
            f"💰 <b>Costo Unitario:</b> {costo:.2f}\n"
            f"💵 <b>Total:</b> {monto_total:.2f}\n\n"
            f"Select la <b>moneda</b>:",
            reply_markup=create_moneda_keyboard("deuda_prov_moneda")
        )
        return DEUDA_PROV_MONEDA
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un costo valid:")
        return DEUDA_PROV_COSTO


async def deuda_proveedor_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda y muestra confirmacion."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    context.user_data["deuda_prov_moneda"] = moneda
    
    proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
    producto_codigo = context.user_data.get("deuda_prov_producto_codigo")
    cantidad = context.user_data.get("deuda_prov_cantidad")
    costo = context.user_data.get("deuda_prov_costo")
    
    if not all([proveedor_id, producto_codigo, cantidad, costo]):
        await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    proveedor = ProveedorService.obtener_por_id(proveedor_id)
    with get_db_connection() as conn:
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
    
    monto_total = cantidad * costo
    
    # Mostrar confirmacion
    msg = (
        f"✅ <b>Confirmar Deuda</b>\n\n"
        f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
        f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
        f"📊 <b>Cantidad:</b> {cantidad}\n"
        f"💰 <b>Costo Unitario:</b> {costo:.2f} {moneda.upper()}\n"
        f"💵 <b>Total:</b> {monto_total:.2f} {moneda.upper()}\n"
        f"📋 <b>Tipo:</b> POR PAGAR\n\n"
        f"Confirmar esta deuda?"
    )
    await reply_html(update, msg, reply_markup=create_yes_no_keyboard("deuda_prov_confirm"))
    return DEUDA_PROV_CONFIRM


async def deuda_proveedor_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra la deuda."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Deuda cancelada.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            proveedor_id = context.user_data.get("deuda_prov_proveedor_id")
            producto_codigo = context.user_data.get("deuda_prov_producto_codigo")
            cantidad = context.user_data.get("deuda_prov_cantidad")
            costo = context.user_data.get("deuda_prov_costo")
            moneda = context.user_data.get("deuda_prov_moneda")
            
            if not all([proveedor_id, producto_codigo, cantidad, costo, moneda]):
                await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
                return ConversationHandler.END
            
            proveedor = ProveedorService.obtener_por_id(proveedor_id)
            if not proveedor:
                await reply_text(update, "❌ Proveedor not found.")
                return ConversationHandler.END
            
            with get_db_connection() as conn:
                producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
                if not producto:
                    await reply_text(update, "❌ Producto not found.")
                    return ConversationHandler.END
                
                # Calcular monto total
                monto_total = cantidad * costo
                
                # Obtener o create deuda
                actor_id = proveedor['name'].upper()
                deuda = DeudaRepository.obtener_por_actor(conn, actor_id, moneda, 'POR_PAGAR')
                
                if deuda:
                    nuevo_monto = deuda['monto_pendiente'] + monto_total
                    DeudaRepository.update_monto(conn, actor_id, moneda, 'POR_PAGAR', nuevo_monto)
                    deuda_id = deuda['id']
                else:
                    deuda_id = DeudaRepository.create(conn, actor_id, monto_total, moneda, 'POR_PAGAR')
                    nuevo_monto = monto_total
                
                # Registrar el producto en la deuda
                DeudaProductoRepository.create(
                    conn, deuda_id, producto_codigo, cantidad, costo, monto_total
                )
            
            await reply_html(
                update,
                f"✅ <b>Deuda Generada!</b>\n\n"
                f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
                f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
                f"📊 <b>Cantidad:</b> {cantidad}\n"
                f"💰 <b>Costo Unitario:</b> {costo:.2f} {moneda.upper()}\n"
                f"💵 <b>Monto de esta deuda:</b> {monto_total:.2f} {moneda.upper()}\n"
                f"📊 <b>Saldo Total con Proveedor:</b> {nuevo_monto:.2f} {moneda.upper()}\n"
                f"📋 <b>Tipo:</b> POR PAGAR"
            )
            
            # Limpiar datos
            keys_to_remove = ["deuda_prov_proveedor_id", "deuda_prov_producto_codigo", "deuda_prov_cantidad", "deuda_prov_costo", "deuda_prov_moneda"]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
        except Exception as e:
            logger.error(f"Error generando deuda: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al generar la deuda.")
    
    return ConversationHandler.END


# ConversationHandler para deuda con proveedor
deuda_proveedor_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("deuda_proveedor", deuda_proveedor_entry),
        CommandHandler("deuda", deuda_proveedor_entry),  # Alias corto
    ],
    states={
        DEUDA_PROV_PROVEEDOR: [
            CallbackQueryHandler(deuda_proveedor_callback, pattern=r"^deuda_prov:(proveedor:|cancel)"),
        ],
        DEUDA_PROV_PRODUCTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, deuda_proveedor_producto_receive),
            CallbackQueryHandler(deuda_proveedor_producto_callback, pattern=r"^deuda_prov:(producto:|create_producto)"),
        ],
        DEUDA_PROV_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, deuda_proveedor_cantidad_receive),
            CallbackQueryHandler(deuda_proveedor_callback, pattern=r"^deuda_prov:.*"),
        ],
        DEUDA_PROV_COSTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, deuda_proveedor_costo_receive),
            CallbackQueryHandler(deuda_proveedor_callback, pattern=r"^deuda_prov:.*"),
        ],
        DEUDA_PROV_MONEDA: [
            CallbackQueryHandler(deuda_proveedor_moneda_callback, pattern=r"^deuda_prov_moneda:"),
        ],
        DEUDA_PROV_CONFIRM: [
            CallbackQueryHandler(deuda_proveedor_confirm_callback, pattern=r"^deuda_prov_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        # Cualquier otro comando cancela la conversacion
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="deuda_proveedor_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE CAMBIO DE MONEDA EN CAJA ====================
CAMBIO_CAJA, CAMBIO_MONEDA_ORIGEN, CAMBIO_MONTO, CAMBIO_TASA, CAMBIO_MONEDA_DESTINO, CAMBIO_CONFIRM = range(6)


@admin_only
async def cambio_moneda_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario para cambiar moneda dentro de una caja."""
    from utils.telegram_helpers import reply_html, reply_text
    from utils.form_helpers import create_caja_keyboard
    
    # Limpiar datos previos
    keys_to_remove = ["cambio_caja_id", "cambio_moneda_origen", "cambio_monto", "cambio_tasa", "cambio_moneda_destino"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas = CajaService.listar()
    if not cajas:
        await reply_text(update, "❌ No cajas disponibles. Crea una primero con /cajas")
        return ConversationHandler.END
    
    text = "💱 <b>Cambio de Moneda en Caja</b>\n\n"
    text += "Select la <b>caja</b> donde quieres cambiar moneda:"
    
    await reply_html(update, text, reply_markup=create_caja_keyboard("cambio_caja"))
    return CAMBIO_CAJA


async def cambio_caja_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("cambio_caja:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaService.obtener_por_id(caja_id)
        
        if not caja:
            await reply_text(update, "❌ Caja not found.")
            return ConversationHandler.END
        
        context.user_data["cambio_caja_id"] = caja_id
        
        # Mostrar saldos disponibles
        saldos = caja.get("saldos", {})
        text = f"📦 <b>Caja:</b> {caja['nombre']}\n\n"
        if saldos:
            text += "<b>Saldos disponibles:</b>\n"
            for moneda, monto in saldos.items():
                text += f"• {moneda.upper()}: <b>{monto:.2f}</b>\n"
        else:
            text += "<i>Sin saldo disponible</i>\n"
        
        text += "\nSelect la <b>moneda origen</b> (la que quieres cambiar):"
        
        await reply_html(update, text, reply_markup=create_moneda_keyboard("cambio_moneda_origen"))
        return CAMBIO_MONEDA_ORIGEN
    
    return CAMBIO_CAJA


async def cambio_moneda_origen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda origen."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda_origen = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    
    caja_id = context.user_data.get("cambio_caja_id")
    if not caja_id:
        await reply_text(update, "❌ Error: Caja no selectda. Empieza de nuevo.")
        return ConversationHandler.END
    
    caja = CajaService.obtener_por_id(caja_id)
    saldos = caja.get("saldos", {})
    saldo_disponible = saldos.get(moneda_origen, 0)
    
    if saldo_disponible <= 0:
        await reply_text(update, f"❌ No saldo disponible en {moneda_origen.upper()} en esta caja.")
        return ConversationHandler.END
    
    context.user_data["cambio_moneda_origen"] = moneda_origen
    
    await reply_html(
        update,
        f"📦 <b>Caja:</b> {caja['nombre']}\n"
        f"💵 <b>Moneda Origen:</b> {moneda_origen.upper()}\n"
        f"💰 <b>Saldo Disponible:</b> {saldo_disponible:.2f} {moneda_origen.upper()}\n\n"
        f"Send el <b>monto</b> a cambiar:"
    )
    return CAMBIO_MONTO


async def cambio_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto a cambiar."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CAMBIO_MONTO
    
    try:
        monto = validate_monto(update.message.text)
        
        caja_id = context.user_data.get("cambio_caja_id")
        moneda_origen = context.user_data.get("cambio_moneda_origen")
        
        if not caja_id or not moneda_origen:
            await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        caja = CajaService.obtener_por_id(caja_id)
        saldos = caja.get("saldos", {})
        saldo_disponible = saldos.get(moneda_origen, 0)
        
        if monto > saldo_disponible:
            await reply_text(update, f"❌ Saldo insuficiente. Disponible: {saldo_disponible:.2f} {moneda_origen.upper()}")
            return CAMBIO_MONTO
        
        context.user_data["cambio_monto"] = monto
        
        await reply_html(
            update,
            f"📦 <b>Caja:</b> {caja['nombre']}\n"
            f"💵 <b>Moneda Origen:</b> {moneda_origen.upper()}\n"
            f"💰 <b>Monto:</b> {monto:.2f} {moneda_origen.upper()}\n\n"
            f"Send la <b>tasa de cambio</b>:\n"
            f"• Si cambias de USD/EUR a CUP: tasa = cuantos CUP por 1 USD/EUR (ej: 410)\n"
            f"• Si cambias de CUP a USD/EUR: tasa = cuantos CUP por 1 USD/EUR (ej: 410)\n"
            f"• Si cambias entre USD y EUR: tasa = cuantos EUR por 1 USD (ej: 0.92)"
        )
        return CAMBIO_TASA
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un monto valid:")
        return CAMBIO_MONTO


async def cambio_tasa_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la tasa de cambio."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CAMBIO_TASA
    
    try:
        tasa = validate_monto(update.message.text)
        if tasa <= 0:
            await reply_text(update, "❌ La tasa debe ser mayor a 0.")
            return CAMBIO_TASA
        
        caja_id = context.user_data.get("cambio_caja_id")
        moneda_origen = context.user_data.get("cambio_moneda_origen")
        monto = context.user_data.get("cambio_monto")
        
        if not all([caja_id, moneda_origen, monto]):
            await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        context.user_data["cambio_tasa"] = tasa
        
        caja = CajaService.obtener_por_id(caja_id)
        
        await reply_html(
            update,
            f"📦 <b>Caja:</b> {caja['nombre']}\n"
            f"💵 <b>Moneda Origen:</b> {moneda_origen.upper()}\n"
            f"💰 <b>Monto:</b> {monto:.2f} {moneda_origen.upper()}\n"
            f"📊 <b>Tasa:</b> {tasa:.2f}\n\n"
            f"Select la <b>moneda destino</b>:",
            reply_markup=create_moneda_keyboard("cambio_moneda_destino")
        )
        return CAMBIO_MONEDA_DESTINO
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend una tasa valid:")
        return CAMBIO_TASA


async def cambio_moneda_destino_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda destino y muestra confirmacion."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda_destino = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    
    caja_id = context.user_data.get("cambio_caja_id")
    moneda_origen = context.user_data.get("cambio_moneda_origen")
    monto = context.user_data.get("cambio_monto")
    tasa = context.user_data.get("cambio_tasa")
    
    if not all([caja_id, moneda_origen, monto, tasa]):
        await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    if moneda_origen == moneda_destino:
        await reply_text(update, "❌ La moneda origen y destino no pueden ser iguales.")
        return CAMBIO_MONEDA_DESTINO
    
    context.user_data["cambio_moneda_destino"] = moneda_destino
    
    caja = CajaService.obtener_por_id(caja_id)
    
    # Calcular monto destino basado en la direccion de conversion
    # La tasa se interpreta como "1 moneda_base = tasa moneda_menor"
    monedas_base = ['usd', 'eur']
    monedas_menores = ['cup', 'cup-t']
    
    # Determinar si necesitamos multiplicar o dividir
    if moneda_origen in monedas_base and moneda_destino in monedas_menores:
        # De base a menor: multiplicar (ej: USD -> CUP)
        monto_destino = monto * tasa
        tasa_texto = f"1 {moneda_origen.upper()} = {tasa:.2f} {moneda_destino.upper()}"
    elif moneda_origen in monedas_menores and moneda_destino in monedas_base:
        # De menor a base: dividir (ej: CUP -> USD)
        monto_destino = monto / tasa
        tasa_texto = f"1 {moneda_destino.upper()} = {tasa:.2f} {moneda_origen.upper()}"
    elif moneda_origen in monedas_base and moneda_destino in monedas_base:
        # Entre monedas base (USD <-> EUR): usar tasa directa
        if moneda_origen == 'usd' and moneda_destino == 'eur':
            # 1 USD = tasa EUR, entonces para convertir USD a EUR: multiplicar
            monto_destino = monto * tasa
            tasa_texto = f"1 {moneda_origen.upper()} = {tasa:.2f} {moneda_destino.upper()}"
        else:
            # 1 EUR = tasa USD, entonces para convertir EUR a USD: dividir
            monto_destino = monto / tasa
            tasa_texto = f"1 {moneda_destino.upper()} = {tasa:.2f} {moneda_origen.upper()}"
    else:
        # Por defecto, multiplicar
        monto_destino = monto * tasa
        tasa_texto = f"1 {moneda_origen.upper()} = {tasa:.2f} {moneda_destino.upper()}"
    
    # Mostrar confirmacion
    msg = (
        f"✅ <b>Confirmar Cambio de Moneda</b>\n\n"
        f"📦 <b>Caja:</b> {caja['nombre']}\n"
        f"💵 <b>Moneda Origen:</b> {moneda_origen.upper()}\n"
        f"💰 <b>Monto Origen:</b> -{monto:.2f} {moneda_origen.upper()}\n"
        f"📊 <b>Tasa:</b> {tasa_texto}\n"
        f"💵 <b>Moneda Destino:</b> {moneda_destino.upper()}\n"
        f"💰 <b>Monto Destino:</b> +{monto_destino:.2f} {moneda_destino.upper()}\n\n"
        f"Confirmar este cambio?"
    )
    await reply_html(update, msg, reply_markup=create_yes_no_keyboard("cambio_confirm"))
    return CAMBIO_CONFIRM


async def cambio_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el cambio de moneda."""
    from utils.telegram_helpers import reply_html, reply_text
    from database.repositories import MovimientoRepository
    from database.connection import get_db_connection
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Cambio cancelado.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            caja_id = context.user_data.get("cambio_caja_id")
            moneda_origen = context.user_data.get("cambio_moneda_origen")
            monto = context.user_data.get("cambio_monto")
            tasa = context.user_data.get("cambio_tasa")
            moneda_destino = context.user_data.get("cambio_moneda_destino")
            
            if not all([caja_id, moneda_origen, monto, tasa, moneda_destino]):
                await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
                return ConversationHandler.END
            
            caja = CajaService.obtener_por_id(caja_id)
            if not caja:
                await reply_text(update, "❌ Caja not found.")
                return ConversationHandler.END
            
            # Calcular monto destino basado en la direccion de conversion
            monedas_base = ['usd', 'eur']
            monedas_menores = ['cup', 'cup-t']
            
            if moneda_origen in monedas_base and moneda_destino in monedas_menores:
                # De base a menor: multiplicar (ej: USD -> CUP)
                monto_destino = monto * tasa
            elif moneda_origen in monedas_menores and moneda_destino in monedas_base:
                # De menor a base: dividir (ej: CUP -> USD)
                monto_destino = monto / tasa
            elif moneda_origen in monedas_base and moneda_destino in monedas_base:
                # Entre monedas base (USD <-> EUR)
                if moneda_origen == 'usd' and moneda_destino == 'eur':
                    monto_destino = monto * tasa
                else:
                    monto_destino = monto / tasa
            else:
                # Por defecto, multiplicar
                monto_destino = monto * tasa
            
            user_id = update.effective_user.id
            
            with get_db_connection() as conn:
                # Verificar saldo suficiente
                saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda_origen)
                if saldo_actual < monto:
                    await reply_text(
                        update,
                        f"❌ Saldo insuficiente. Disponible: {saldo_actual:.2f} {moneda_origen.upper()}"
                    )
                    return ConversationHandler.END
                
                # Registrar gasto en moneda origen
                MovimientoRepository.create(
                    conn, 'gasto', monto, moneda_origen, caja_id, user_id,
                    f"CAMBIO DE MONEDA: {monto:.2f} {moneda_origen.upper()} -> {monto_destino:.2f} {moneda_destino.upper()} (Tasa: {tasa:.2f})"
                )
                
                # Registrar ingreso en moneda destino
                MovimientoRepository.create(
                    conn, 'ingreso', monto_destino, moneda_destino, caja_id, user_id,
                    f"CAMBIO DE MONEDA: {monto:.2f} {moneda_origen.upper()} -> {monto_destino:.2f} {moneda_destino.upper()} (Tasa: {tasa:.2f})"
                )
            
            await reply_html(
                update,
                f"✅ <b>Cambio de Moneda Registrado!</b>\n\n"
                f"📦 <b>Caja:</b> {caja['nombre']}\n"
                f"💵 <b>Origen:</b> -{monto:.2f} {moneda_origen.upper()}\n"
                f"💵 <b>Destino:</b> +{monto_destino:.2f} {moneda_destino.upper()}\n"
                f"📊 <b>Tasa:</b> 1 {moneda_origen.upper()} = {tasa:.2f} {moneda_destino.upper()}"
            )
            
            # Limpiar datos
            keys_to_remove = ["cambio_caja_id", "cambio_moneda_origen", "cambio_monto", "cambio_tasa", "cambio_moneda_destino"]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
        except Exception as e:
            logger.error(f"Error registrando cambio de moneda: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al registrar el cambio de moneda.")
    
    return ConversationHandler.END


# ConversationHandler para cambio de moneda en caja
cambio_moneda_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("cambio_moneda", cambio_moneda_entry),
    ],
    states={
        CAMBIO_CAJA: [
            CallbackQueryHandler(cambio_caja_callback, pattern=r"^cambio_caja:"),
        ],
        CAMBIO_MONEDA_ORIGEN: [
            CallbackQueryHandler(cambio_moneda_origen_callback, pattern=r"^cambio_moneda_origen:"),
        ],
        CAMBIO_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, cambio_monto_receive),
            CallbackQueryHandler(cambio_caja_callback, pattern=r"^cambio_caja:.*"),
        ],
        CAMBIO_TASA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, cambio_tasa_receive),
            CallbackQueryHandler(cambio_caja_callback, pattern=r"^cambio_caja:.*"),
        ],
        CAMBIO_MONEDA_DESTINO: [
            CallbackQueryHandler(cambio_moneda_destino_callback, pattern=r"^cambio_moneda_destino:"),
        ],
        CAMBIO_CONFIRM: [
            CallbackQueryHandler(cambio_confirm_callback, pattern=r"^cambio_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        # Cualquier otro comando cancela la conversacion
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="cambio_moneda_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE TRANSFERENCIA A CAJA EXTERNA ====================
TRANSF_EXT_CAJA_ORIGEN, TRANSF_EXT_CAJA_EXTERNA, TRANSF_EXT_PRODUCTO, TRANSF_EXT_MONTO, TRANSF_EXT_MONEDA, TRANSF_EXT_PORCENTAJE, TRANSF_EXT_CONFIRM = range(7)


@admin_only
async def transferencia_externa_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario para transferir a caja externa."""
    from utils.telegram_helpers import reply_html, reply_text
    from utils.form_helpers import create_caja_keyboard
    
    # Limpiar datos previos
    keys_to_remove = ["transf_ext_caja_origen_id", "transf_ext_caja_externa_id", "transf_ext_producto_codigo",
                      "transf_ext_monto", "transf_ext_moneda", "transf_ext_porcentaje"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    cajas = CajaService.listar()
    if not cajas:
        await reply_text(update, "❌ No cajas disponibles. Crea una primero con /cajas")
        return ConversationHandler.END
    
    text = "🌍 <b>Transferencia a Caja Externa</b>\n\n"
    text += "Select la <b>caja origen</b> (en Cuba):"
    
    await reply_html(update, text, reply_markup=create_caja_keyboard("transf_ext_caja_origen"))
    return TRANSF_EXT_CAJA_ORIGEN


async def transf_ext_caja_origen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja origen."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("transf_ext_caja_origen:"):
        caja_id = int(data.split(":")[-1])
        caja = CajaService.obtener_por_id(caja_id)
        
        if not caja:
            await reply_text(update, "❌ Caja not found.")
            return ConversationHandler.END
        
        context.user_data["transf_ext_caja_origen_id"] = caja_id
        
        # Mostrar cajas externas disponibles
        cajas_externas = CajaExternaService.listar()
        if not cajas_externas:
            await reply_text(update, "❌ No cajas externas disponibles. Crea una primero.")
            return ConversationHandler.END
        
        text = f"📦 <b>Caja Origen:</b> {caja['nombre']}\n\n"
        text += "Select la <b>caja externa</b> (destino):"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for caja_ext in cajas_externas:
            keyboard.append([
                InlineKeyboardButton(
                    f"🌍 {caja_ext['nombre']} ({caja_ext['ubicacion']})",
                    callback_data=f"transf_ext_caja_externa:{caja_ext['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Cancel", callback_data="transf_ext:cancel")])
        kb = InlineKeyboardMarkup(keyboard)
        
        await reply_html(update, text, reply_markup=kb)
        return TRANSF_EXT_CAJA_EXTERNA
    
    return TRANSF_EXT_CAJA_ORIGEN


async def transf_ext_caja_externa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja externa."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancel" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("transf_ext_caja_externa:"):
        caja_externa_id = int(data.split(":")[-1])
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        
        if not caja_externa:
            await reply_text(update, "❌ Caja externa not found.")
            return ConversationHandler.END
        
        context.user_data["transf_ext_caja_externa_id"] = caja_externa_id
        
        # Mostrar productos disponibles
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_todos(conn)
        
        caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
        caja_origen = CajaService.obtener_por_id(caja_origen_id)
        
        text = f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
        text += f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n\n"
        
        if not productos:
            text += "Send el <b>codigo del producto</b> (o crea uno nuevo con /productos):"
        else:
            text += "Select el <b>producto</b> o send un codigo nuevo:"
            
            keyboard: List[List[InlineKeyboardButton]] = []
            for prod in productos[:20]:  # Limitar a 20 productos
                keyboard.append([
                    InlineKeyboardButton(
                        f"📦 {prod['codigo']} - {prod['nombre']}",
                        callback_data=f"transf_ext:producto:{prod['codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("➕ Create nuevo producto", callback_data="transf_ext:create_producto")])
            keyboard.append([InlineKeyboardButton("↩️ Cancel", callback_data="transf_ext:cancel")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return TRANSF_EXT_PRODUCTO
        
        await reply_html(update, text)
        return TRANSF_EXT_PRODUCTO
    
    return TRANSF_EXT_CAJA_EXTERNA


async def transf_ext_producto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el codigo del producto."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return TRANSF_EXT_PRODUCTO
    
    codigo = (update.message.text or "").strip().upper()
    if not codigo:
        await reply_text(update, "❌ El codigo no puede estar empty.")
        return TRANSF_EXT_PRODUCTO
    
    # Verificar si el producto existe
    with get_db_connection() as conn:
        producto = ProductoRepository.obtener_por_codigo(conn, codigo)
    
    if not producto:
        await reply_text(update, f"❌ Producto '{codigo}' not found. Crealo primero con /productos o select uno de la lista.")
        return TRANSF_EXT_PRODUCTO
    
    context.user_data["transf_ext_producto_codigo"] = codigo
    
    caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
    caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
    caja_origen = CajaService.obtener_por_id(caja_origen_id)
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    
    await reply_html(
        update,
        f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
        f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
        f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n\n"
        f"Send el <b>monto</b> a transferir:"
    )
    return TRANSF_EXT_MONTO


async def transf_ext_producto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de producto desde botones."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "transf_ext:create_producto":
        await reply_text(update, "📝 Crea el producto primero con /productos y luego vuelve a /transferencia_externa")
        return ConversationHandler.END
    
    if data.startswith("transf_ext:producto:"):
        codigo = data.split(":")[-1]
        context.user_data["transf_ext_producto_codigo"] = codigo
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto not found.")
            return ConversationHandler.END
        
        caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
        caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
        caja_origen = CajaService.obtener_por_id(caja_origen_id)
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        
        await reply_html(
            update,
            f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
            f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n\n"
            f"Send el <b>monto</b> a transferir:"
        )
        return TRANSF_EXT_MONTO
    
    return TRANSF_EXT_PRODUCTO


async def transf_ext_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto a transferir."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return TRANSF_EXT_MONTO
    
    try:
        monto = validate_monto(update.message.text)
        
        caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
        if not caja_origen_id:
            await reply_text(update, "❌ Error: Caja origen no selectda. Empieza de nuevo.")
            return ConversationHandler.END
        
        caja_origen = CajaService.obtener_por_id(caja_origen_id)
        
        context.user_data["transf_ext_monto"] = monto
        
        caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
        producto_codigo = context.user_data.get("transf_ext_producto_codigo")
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
            f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
            f"💰 <b>Monto:</b> {monto:.2f}\n\n"
            f"Select la <b>moneda</b>:",
            reply_markup=create_moneda_keyboard("transf_ext_moneda")
        )
        return TRANSF_EXT_MONEDA
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un monto valid:")
        return TRANSF_EXT_MONTO


async def transf_ext_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":cancelar" in data:
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    # Extraer moneda del callback
    moneda_part = data.split(":")[-1]
    moneda_map = {"usd": "usd", "cup": "cup", "cup_t": "cup-t", "eur": "eur"}
    moneda = moneda_map.get(moneda_part, moneda_part.replace("_", "-"))
    
    caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
    caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
    monto = context.user_data.get("transf_ext_monto")
    
    if not all([caja_origen_id, caja_externa_id, monto]):
        await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
        return ConversationHandler.END
    
    # Verificar saldo suficiente
    caja_origen = CajaService.obtener_por_id(caja_origen_id)
    saldos = caja_origen.get("saldos", {})
    saldo_disponible = saldos.get(moneda, 0)
    
    if monto > saldo_disponible:
        await reply_text(update, f"❌ Saldo insuficiente. Disponible: {saldo_disponible:.2f} {moneda.upper()}")
        return TRANSF_EXT_MONEDA
    
    context.user_data["transf_ext_moneda"] = moneda
    
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    porcentaje_default = caja_externa.get("porcentaje_envio", 0)
    
    await reply_html(
        update,
        f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
        f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
        f"💰 <b>Monto:</b> {monto:.2f} {moneda.upper()}\n"
        f"💵 <b>Moneda:</b> {moneda.upper()}\n\n"
        f"Send el <b>porcentaje de envio</b> (ej: {porcentaje_default:.2f}%):"
    )
    return TRANSF_EXT_PORCENTAJE


async def transf_ext_porcentaje_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el porcentaje de envio."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return TRANSF_EXT_PORCENTAJE
    
    try:
        porcentaje = validate_monto(update.message.text)
        if porcentaje < 0 or porcentaje > 100:
            await reply_text(update, "❌ El porcentaje debe estar entre 0 y 100.")
            return TRANSF_EXT_PORCENTAJE
        
        caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
        caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
        producto_codigo = context.user_data.get("transf_ext_producto_codigo")
        monto = context.user_data.get("transf_ext_monto")
        moneda = context.user_data.get("transf_ext_moneda")
        
        if not all([caja_origen_id, caja_externa_id, producto_codigo, monto, moneda]):
            await reply_text(update, "❌ Error: Datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        context.user_data["transf_ext_porcentaje"] = porcentaje
        
        # Calcular montos
        monto_envio = monto * (porcentaje / 100)
        monto_recibido = monto - monto_envio
        
        caja_origen = CajaService.obtener_por_id(caja_origen_id)
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        # Mostrar confirmacion
        msg = (
            f"✅ <b>Confirmar Transferencia Externa</b>\n\n"
            f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
            f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
            f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
            f"💰 <b>Monto Total:</b> {monto:.2f} {moneda.upper()}\n"
            f"📊 <b>Porcentaje Envio:</b> {porcentaje:.2f}%\n"
            f"💸 <b>Gasto de Envio:</b> {monto_envio:.2f} {moneda.upper()}\n"
            f"💵 <b>Monto Recibido:</b> {monto_recibido:.2f} {moneda.upper()}\n\n"
            f"Confirmar esta transferencia?"
        )
        await reply_html(update, msg, reply_markup=create_yes_no_keyboard("transf_ext_confirm"))
        return TRANSF_EXT_CONFIRM
    except ValidationError as e:
        await reply_text(update, f"❌ {e}\n\nSend un porcentaje valid (0-100):")
        return TRANSF_EXT_PORCENTAJE


async def transf_ext_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra la transferencia externa."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if ":no" in data or ":cancel" in data:
        await reply_text(update, "❌ Transferencia cancelada.")
        return ConversationHandler.END
    
    if ":yes" in data:
        try:
            caja_origen_id = context.user_data.get("transf_ext_caja_origen_id")
            caja_externa_id = context.user_data.get("transf_ext_caja_externa_id")
            producto_codigo = context.user_data.get("transf_ext_producto_codigo")
            monto = context.user_data.get("transf_ext_monto")
            moneda = context.user_data.get("transf_ext_moneda")
            porcentaje = context.user_data.get("transf_ext_porcentaje")
            
            if not all([caja_origen_id, caja_externa_id, producto_codigo, monto, moneda, porcentaje is not None]):
                await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
                return ConversationHandler.END
            
            caja_origen = CajaService.obtener_por_id(caja_origen_id)
            caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
            
            if not caja_origen or not caja_externa:
                await reply_text(update, "❌ Caja not found.")
                return ConversationHandler.END
            
            with get_db_connection() as conn:
                producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
                if not producto:
                    await reply_text(update, "❌ Producto not found.")
                    return ConversationHandler.END
                
                # Verificar saldo suficiente
                saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_origen_id, moneda)
                if saldo_actual < monto:
                    await reply_text(
                        update,
                        f"❌ Saldo insuficiente. Disponible: {saldo_actual:.2f} {moneda.upper()}"
                    )
                    return ConversationHandler.END
                
                # Calcular montos
                monto_envio = monto * (porcentaje / 100)
                monto_recibido = monto - monto_envio
                
                user_id = update.effective_user.id
                
                # Registrar gasto en caja origen (monto total, que incluye el gasto de envio)
                descripcion_gasto = f"TRANSFERENCIA EXTERNA: {monto:.2f} {moneda.upper()} a {caja_externa['nombre']} ({caja_externa['ubicacion']}) - Producto: {producto['codigo']}"
                if monto_envio > 0:
                    descripcion_gasto += f" (Envio: {monto_envio:.2f} {moneda.upper()} - {porcentaje:.2f}%)"
                
                MovimientoRepository.create(
                    conn, 'gasto', monto, moneda, caja_origen_id, user_id, descripcion_gasto
                )
                
                # Registrar transferencia externa
                TransferenciaExternaRepository.create(
                    conn, caja_origen_id, caja_externa_id, producto_codigo,
                    monto, moneda, porcentaje, monto_envio, monto_recibido, user_id,
                    f"Transferencia de {producto['codigo']} a {caja_externa['nombre']}"
                )
            
            await reply_html(
                update,
                f"✅ <b>Transferencia Externa Registrada!</b>\n\n"
                f"📦 <b>Caja Origen:</b> {caja_origen['nombre']}\n"
                f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} ({caja_externa['ubicacion']})\n"
                f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
                f"💰 <b>Monto Total:</b> {monto:.2f} {moneda.upper()}\n"
                f"💸 <b>Gasto de Envio:</b> {monto_envio:.2f} {moneda.upper()} ({porcentaje:.2f}%)\n"
                f"💵 <b>Monto Recibido:</b> {monto_recibido:.2f} {moneda.upper()}"
            )
            
            # Limpiar datos
            keys_to_remove = ["transf_ext_caja_origen_id", "transf_ext_caja_externa_id", "transf_ext_producto_codigo",
                            "transf_ext_monto", "transf_ext_moneda", "transf_ext_porcentaje"]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
        except Exception as e:
            logger.error(f"Error registrando transferencia externa: {e}", exc_info=True)
            await reply_text(update, "❌ An error occurred al registrar la transferencia.")
    
    return ConversationHandler.END


# ConversationHandler para transferencia a caja externa
transferencia_externa_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("transferencia_externa", transferencia_externa_entry),
    ],
    states={
        TRANSF_EXT_CAJA_ORIGEN: [
            CallbackQueryHandler(transf_ext_caja_origen_callback, pattern=r"^transf_ext_caja_origen:"),
        ],
        TRANSF_EXT_CAJA_EXTERNA: [
            CallbackQueryHandler(transf_ext_caja_externa_callback, pattern=r"^transf_ext_caja_externa:|transf_ext:cancel"),
        ],
        TRANSF_EXT_PRODUCTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, transf_ext_producto_receive),
            CallbackQueryHandler(transf_ext_producto_callback, pattern=r"^transf_ext:(producto:|create_producto|cancel)"),
        ],
        TRANSF_EXT_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, transf_ext_monto_receive),
            CallbackQueryHandler(transf_ext_caja_origen_callback, pattern=r"^transf_ext:.*"),
        ],
        TRANSF_EXT_MONEDA: [
            CallbackQueryHandler(transf_ext_moneda_callback, pattern=r"^transf_ext_moneda:"),
        ],
        TRANSF_EXT_PORCENTAJE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, transf_ext_porcentaje_receive),
            CallbackQueryHandler(transf_ext_caja_origen_callback, pattern=r"^transf_ext:.*"),
        ],
        TRANSF_EXT_CONFIRM: [
            CallbackQueryHandler(transf_ext_confirm_callback, pattern=r"^transf_ext_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="transferencia_externa_conversation",
    persistent=False,
)

# ==================== FORMULARIO DE PAGO A PROVEEDOR ====================
PAGO_PROV_PROVEEDOR, PAGO_PROV_TIPO_CAJA, PAGO_PROV_CAJA_INTERNA, PAGO_PROV_CAJA_EXTERNA, PAGO_PROV_PRODUCTO, PAGO_PROV_MONTO, PAGO_PROV_MONEDA, PAGO_PROV_MOTIVO, PAGO_PROV_CONFIRM = range(9)


@admin_only
async def pago_proveedor_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el formulario para pagar deuda a proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    # Limpiar datos previos
    keys_to_remove = [
        "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
        "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
        "pago_prov_moneda", "pago_prov_motivo"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    # Obtener proveedores con deudas pendientes
    with get_db_connection() as conn:
        deudas = DeudaRepository.obtener_pendientes(conn)
    
    proveedores_con_deuda = {}
    for deuda in deudas:
        if deuda['tipo'] == 'POR_PAGAR':
            actor_id = deuda['actor_id']
            if actor_id not in proveedores_con_deuda:
                proveedores_con_deuda[actor_id] = []
            proveedores_con_deuda[actor_id].append({
                'moneda': deuda['moneda'],
                'monto': deuda['monto_pendiente']
            })
    
    if not proveedores_con_deuda:
        await reply_text(update, "❌ No proveedores con deudas pendientes.")
        return ConversationHandler.END
    
    # Obtener todos los proveedores para mostrar
    proveedores = ProveedorService.listar()
    proveedores_con_deuda_list = [p for p in proveedores if p['name'].upper() in proveedores_con_deuda]
    
    if not proveedores_con_deuda_list:
        await reply_text(update, "❌ No se encontraron proveedores registrados con deudas.")
        return ConversationHandler.END
    
    text = "💸 <b>Pago a Proveedor</b>\n\n"
    text += "Select el <b>proveedor</b> al que deseas pagar:"
    
    keyboard: List[List[InlineKeyboardButton]] = []
    for prov in proveedores_con_deuda_list:
        prov_name = prov['name'].upper()
        deudas_info = proveedores_con_deuda[prov_name]
        deuda_text = ", ".join([f"{d['monto']:.2f} {d['moneda'].upper()}" for d in deudas_info])
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {prov['name']} ({deuda_text})",
                callback_data=f"pago_prov:proveedor:{prov['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="pago_prov:cancel")])
    
    await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
    return PAGO_PROV_PROVEEDOR


async def pago_prov_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection del proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov:proveedor:"):
        proveedor_id = int(data.split(":")[-1])
        context.user_data["pago_prov_proveedor_id"] = proveedor_id
        
        proveedor = ProveedorService.obtener_por_id(proveedor_id)
        if not proveedor:
            await reply_text(update, "❌ Proveedor not found.")
            return ConversationHandler.END
        
        # Obtener deudas del proveedor
        with get_db_connection() as conn:
            deudas = DeudaRepository.obtener_pendientes(conn)
        
        deudas_proveedor = [
            d for d in deudas 
            if d['actor_id'] == proveedor['name'].upper() and d['tipo'] == 'POR_PAGAR'
        ]
        
        if not deudas_proveedor:
            await reply_text(update, "❌ Este proveedor no tiene deudas pendientes.")
            return ConversationHandler.END
        
        text = f"🏢 <b>Proveedor:</b> {proveedor['name']}\n\n"
        text += "<b>Deudas pendientes:</b>\n"
        for deuda in deudas_proveedor:
            text += f"  • {deuda['monto_pendiente']:,.2f} {deuda['moneda'].upper()}\n"
        text += "\nDesde que tipo de caja deseas pagar?"
        
        keyboard = [
            [
                InlineKeyboardButton("🏦 Caja Interna (Cuba)", callback_data="pago_prov:tipo_caja:interna"),
                InlineKeyboardButton("🌍 Caja Externa (USA)", callback_data="pago_prov:tipo_caja:externa"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="pago_prov:cancel")],
        ]
        
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return PAGO_PROV_TIPO_CAJA
    
    return PAGO_PROV_PROVEEDOR


async def pago_prov_tipo_caja_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection del tipo de caja."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov:tipo_caja:"):
        tipo_caja = data.split(":")[-1]
        context.user_data["pago_prov_tipo_caja"] = tipo_caja
        
        if tipo_caja == "interna":
            # Mostrar cajas internas
            cajas = CajaService.listar()
            if not cajas:
                await reply_text(update, "❌ No cajas internas disponibles.")
                return ConversationHandler.END
            
            text = "🏦 <b>Caja Interna</b>\n\n"
            text += "Select la <b>caja</b> desde la que deseas pagar:"
            
            await reply_html(update, text, reply_markup=create_caja_keyboard("pago_prov:caja_interna"))
            return PAGO_PROV_CAJA_INTERNA
        
        elif tipo_caja == "externa":
            # Mostrar cajas externas
            cajas_externas = CajaExternaService.listar()
            if not cajas_externas:
                await reply_text(update, "❌ No cajas externas disponibles. Crea una primero con /cajas_externas")
                return ConversationHandler.END
            
            text = "🌍 <b>Caja Externa</b>\n\n"
            text += "Select la <b>caja externa</b> desde la que deseas pagar:"
            
            keyboard: List[List[InlineKeyboardButton]] = []
            for caja in cajas_externas:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🌍 {caja['nombre']} - {caja['ubicacion']}",
                        callback_data=f"pago_prov:caja_externa:{caja['id']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="pago_prov:cancel")])
            
            await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
            return PAGO_PROV_CAJA_EXTERNA
    
    return PAGO_PROV_TIPO_CAJA


async def pago_prov_caja_interna_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja interna."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov:caja_interna:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["pago_prov_caja_interna_id"] = caja_id
        
        caja = CajaService.obtener_por_id(caja_id)
        if not caja:
            await reply_text(update, "❌ Caja not found.")
            return ConversationHandler.END
        
        text = f"🏦 <b>Caja:</b> {caja['nombre']}\n\n"
        text += "Send el <b>monto</b> a pagar:"
        
        await reply_html(update, text, reply_markup=create_back_keyboard("pago_prov"))
        return PAGO_PROV_MONTO
    
    return PAGO_PROV_CAJA_INTERNA


async def pago_prov_caja_externa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de caja externa."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov:caja_externa:"):
        caja_externa_id = int(data.split(":")[-1])
        context.user_data["pago_prov_caja_externa_id"] = caja_externa_id
        
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        if not caja_externa:
            await reply_text(update, "❌ Caja externa not found.")
            return ConversationHandler.END
        
        # Para caja externa, necesitamos selectr un producto
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_todos(conn)
        
        if not productos:
            await reply_text(update, "❌ No productos disponibles. Crea uno primero con /productos")
            return ConversationHandler.END
        
        text = f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} - {caja_externa['ubicacion']}\n\n"
        text += "Select el <b>producto</b> asociado al pago:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for prod in productos[:20]:  # Limitar a 20 productos
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {prod['codigo']} - {prod['nombre']}",
                    callback_data=f"pago_prov:producto:{prod['codigo']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="pago_prov:cancel")])
        
        await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
        return PAGO_PROV_PRODUCTO
    
    return PAGO_PROV_CAJA_EXTERNA


async def pago_prov_producto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection del producto (solo para cajas externas)."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov:producto:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["pago_prov_producto_codigo"] = producto_codigo
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto not found.")
            return ConversationHandler.END
        
        text = f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n\n"
        text += "Send el <b>monto</b> a pagar:"
        
        await reply_html(update, text, reply_markup=create_back_keyboard("pago_prov"))
        return PAGO_PROV_MONTO
    
    return PAGO_PROV_PRODUCTO


async def pago_prov_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto del pago."""
    from utils.telegram_helpers import reply_html, reply_text
    
    try:
        monto = validate_monto(update.message.text)
        context.user_data["pago_prov_monto"] = monto
        
        text = f"💰 <b>Monto:</b> {monto:.2f}\n\n"
        text += "Select la <b>moneda</b>:"
        
        await reply_html(update, text, reply_markup=create_moneda_keyboard("pago_prov_moneda"))
        return PAGO_PROV_MONEDA
        
    except ValidationError as e:
        await reply_text(update, f"❌ {e}")
        return PAGO_PROV_MONTO


async def pago_prov_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selection de moneda."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data.startswith("pago_prov_moneda:"):
        moneda = data.split(":")[-1]
        context.user_data["pago_prov_moneda"] = moneda
        
        text = f"💱 <b>Moneda:</b> {moneda.upper()}\n\n"
        text += "Send el <b>motivo</b> del pago (opcional, puedes escribir 'sin motivo'):"
        
        await reply_html(update, text, reply_markup=create_back_keyboard("pago_prov"))
        return PAGO_PROV_MOTIVO
    
    return PAGO_PROV_MONEDA


async def pago_prov_motivo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el motivo del pago."""
    from utils.telegram_helpers import reply_html, reply_text
    
    motivo = update.message.text.strip()
    if motivo.lower() in ['sin motivo', 'n/a', '']:
        motivo = None
    context.user_data["pago_prov_motivo"] = motivo
    
    # Mostrar resumen y confirmar
    proveedor_id = context.user_data.get("pago_prov_proveedor_id")
    tipo_caja = context.user_data.get("pago_prov_tipo_caja")
    monto = context.user_data.get("pago_prov_monto")
    moneda = context.user_data.get("pago_prov_moneda")
    
    proveedor = ProveedorService.obtener_por_id(proveedor_id)
    
    text = "📋 <b>Resumen del Pago</b>\n\n"
    text += f"🏢 <b>Proveedor:</b> {proveedor['name']}\n"
    text += f"💰 <b>Monto:</b> {monto:.2f} {moneda.upper()}\n"
    
    if tipo_caja == "interna":
        caja_id = context.user_data.get("pago_prov_caja_interna_id")
        caja = CajaService.obtener_por_id(caja_id)
        text += f"🏦 <b>Caja:</b> {caja['nombre']}\n"
    else:
        caja_externa_id = context.user_data.get("pago_prov_caja_externa_id")
        producto_codigo = context.user_data.get("pago_prov_producto_codigo")
        caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        text += f"🌍 <b>Caja Externa:</b> {caja_externa['nombre']} - {caja_externa['ubicacion']}\n"
        text += f"📦 <b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
    
    if motivo:
        text += f"📝 <b>Motivo:</b> {motivo}\n"
    
    text += "\nConfirmas el pago?"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="pago_prov_confirm:yes"),
            InlineKeyboardButton("❌ Cancel", callback_data="pago_prov_confirm:no"),
        ],
    ]
    
    await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))
    return PAGO_PROV_CONFIRM


async def pago_prov_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y procesa el pago."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "pago_prov_confirm:no" or data == "pago_prov:cancel":
        keys_to_remove = [
            "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
            "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
            "pago_prov_moneda", "pago_prov_motivo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation cancelada.")
        return ConversationHandler.END
    
    if data == "pago_prov_confirm:yes":
        try:
            proveedor_id = context.user_data.get("pago_prov_proveedor_id")
            tipo_caja = context.user_data.get("pago_prov_tipo_caja")
            monto = context.user_data.get("pago_prov_monto")
            moneda = context.user_data.get("pago_prov_moneda")
            motivo = context.user_data.get("pago_prov_motivo")
            user_id = update.effective_user.id
            
            proveedor = ProveedorService.obtener_por_id(proveedor_id)
            proveedor_nombre = proveedor['name'].upper()
            
            if tipo_caja == "interna":
                # Pago desde caja interna (gasto normal)
                caja_id = context.user_data.get("pago_prov_caja_interna_id")
                caja = CajaService.obtener_por_id(caja_id)
                
                descripcion = f"PAGO a Proveedor: {proveedor_nombre}"
                if motivo:
                    descripcion += f" - Motivo: {motivo}"
                
                # Registrar gasto
                ContabilidadService.registrar_gasto(
                    monto, moneda, caja_id, user_id, descripcion
                )
                
                # Update deuda
                try:
                    DeudaService.update_deuda(proveedor_nombre, monto, moneda, 'POR_PAGAR', es_incremento=False)
                    mensaje_deuda = f"<b>Deuda Actualizada:</b> Monto {monto:.2f} {moneda.upper()} restado de POR PAGAR."
                except ValueError:
                    mensaje_deuda = "<b>Aviso:</b> No se encontro deuda 'POR PAGAR' para este proveedor."
                
                await reply_html(
                    update,
                    f"💸 <b>Pago a Proveedor Registrado!</b>\n\n"
                    f"<b>Proveedor:</b> {proveedor_nombre}\n"
                    f"<b>Monto:</b> -{monto:.2f} {moneda.upper()} de {caja['nombre'].upper()}\n"
                    f"<b>Motivo:</b> {motivo if motivo else 'Sin motivo'}\n"
                    f"{mensaje_deuda}"
                )
                
            else:
                # Pago desde caja externa (transferencia externa)
                caja_externa_id = context.user_data.get("pago_prov_caja_externa_id")
                producto_codigo = context.user_data.get("pago_prov_producto_codigo")
                
                # Necesitamos una caja interna de origen para la transferencia
                # Por ahora, usaremos la primera caja disponible o pediremos al usuario
                cajas = CajaService.listar()
                if not cajas:
                    await reply_text(update, "❌ No cajas internas disponibles para realizar la transferencia.")
                    return ConversationHandler.END
                
                # Usar la primera caja como origen (o podriamos pedir al usuario)
                caja_origen_id = cajas[0]['id']
                caja_origen = cajas[0]
                
                descripcion = f"PAGO a Proveedor: {proveedor_nombre}"
                if motivo:
                    descripcion += f" - Motivo: {motivo}"
                
                # Registrar transferencia externa
                from services.cajas_externas_service import CajaExternaService
                transferencia = CajaExternaService.registrar_transferencia_externa(
                    caja_origen_id, caja_externa_id, producto_codigo, monto, moneda, user_id, descripcion
                )
                
                # Update deuda
                try:
                    DeudaService.update_deuda(proveedor_nombre, monto, moneda, 'POR_PAGAR', es_incremento=False)
                    mensaje_deuda = f"<b>Deuda Actualizada:</b> Monto {monto:.2f} {moneda.upper()} restado de POR PAGAR."
                except ValueError:
                    mensaje_deuda = "<b>Aviso:</b> No se encontro deuda 'POR PAGAR' para este proveedor."
                
                caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
                with get_db_connection() as conn:
                    producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
                
                await reply_html(
                    update,
                    f"💸 <b>Pago a Proveedor Registrado!</b>\n\n"
                    f"<b>Proveedor:</b> {proveedor_nombre}\n"
                    f"<b>Monto Enviado:</b> {monto:.2f} {moneda.upper()}\n"
                    f"<b>Monto Envio:</b> {transferencia['monto_envio']:.2f} {moneda.upper()}\n"
                    f"<b>Monto Recibido:</b> {transferencia['monto_recibido']:.2f} {moneda.upper()}\n"
                    f"<b>Desde:</b> {caja_origen['nombre']}\n"
                    f"<b>Hacia:</b> {caja_externa['nombre']} - {caja_externa['ubicacion']}\n"
                    f"<b>Producto:</b> {producto['codigo']} - {producto['nombre']}\n"
                    f"<b>Motivo:</b> {motivo if motivo else 'Sin motivo'}\n"
                    f"{mensaje_deuda}"
                )
            
            logger.info(f"Pago a Proveedor {proveedor_nombre} registrado por {user_id}")
            
            # Limpiar datos
            keys_to_remove = [
                "pago_prov_proveedor_id", "pago_prov_tipo_caja", "pago_prov_caja_interna_id",
                "pago_prov_caja_externa_id", "pago_prov_producto_codigo", "pago_prov_monto",
                "pago_prov_moneda", "pago_prov_motivo"
            ]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
            return ConversationHandler.END
            
        except ValueError as e:
            await reply_text(update, f"❌ Error: {e}")
            return PAGO_PROV_CONFIRM
        except Exception as e:
            logger.error(f"Error inesperado en pago a proveedor: {e}", exc_info=True)
            await reply_text(update, f"❌ An error occurred inesperado: {e}")
            return PAGO_PROV_CONFIRM
    
    return PAGO_PROV_CONFIRM


# ConversationHandler para pago a proveedor
pago_proveedor_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("pago_proveedor", pago_proveedor_entry),
        CommandHandler("pago_prov", pago_proveedor_entry),  # Alias
    ],
    states={
        PAGO_PROV_PROVEEDOR: [
            CallbackQueryHandler(pago_prov_proveedor_callback, pattern=r"^pago_prov:(proveedor:|cancel)"),
        ],
        PAGO_PROV_TIPO_CAJA: [
            CallbackQueryHandler(pago_prov_tipo_caja_callback, pattern=r"^pago_prov:(tipo_caja:|cancel)"),
        ],
        PAGO_PROV_CAJA_INTERNA: [
            CallbackQueryHandler(pago_prov_caja_interna_callback, pattern=r"^pago_prov:(caja_interna:|cancel)"),
        ],
        PAGO_PROV_CAJA_EXTERNA: [
            CallbackQueryHandler(pago_prov_caja_externa_callback, pattern=r"^pago_prov:(caja_externa:|cancel)"),
        ],
        PAGO_PROV_PRODUCTO: [
            CallbackQueryHandler(pago_prov_producto_callback, pattern=r"^pago_prov:(producto:|cancel)"),
        ],
        PAGO_PROV_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pago_prov_monto_receive),
            CallbackQueryHandler(pago_prov_caja_interna_callback, pattern=r"^pago_prov:.*"),
        ],
        PAGO_PROV_MONEDA: [
            CallbackQueryHandler(pago_prov_moneda_callback, pattern=r"^pago_prov_moneda:|pago_prov:cancel"),
        ],
        PAGO_PROV_MOTIVO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pago_prov_motivo_receive),
            CallbackQueryHandler(pago_prov_moneda_callback, pattern=r"^pago_prov:.*"),
        ],
        PAGO_PROV_CONFIRM: [
            CallbackQueryHandler(pago_prov_confirm_callback, pattern=r"^pago_prov_confirm:"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_conversation),
        MessageHandler(filters.COMMAND, _cancel_conversation),
    ],
    name="pago_proveedor_conversation",
    persistent=False,
)

