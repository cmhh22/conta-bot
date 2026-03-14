"""
Handlers para operaciones de logística (mover productos entre contenedores y almacenes).
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
from utils.telegram_helpers import reply_html, reply_text
from services.logistica_service import (
    agregar_producto_a_contenedor,
    obtener_productos_de_contenedor,
    mover_producto_contenedor_a_almacen,
    mover_producto_almacen_a_almacen,
    ajustar_inventario_almacen,
    obtener_inventario_almacen,
    obtener_resumen_logistica,
    consignar_desde_almacen,
    mover_consignacion_vendedor,
    pagar_consignacion,
)
from services.contenedores_service import ContenedorService
from services.almacenes_service import listar as listar_almacenes, obtener_por_id
from services.vendedores_service import VendedorService
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService
from database.connection import get_db_connection
from database.repositories import ProductoRepository

logger = logging.getLogger(__name__)

# Estados para mover productos (contenedor → almacén)
MOVER_MENU, MOVER_SEL_CONTENEDOR, MOVER_SEL_ALMACEN, MOVER_SEL_PRODUCTO, MOVER_CANTIDAD = range(5)

# Estados para agregar productos a contenedores
AGREGAR_SEL_CONTENEDOR, AGREGAR_SEL_PRODUCTO, AGREGAR_CANTIDAD = range(5, 8)

# Estados para mover entre almacenes
MOVER_ALM_SEL_ORIGEN, MOVER_ALM_SEL_DESTINO, MOVER_ALM_SEL_PRODUCTO, MOVER_ALM_CANTIDAD = range(8, 12)

# Estados para consignar desde almacenes
CONSIGNAR_SEL_ALMACEN, CONSIGNAR_SEL_PRODUCTO, CONSIGNAR_SEL_VENDEDOR, CONSIGNAR_PRECIO, CONSIGNAR_MONEDA, CONSIGNAR_CANTIDAD = range(12, 18)

# Estados para mover consignaciones entre vendedores
MOVER_CONS_SEL_ORIGEN, MOVER_CONS_SEL_PRODUCTO, MOVER_CONS_SEL_DESTINO, MOVER_CONS_CANTIDAD = range(18, 22)

# Estados para pagar consignaciones
PAGAR_CONS_SEL_VENDEDOR, PAGAR_CONS_SEL_MONEDA, PAGAR_CONS_MONTO, PAGAR_CONS_SEL_CAJA = range(22, 26)


@admin_only
async def productos_contenedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra los productos de un contenedor."""
    if not context.args or len(context.args) < 1:
        await reply_text(
            update,
            "📦 <b>Productos de Contenedor</b>\n\n"
            "Uso: <code>/productos_contenedor [ID]</code>\n"
            "Ejemplo: <code>/productos_contenedor 1</code>"
        )
        return
    
    try:
        contenedor_id = int(context.args[0])
        productos = obtener_productos_de_contenedor(contenedor_id)
        
        contenedor = ContenedorService.obtener_por_id(contenedor_id)
        if not contenedor:
            await reply_text(update, f"❌ No existe un contenedor con ID {contenedor_id}")
            return
        
        if not productos:
            await reply_html(
                update,
                f"📦 <b>Contenedor: {contenedor['nombre']}</b>\n\n"
                f"Este contenedor no tiene productos registrados."
            )
            return
        
        text = f"📦 <b>Productos en Contenedor: {contenedor['nombre']}</b>\n\n"
        for prod in productos:
            text += (
                f"• <b>{prod['producto_nombre']}</b> ({prod['producto_codigo']})\n"
                f"  Cantidad: {prod['cantidad']}\n\n"
            )
        
        await reply_html(update, text)
    except ValueError:
        await reply_text(update, "❌ El ID debe ser un número válido.")
    except Exception as e:
        logger.error(f"Error obteniendo productos del contenedor: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def inventario_almacen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el inventario de un almacén."""
    from services.almacenes_service import obtener_por_id
    
    # Si no hay argumentos, mostrar lista de almacenes para seleccionar
    if not context.args or len(context.args) < 1:
        almacenes = listar_almacenes()
        if not almacenes:
            await reply_text(update, "❌ No hay almacenes disponibles. Crea uno primero.")
            return
        
        text = "🏢 <b>Selecciona un almacén para ver su inventario:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in almacenes:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {alm['nombre']}",
                    callback_data=f"inv_alm:{alm['id']}"
                )
            ])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return
    
    # Si hay argumentos, mostrar inventario directamente
    try:
        almacen_id = int(context.args[0])
        inventario = obtener_inventario_almacen(almacen_id)
        
        almacen = obtener_por_id(almacen_id)
        if not almacen:
            await reply_text(update, f"❌ No existe un almacén con ID {almacen_id}")
            return
        
        if not inventario:
            await reply_html(
                update,
                f"🏢 <b>Almacén: {almacen['nombre']}</b>\n\n"
                f"Este almacén no tiene productos en inventario."
            )
            return
        
        text = f"🏢 <b>Inventario: {almacen['nombre']}</b>\n\n"
        for item in inventario:
            text += (
                f"• <b>{item['producto_nombre']}</b> ({item['producto_codigo']})\n"
                f"  Cantidad: {item['cantidad']}\n\n"
            )
        
        await reply_html(update, text)
    except ValueError:
        await reply_text(update, "❌ El ID debe ser un número válido.")
    except Exception as e:
        logger.error(f"Error obteniendo inventario del almacén: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def inventario_almacen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el callback para mostrar inventario de almacén."""
    from services.almacenes_service import obtener_por_id
    
    q = update.callback_query
    if q:
        await q.answer()
    
    if not q or not q.data:
        return
    
    if q.data.startswith("inv_alm:"):
        try:
            almacen_id = int(q.data.split(":")[-1])
            inventario = obtener_inventario_almacen(almacen_id)
            
            almacen = obtener_por_id(almacen_id)
            if not almacen:
                await reply_text(update, f"❌ No existe un almacén con ID {almacen_id}")
                return
            
            if not inventario:
                text = f"📦 <b>Inventario: {almacen['nombre']}</b>\n\nEste almacén no tiene productos en inventario."
            else:
                text = f"📦 <b>Inventario: {almacen['nombre']}</b>\n\n"
                for item in inventario:
                    text += (
                        f"• <b>{item['producto_nombre']}</b> ({item['producto_codigo']})\n"
                        f"  Cantidad: {item['cantidad']}\n\n"
                    )
            
            try:
                await q.edit_message_text(text, parse_mode="HTML")
            except Exception:
                await reply_html(update, text)
        except ValueError:
            await reply_text(update, "❌ El ID debe ser un número válido.")
        except Exception as e:
            logger.error(f"Error obteniendo inventario del almacén: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def mover_producto_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover productos de contenedor a almacén."""
    # Limpiar datos previos
    keys_to_remove = [
        "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    # Listar contenedores
    contenedores = ContenedorService.listar()
    if not contenedores:
        await reply_text(update, "❌ No hay contenedores disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Mover Producto: Contenedor → Almacén</b>\n\nSelecciona el contenedor:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in contenedores:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {cont['nombre']}",
                callback_data=f"log:cont:{cont['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="log:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_SEL_CONTENEDOR


async def mover_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de mover productos."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("log:cont:"):
        contenedor_id = int(data.split(":")[-1])
        context.user_data["log_cont_id"] = contenedor_id
        
        # Obtener productos del contenedor
        try:
            productos = obtener_productos_de_contenedor(contenedor_id)
            if not productos:
                await reply_text(update, "❌ Este contenedor no tiene productos.")
                return ConversationHandler.END
            
            contenedor = ContenedorService.obtener_por_id(contenedor_id)
            text = f"📦 <b>Contenedor: {contenedor['nombre']}</b>\n\nSelecciona el producto:"
            keyboard: List[List[InlineKeyboardButton]] = []
            for prod in productos:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prod['producto_nombre']} ({prod['cantidad']})",
                        callback_data=f"log:prod:{prod['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="log:back")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return MOVER_SEL_PRODUCTO
        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    if data.startswith("log:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["log_prod_codigo"] = producto_codigo
        
        # Listar almacenes
        almacenes = listar_almacenes()
        if not almacenes:
            await reply_text(update, "❌ No hay almacenes disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        text = "🏢 <b>Selecciona el almacén destino:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in almacenes:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {alm['nombre']}",
                    callback_data=f"log:alm:{alm['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="log:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_SEL_ALMACEN
    
    if data.startswith("log:alm:"):
        almacen_id = int(data.split(":")[-1])
        context.user_data["log_alm_id"] = almacen_id
        
        cont_id = context.user_data.get("log_cont_id")
        prod_codigo = context.user_data.get("log_prod_codigo")
        
        if not cont_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        productos = obtener_productos_de_contenedor(cont_id)
        producto = next((p for p in productos if p["producto_codigo"] == prod_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado en el contenedor.")
            return ConversationHandler.END
        
        contenedor = ContenedorService.obtener_por_id(cont_id)
        from services.almacenes_service import obtener_por_id
        almacen = obtener_por_id(almacen_id)
        
        await reply_html(
            update,
            f"📦 <b>Mover Producto</b>\n\n"
            f"Contenedor: <code>{contenedor['nombre']}</code>\n"
            f"Producto: <code>{producto['producto_nombre']}</code>\n"
            f"Almacén: <code>{almacen['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Envía la <b>cantidad</b> a mover:"
        )
        return MOVER_CANTIDAD
    
    if data == "log:back":
        return await mover_producto_entry(update, context)
    
    if data == "log:cancel":
        keys_to_remove = [
            "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return MOVER_MENU


async def mover_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza el movimiento."""
    if not update.message:
        return MOVER_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return MOVER_CANTIDAD
        
        cont_id = context.user_data.get("log_cont_id")
        alm_id = context.user_data.get("log_alm_id")
        prod_codigo = context.user_data.get("log_prod_codigo")
        user_id = update.effective_user.id
        
        if not all([cont_id, alm_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar el movimiento
        resultado = mover_producto_contenedor_a_almacen(
            cont_id, alm_id, prod_codigo, cantidad, user_id
        )
        
        contenedor = ContenedorService.obtener_por_id(cont_id)
        almacen = obtener_por_id(alm_id)
        
        await reply_html(
            update,
            f"✅ <b>Producto Movido</b>\n\n"
            f"De: <code>{contenedor['nombre']}</code>\n"
            f"A: <code>{almacen['nombre']}</code>\n"
            f"Cantidad: <b>{cantidad}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return MOVER_CANTIDAD
    except Exception as e:
        logger.error(f"Error moviendo producto: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return MOVER_CANTIDAD


async def mover_cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación de mover producto."""
    keys_to_remove = [
        "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler para mover productos
mover_producto_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("mover_producto", mover_producto_entry),
    ],
    states={
        MOVER_SEL_CONTENEDOR: [
            CallbackQueryHandler(mover_menu_callback, pattern=r"^log:(cont:|cancel)"),
        ],
        MOVER_SEL_PRODUCTO: [
            CallbackQueryHandler(mover_menu_callback, pattern=r"^log:(prod:|back)"),
        ],
        MOVER_SEL_ALMACEN: [
            CallbackQueryHandler(mover_menu_callback, pattern=r"^log:(alm:|back)"),
        ],
        MOVER_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mover_cantidad_receive),
            CallbackQueryHandler(mover_menu_callback, pattern=r"^log:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="mover_producto_conversation",
    persistent=False,
)


# ========== AGREGAR PRODUCTOS A CONTENEDORES ==========

@admin_only
async def agregar_producto_contenedor_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para agregar productos a contenedores."""
    keys_to_remove = ["agr_cont_id", "agr_prod_codigo", "agr_cantidad"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    contenedores = ContenedorService.listar()
    if not contenedores:
        await reply_text(update, "❌ No hay contenedores disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Agregar Producto a Contenedor</b>\n\nSelecciona el contenedor:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in contenedores:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {cont['nombre']}",
                callback_data=f"agr:cont:{cont['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="agr:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return AGREGAR_SEL_CONTENEDOR


async def agregar_producto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de agregar productos."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("agr:cont:"):
        contenedor_id = int(data.split(":")[-1])
        context.user_data["agr_cont_id"] = contenedor_id
        
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_todos(conn)
        
        if not productos:
            await reply_text(update, "❌ No hay productos disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        contenedor = ContenedorService.obtener_por_id(contenedor_id)
        text = f"📦 <b>Contenedor: {contenedor['nombre']}</b>\n\nSelecciona el producto:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for prod in productos[:20]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{prod['nombre']} ({prod['codigo']})",
                    callback_data=f"agr:prod:{prod['codigo']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="agr:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return AGREGAR_SEL_PRODUCTO
    
    if data.startswith("agr:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["agr_prod_codigo"] = producto_codigo
        
        cont_id = context.user_data.get("agr_cont_id")
        contenedor = ContenedorService.obtener_por_id(cont_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Agregar Producto</b>\n\n"
            f"Contenedor: <code>{contenedor['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({producto_codigo})\n\n"
            f"Envía la <b>cantidad</b> a agregar:"
        )
        return AGREGAR_CANTIDAD
    
    if data == "agr:back":
        return await agregar_producto_contenedor_entry(update, context)
    
    if data == "agr:cancel":
        keys_to_remove = ["agr_cont_id", "agr_prod_codigo", "agr_cantidad"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return AGREGAR_SEL_CONTENEDOR


async def agregar_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y agrega el producto al contenedor."""
    if not update.message:
        return AGREGAR_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return AGREGAR_CANTIDAD
        
        cont_id = context.user_data.get("agr_cont_id")
        prod_codigo = context.user_data.get("agr_prod_codigo")
        
        if not all([cont_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        resultado = agregar_producto_a_contenedor(cont_id, prod_codigo, cantidad)
        
        contenedor = ContenedorService.obtener_por_id(cont_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"✅ <b>Producto Agregado</b>\n\n"
            f"Contenedor: <code>{contenedor['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code>\n"
            f"Cantidad: <b>{cantidad}</b>"
        )
        
        keys_to_remove = ["agr_cont_id", "agr_prod_codigo", "agr_cantidad"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return AGREGAR_CANTIDAD
    except Exception as e:
        logger.error(f"Error agregando producto: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return AGREGAR_CANTIDAD


agregar_producto_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("agregar_producto_contenedor", agregar_producto_contenedor_entry)],
    states={
        AGREGAR_SEL_CONTENEDOR: [CallbackQueryHandler(agregar_producto_callback, pattern=r"^agr:(cont:|cancel)")],
        AGREGAR_SEL_PRODUCTO: [CallbackQueryHandler(agregar_producto_callback, pattern=r"^agr:(prod:|back)")],
        AGREGAR_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_cantidad_receive),
            CallbackQueryHandler(agregar_producto_callback, pattern=r"^agr:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="agregar_producto_conversation",
    persistent=False,
)


# ========== REPORTES DE LOGÍSTICA ==========

@admin_only
async def resumen_logistica_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra un resumen general de la logística."""
    try:
        resumen = obtener_resumen_logistica()
        
        text = "📊 <b>Resumen de Logística</b>\n\n"
        text += f"📦 <b>Contenedores:</b>\n"
        text += f"  • Total: {resumen['total_contenedores']}\n"
        text += f"  • Productos únicos: {resumen['total_productos_contenedores']}\n\n"
        text += f"🏢 <b>Almacenes:</b>\n"
        text += f"  • Total: {resumen['total_almacenes']}\n"
        text += f"  • Productos únicos: {resumen['total_productos_almacenes']}\n"
        
        await reply_html(update, text)
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


# ========== MOVER PRODUCTOS ENTRE ALMACENES ==========

@admin_only
async def mover_almacen_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover productos entre almacenes."""
    keys_to_remove = [
        "mover_alm_origen_id", "mover_alm_destino_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    almacenes = listar_almacenes()
    if len(almacenes) < 2:
        await reply_text(update, "❌ Necesitas al menos 2 almacenes para mover productos entre ellos.")
        return ConversationHandler.END
    
    text = "🏢 <b>Mover Producto: Almacén → Almacén</b>\n\nSelecciona el almacén <b>origen</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in almacenes:
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {alm['nombre']}",
                callback_data=f"mover_alm:origen:{alm['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="mover_alm:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_ALM_SEL_ORIGEN


async def mover_almacen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de mover productos entre almacenes."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("mover_alm:origen:"):
        almacen_id = int(data.split(":")[-1])
        context.user_data["mover_alm_origen_id"] = almacen_id
        
        # Listar almacenes destino (excluyendo el origen)
        almacenes = listar_almacenes()
        almacenes_destino = [a for a in almacenes if a["id"] != almacen_id]
        
        if not almacenes_destino:
            await reply_text(update, "❌ No hay otros almacenes disponibles como destino.")
            return ConversationHandler.END
        
        almacen_origen = obtener_por_id(almacen_id)
        text = f"🏢 <b>Origen: {almacen_origen['nombre']}</b>\n\nSelecciona el almacén <b>destino</b>:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in almacenes_destino:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {alm['nombre']}",
                    callback_data=f"mover_alm:destino:{alm['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="mover_alm:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_ALM_SEL_DESTINO
    
    if data.startswith("mover_alm:destino:"):
        almacen_id = int(data.split(":")[-1])
        context.user_data["mover_alm_destino_id"] = almacen_id
        
        origen_id = context.user_data.get("mover_alm_origen_id")
        if not origen_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener productos del almacén origen
        try:
            inventario = obtener_inventario_almacen(origen_id)
            if not inventario:
                await reply_text(update, "❌ El almacén origen no tiene productos en inventario.")
                return ConversationHandler.END
            
            almacen_origen = obtener_por_id(origen_id)
            almacen_destino = obtener_por_id(almacen_id)
            
            text = (
                f"🏢 <b>Mover Producto</b>\n\n"
                f"Origen: <code>{almacen_origen['nombre']}</code>\n"
                f"Destino: <code>{almacen_destino['nombre']}</code>\n\n"
                f"Selecciona el producto:"
            )
            keyboard: List[List[InlineKeyboardButton]] = []
            for item in inventario:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{item['producto_nombre']} ({item['cantidad']})",
                        callback_data=f"mover_alm:prod:{item['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="mover_alm:back")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return MOVER_ALM_SEL_PRODUCTO
        except Exception as e:
            logger.error(f"Error obteniendo inventario: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    if data.startswith("mover_alm:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["mover_alm_prod_codigo"] = producto_codigo
        
        origen_id = context.user_data.get("mover_alm_origen_id")
        destino_id = context.user_data.get("mover_alm_destino_id")
        
        if not origen_id or not destino_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        inventario = obtener_inventario_almacen(origen_id)
        producto = next((p for p in inventario if p["producto_codigo"] == producto_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado en el almacén origen.")
            return ConversationHandler.END
        
        almacen_origen = obtener_por_id(origen_id)
        almacen_destino = obtener_por_id(destino_id)
        
        with get_db_connection() as conn:
            prod = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"🏢 <b>Mover Producto</b>\n\n"
            f"Origen: <code>{almacen_origen['nombre']}</code>\n"
            f"Destino: <code>{almacen_destino['nombre']}</code>\n"
            f"Producto: <code>{prod['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Envía la <b>cantidad</b> a mover:"
        )
        return MOVER_ALM_CANTIDAD
    
    if data == "mover_alm:back":
        return await mover_almacen_entry(update, context)
    
    if data == "mover_alm:cancel":
        keys_to_remove = [
            "mover_alm_origen_id", "mover_alm_destino_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return MOVER_ALM_SEL_ORIGEN


async def mover_almacen_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza el movimiento entre almacenes."""
    if not update.message:
        return MOVER_ALM_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return MOVER_ALM_CANTIDAD
        
        origen_id = context.user_data.get("mover_alm_origen_id")
        destino_id = context.user_data.get("mover_alm_destino_id")
        prod_codigo = context.user_data.get("mover_alm_prod_codigo")
        user_id = update.effective_user.id
        
        if not all([origen_id, destino_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar el movimiento
        resultado = mover_producto_almacen_a_almacen(
            origen_id, destino_id, prod_codigo, cantidad, user_id
        )
        
        almacen_origen = obtener_por_id(origen_id)
        almacen_destino = obtener_por_id(destino_id)
        
        await reply_html(
            update,
            f"✅ <b>Producto Movido</b>\n\n"
            f"De: <code>{almacen_origen['nombre']}</code>\n"
            f"A: <code>{almacen_destino['nombre']}</code>\n"
            f"Cantidad: <b>{cantidad}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "mover_alm_origen_id", "mover_alm_destino_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return MOVER_ALM_CANTIDAD
    except Exception as e:
        logger.error(f"Error moviendo producto entre almacenes: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return MOVER_ALM_CANTIDAD


mover_almacen_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("mover_almacen", mover_almacen_entry),
    ],
    states={
        MOVER_ALM_SEL_ORIGEN: [
            CallbackQueryHandler(mover_almacen_callback, pattern=r"^mover_alm:(origen:|cancel)"),
        ],
        MOVER_ALM_SEL_DESTINO: [
            CallbackQueryHandler(mover_almacen_callback, pattern=r"^mover_alm:(destino:|back)"),
        ],
        MOVER_ALM_SEL_PRODUCTO: [
            CallbackQueryHandler(mover_almacen_callback, pattern=r"^mover_alm:(prod:|back)"),
        ],
        MOVER_ALM_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mover_almacen_cantidad_receive),
            CallbackQueryHandler(mover_almacen_callback, pattern=r"^mover_alm:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="mover_almacen_conversation",
    persistent=False,
)


# ========== CONSIGNAR DESDE ALMACENES ==========

@admin_only
async def consignar_almacen_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para consignar productos desde almacenes."""
    keys_to_remove = [
        "cons_alm_id", "cons_prod_codigo", "cons_vendedor_id", "cons_precio", "cons_moneda", "cons_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    almacenes = listar_almacenes()
    if not almacenes:
        await reply_text(update, "❌ No hay almacenes disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Consignar Producto desde Almacén</b>\n\nSelecciona el almacén:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in almacenes:
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {alm['nombre']}",
                callback_data=f"cons:alm:{alm['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return CONSIGNAR_SEL_ALMACEN


async def consignar_almacen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de consignación."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("cons:alm:"):
        almacen_id = int(data.split(":")[-1])
        context.user_data["cons_alm_id"] = almacen_id
        
        # Obtener productos del almacén
        try:
            inventario = obtener_inventario_almacen(almacen_id)
            if not inventario:
                await reply_text(update, "❌ Este almacén no tiene productos en inventario.")
                return ConversationHandler.END
            
            almacen = obtener_por_id(almacen_id)
            text = f"🏢 <b>Almacén: {almacen['nombre']}</b>\n\nSelecciona el producto:"
            keyboard: List[List[InlineKeyboardButton]] = []
            for item in inventario:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{item['producto_nombre']} ({item['cantidad']})",
                        callback_data=f"cons:prod:{item['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="cons:back")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return CONSIGNAR_SEL_PRODUCTO
        except Exception as e:
            logger.error(f"Error obteniendo inventario: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    if data.startswith("cons:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["cons_prod_codigo"] = producto_codigo
        
        # Listar vendedores
        vendedores = VendedorService.listar()
        if not vendedores:
            await reply_text(update, "❌ No hay vendedores disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        text = "👤 <b>Selecciona el vendedor:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for vend in vendedores:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {vend['name']}",
                    callback_data=f"cons:vend:{vend['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return CONSIGNAR_SEL_VENDEDOR
    
    if data.startswith("cons:vend:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["cons_vendedor_id"] = vendedor_id
        
        almacen_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        
        if not almacen_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        almacen = obtener_por_id(almacen_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Almacén: <code>{almacen['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({prod_codigo})\n"
            f"Vendedor: <code>{vendedor['name']}</code>\n\n"
            f"Envía el <b>precio unitario</b> de venta:"
        )
        return CONSIGNAR_PRECIO
    
    if data == "cons:back":
        return await consignar_almacen_entry(update, context)
    
    if data == "cons:cancel":
        keys_to_remove = [
            "cons_alm_id", "cons_prod_codigo", "cons_vendedor_id", "cons_precio", "cons_moneda", "cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return CONSIGNAR_SEL_ALMACEN


async def consignar_precio_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el precio."""
    if not update.message:
        return CONSIGNAR_PRECIO
    
    try:
        precio = float((update.message.text or "").strip())
        if precio <= 0:
            await reply_text(update, "❌ El precio debe ser mayor a 0.")
            return CONSIGNAR_PRECIO
        
        context.user_data["cons_precio"] = precio
        
        # Mostrar opciones de moneda
        text = f"✅ Precio: <b>{precio}</b>\n\nSelecciona la <b>moneda</b>:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"cons:moneda:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return CONSIGNAR_MONEDA
    except ValueError:
        await reply_text(update, "❌ El precio debe ser un número válido.")
        return CONSIGNAR_PRECIO


async def consignar_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de moneda."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("cons:moneda:"):
        moneda = data.split(":")[-1]
        context.user_data["cons_moneda"] = moneda
        
        almacen_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        
        if not almacen_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        inventario = obtener_inventario_almacen(almacen_id)
        producto = next((p for p in inventario if p["producto_codigo"] == prod_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado en el almacén.")
            return ConversationHandler.END
        
        almacen = obtener_por_id(almacen_id)
        precio = context.user_data.get("cons_precio")
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Almacén: <code>{almacen['nombre']}</code>\n"
            f"Producto: <code>{producto['producto_nombre']}</code>\n"
            f"Precio: <b>{precio} {moneda.upper()}</b>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Envía la <b>cantidad</b> a consignar:"
        )
        return CONSIGNAR_CANTIDAD
    
    if data == "cons:back":
        # Volver a pedir precio
        almacen_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        vendedor_id = context.user_data.get("cons_vendedor_id")
        
        if not all([almacen_id, prod_codigo, vendedor_id]):
            return await consignar_almacen_entry(update, context)
        
        almacen = obtener_por_id(almacen_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Almacén: <code>{almacen['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({prod_codigo})\n"
            f"Vendedor: <code>{vendedor['name']}</code>\n\n"
            f"Envía el <b>precio unitario</b> de venta:"
        )
        return CONSIGNAR_PRECIO
    
    return CONSIGNAR_MONEDA


async def consignar_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza la consignación."""
    if not update.message:
        return CONSIGNAR_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return CONSIGNAR_CANTIDAD
        
        almacen_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        vendedor_id = context.user_data.get("cons_vendedor_id")
        precio = context.user_data.get("cons_precio")
        moneda = context.user_data.get("cons_moneda")
        user_id = update.effective_user.id
        
        if not all([almacen_id, prod_codigo, vendedor_id, precio, moneda]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar la consignación
        resultado = consignar_desde_almacen(
            almacen_id, prod_codigo, cantidad, vendedor_id, precio, moneda, user_id
        )
        
        almacen = obtener_por_id(almacen_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        await reply_html(
            update,
            f"✅ <b>Consignación Realizada</b>\n\n"
            f"Almacén: <code>{almacen['nombre']}</code>\n"
            f"Producto: <code>{prod_codigo}</code>\n"
            f"Vendedor: <code>{vendedor['name']}</code>\n"
            f"Cantidad: <b>{cantidad}</b>\n"
            f"Precio: <b>{precio} {moneda.upper()}</b>\n\n"
            f"💰 <b>Deuda generada: {resultado['monto_deuda']:.2f} {moneda.upper()}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "cons_alm_id", "cons_prod_codigo", "cons_vendedor_id", "cons_precio", "cons_moneda", "cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return CONSIGNAR_CANTIDAD
    except Exception as e:
        logger.error(f"Error consignando producto: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return CONSIGNAR_CANTIDAD


consignar_almacen_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("consignar_almacen", consignar_almacen_entry),
    ],
    states={
        CONSIGNAR_SEL_ALMACEN: [
            CallbackQueryHandler(consignar_almacen_callback, pattern=r"^cons:(alm:|cancel)"),
        ],
        CONSIGNAR_SEL_PRODUCTO: [
            CallbackQueryHandler(consignar_almacen_callback, pattern=r"^cons:(prod:|back)"),
        ],
        CONSIGNAR_SEL_VENDEDOR: [
            CallbackQueryHandler(consignar_almacen_callback, pattern=r"^cons:(vend:|back)"),
        ],
        CONSIGNAR_PRECIO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, consignar_precio_receive),
            CallbackQueryHandler(consignar_almacen_callback, pattern=r"^cons:.*"),
        ],
        CONSIGNAR_MONEDA: [
            CallbackQueryHandler(consignar_moneda_callback, pattern=r"^cons:(moneda:|back)"),
        ],
        CONSIGNAR_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, consignar_cantidad_receive),
            CallbackQueryHandler(consignar_almacen_callback, pattern=r"^cons:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="consignar_almacen_conversation",
    persistent=False,
)


# ========== MOVER CONSIGNACIONES ENTRE VENDEDORES ==========

@admin_only
async def mover_consignacion_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover consignaciones entre vendedores."""
    keys_to_remove = [
        "mover_cons_origen_id", "mover_cons_destino_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    vendedores = VendedorService.listar()
    if len(vendedores) < 2:
        await reply_text(update, "❌ Necesitas al menos 2 vendedores para mover consignaciones.")
        return ConversationHandler.END
    
    text = "🔄 <b>Mover Consignación: Vendedor → Vendedor</b>\n\nSelecciona el vendedor <b>origen</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {vend['name']}",
                callback_data=f"mover_cons:origen:{vend['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="mover_cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_CONS_SEL_ORIGEN


async def mover_consignacion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de mover consignaciones."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("mover_cons:origen:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["mover_cons_origen_id"] = vendedor_id
        
        # Obtener consignaciones del vendedor origen
        try:
            vendedor = VendedorService.obtener_por_id(vendedor_id)
            with get_db_connection() as conn:
                from database.repositories import ConsignacionRepository
                consignaciones = ConsignacionRepository.obtener_por_vendedor(conn, vendedor['name'])
            
            if not consignaciones:
                await reply_text(update, "❌ Este vendedor no tiene productos consignados.")
                return ConversationHandler.END
            
            text = f"👤 <b>Vendedor Origen: {vendedor['name']}</b>\n\nSelecciona el producto:"
            keyboard: List[List[InlineKeyboardButton]] = []
            for cons in consignaciones:
                with get_db_connection() as conn:
                    producto = ProductoRepository.obtener_por_codigo(conn, cons['codigo'])
                keyboard.append([
                    InlineKeyboardButton(
                        f"{producto['nombre']} ({cons['stock']})",
                        callback_data=f"mover_cons:prod:{cons['codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="mover_cons:back")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return MOVER_CONS_SEL_PRODUCTO
        except Exception as e:
            logger.error(f"Error obteniendo consignaciones: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    if data.startswith("mover_cons:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["mover_cons_prod_codigo"] = producto_codigo
        
        origen_id = context.user_data.get("mover_cons_origen_id")
        if not origen_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Listar vendedores destino (excluyendo el origen)
        vendedores = VendedorService.listar()
        vendedores_destino = [v for v in vendedores if v["id"] != origen_id]
        
        if not vendedores_destino:
            await reply_text(update, "❌ No hay otros vendedores disponibles como destino.")
            return ConversationHandler.END
        
        vendedor_origen = VendedorService.obtener_por_id(origen_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
            from database.repositories import ConsignacionRepository
            consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(
                conn, vendedor_origen['name'], producto_codigo
            )
        
        text = (
            f"🔄 <b>Mover Consignación</b>\n\n"
            f"Origen: <code>{vendedor_origen['name']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({producto_codigo})\n"
            f"Stock disponible: <b>{consignacion['stock']}</b>\n\n"
            f"Selecciona el vendedor <b>destino</b>:"
        )
        keyboard: List[List[InlineKeyboardButton]] = []
        for vend in vendedores_destino:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {vend['name']}",
                    callback_data=f"mover_cons:destino:{vend['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="mover_cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_CONS_SEL_DESTINO
    
    if data.startswith("mover_cons:destino:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["mover_cons_destino_id"] = vendedor_id
        
        origen_id = context.user_data.get("mover_cons_origen_id")
        prod_codigo = context.user_data.get("mover_cons_prod_codigo")
        
        if not origen_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        vendedor_origen = VendedorService.obtener_por_id(origen_id)
        vendedor_destino = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
            from database.repositories import ConsignacionRepository
            consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(
                conn, vendedor_origen['name'], prod_codigo
            )
        
        await reply_html(
            update,
            f"🔄 <b>Mover Consignación</b>\n\n"
            f"De: <code>{vendedor_origen['name']}</code>\n"
            f"A: <code>{vendedor_destino['name']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{consignacion['stock']}</b>\n\n"
            f"Envía la <b>cantidad</b> a mover:"
        )
        return MOVER_CONS_CANTIDAD
    
    if data == "mover_cons:back":
        return await mover_consignacion_entry(update, context)
    
    if data == "mover_cons:cancel":
        keys_to_remove = [
            "mover_cons_origen_id", "mover_cons_destino_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return MOVER_CONS_SEL_ORIGEN


async def mover_consignacion_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza el movimiento de consignación."""
    if not update.message:
        return MOVER_CONS_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return MOVER_CONS_CANTIDAD
        
        origen_id = context.user_data.get("mover_cons_origen_id")
        destino_id = context.user_data.get("mover_cons_destino_id")
        prod_codigo = context.user_data.get("mover_cons_prod_codigo")
        user_id = update.effective_user.id
        
        if not all([origen_id, destino_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar el movimiento
        resultado = mover_consignacion_vendedor(
            origen_id, destino_id, prod_codigo, cantidad, user_id
        )
        
        vendedor_origen = VendedorService.obtener_por_id(origen_id)
        vendedor_destino = VendedorService.obtener_por_id(destino_id)
        
        await reply_html(
            update,
            f"✅ <b>Consignación Movida</b>\n\n"
            f"De: <code>{vendedor_origen['name']}</code>\n"
            f"A: <code>{vendedor_destino['name']}</code>\n"
            f"Producto: <code>{prod_codigo}</code>\n"
            f"Cantidad: <b>{cantidad}</b>\n\n"
            f"💰 Deuda transferida: <b>{resultado['monto_movimiento']:.2f} {resultado['moneda'].upper()}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "mover_cons_origen_id", "mover_cons_destino_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return MOVER_CONS_CANTIDAD
    except Exception as e:
        logger.error(f"Error moviendo consignación: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return MOVER_CONS_CANTIDAD


mover_consignacion_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("mover_consignacion", mover_consignacion_entry),
    ],
    states={
        MOVER_CONS_SEL_ORIGEN: [
            CallbackQueryHandler(mover_consignacion_callback, pattern=r"^mover_cons:(origen:|cancel)"),
        ],
        MOVER_CONS_SEL_PRODUCTO: [
            CallbackQueryHandler(mover_consignacion_callback, pattern=r"^mover_cons:(prod:|back)"),
        ],
        MOVER_CONS_SEL_DESTINO: [
            CallbackQueryHandler(mover_consignacion_callback, pattern=r"^mover_cons:(destino:|back)"),
        ],
        MOVER_CONS_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mover_consignacion_cantidad_receive),
            CallbackQueryHandler(mover_consignacion_callback, pattern=r"^mover_cons:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="mover_consignacion_conversation",
    persistent=False,
)


# ========== PAGAR CONSIGNACIONES ==========

@admin_only
async def pagar_consignacion_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para pagar consignaciones."""
    keys_to_remove = [
        "pagar_cons_vendedor_id", "pagar_cons_moneda_deuda", "pagar_cons_monto", "pagar_cons_moneda_pago", "pagar_cons_caja_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    vendedores = VendedorService.listar()
    if not vendedores:
        await reply_text(update, "❌ No hay vendedores disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "💰 <b>Pagar Consignación</b>\n\nSelecciona el vendedor:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {vend['name']}",
                callback_data=f"pagar_cons:vend:{vend['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pagar_cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return PAGAR_CONS_SEL_VENDEDOR


async def pagar_consignacion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del flujo de pago de consignaciones."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("pagar_cons:vend:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["pagar_cons_vendedor_id"] = vendedor_id
        
        # Obtener deudas del vendedor
        try:
            vendedor = VendedorService.obtener_por_id(vendedor_id)
            with get_db_connection() as conn:
                from database.repositories import DeudaRepository
                deudas = DeudaRepository.obtener_pendientes(conn)
            
            # Filtrar deudas del vendedor (POR_COBRAR)
            deudas_vendedor = [
                d for d in deudas 
                if d['actor_id'] == vendedor['name'] and d['tipo'] == 'POR_COBRAR'
            ]
            
            if not deudas_vendedor:
                await reply_text(update, f"❌ El vendedor {vendedor['name']} no tiene deudas POR_COBRAR.")
                return ConversationHandler.END
            
            text = f"👤 <b>Vendedor: {vendedor['name']}</b>\n\n<b>Deudas:</b>\n"
            for deuda in deudas_vendedor:
                text += f"• {deuda['monto_pendiente']:.2f} {deuda['moneda'].upper()}\n"
            text += "\nSelecciona la <b>moneda de la deuda</b> a pagar:"
            
            keyboard: List[List[InlineKeyboardButton]] = []
            monedas_deuda = list(set([d['moneda'] for d in deudas_vendedor]))
            for moneda in monedas_deuda:
                deuda_monto = next((d['monto_pendiente'] for d in deudas_vendedor if d['moneda'] == moneda), 0)
                keyboard.append([
                    InlineKeyboardButton(
                        f"{moneda.upper()} ({deuda_monto:.2f})",
                        callback_data=f"pagar_cons:moneda_deuda:{moneda}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="pagar_cons:back")])
            kb = InlineKeyboardMarkup(keyboard)
            await reply_html(update, text, reply_markup=kb)
            return PAGAR_CONS_SEL_MONEDA
        except Exception as e:
            logger.error(f"Error obteniendo deudas: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return ConversationHandler.END
    
    if data.startswith("pagar_cons:moneda_deuda:"):
        moneda_deuda = data.split(":")[-1]
        context.user_data["pagar_cons_moneda_deuda"] = moneda_deuda
        
        vendedor_id = context.user_data.get("pagar_cons_vendedor_id")
        if not vendedor_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        with get_db_connection() as conn:
            from database.repositories import DeudaRepository
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor['name'], moneda_deuda, 'POR_COBRAR')
        
        await reply_html(
            update,
            f"💰 <b>Pagar Consignación</b>\n\n"
            f"Vendedor: <code>{vendedor['name']}</code>\n"
            f"Deuda: <b>{deuda['monto_pendiente']:.2f} {moneda_deuda.upper()}</b>\n\n"
            f"Envía el <b>monto</b> a pagar:"
        )
        return PAGAR_CONS_MONTO
    
    if data.startswith("pagar_cons:moneda_pago:"):
        moneda_pago = data.split(":")[-1]
        context.user_data["pagar_cons_moneda_pago"] = moneda_pago
        
        vendedor_id = context.user_data.get("pagar_cons_vendedor_id")
        monto = context.user_data.get("pagar_cons_monto")
        
        if not vendedor_id or not monto:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        moneda_deuda = context.user_data.get("pagar_cons_moneda_deuda")
        
        text = f"💰 <b>Pagar Consignación</b>\n\n"
        text += f"Vendedor: <code>{vendedor['name']}</code>\n"
        text += f"Monto: <b>{monto} {moneda_pago.upper()}</b>\n\n"
        text += f"Selecciona la <b>caja</b> donde se recibe el pago:"
        
        cajas = CajaService.listar()
        if not cajas:
            await reply_text(update, "❌ No hay cajas disponibles. Crea una primero.")
            return ConversationHandler.END
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for caja in cajas:
            keyboard.append([
                InlineKeyboardButton(
                    caja['nombre'].upper(),
                    callback_data=f"pagar_cons:caja:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="pagar_cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return PAGAR_CONS_SEL_CAJA
    
    if data.startswith("pagar_cons:caja:"):
        caja_id = int(data.split(":")[-1])
        context.user_data["pagar_cons_caja_id"] = caja_id
        
        vendedor_id = context.user_data.get("pagar_cons_vendedor_id")
        moneda_deuda = context.user_data.get("pagar_cons_moneda_deuda")
        monto = context.user_data.get("pagar_cons_monto")
        moneda_pago = context.user_data.get("pagar_cons_moneda_pago")
        user_id = update.effective_user.id
        
        if not all([vendedor_id, moneda_deuda, monto, moneda_pago, caja_id]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        try:
            # Realizar el pago
            resultado = pagar_consignacion(
                vendedor_id, moneda_deuda, monto, moneda_pago, caja_id, user_id
            )
            
            caja_obj = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja_obj['nombre'] if caja_obj else str(caja_id)
            
            vendedor = VendedorService.obtener_por_id(vendedor_id)
            
            text = f"✅ <b>Pago Registrado</b>\n\n"
            text += f"Vendedor: <code>{vendedor['name']}</code>\n"
            text += f"Monto recibido: <b>{monto} {moneda_pago.upper()}</b>\n"
            text += f"Caja: <code>{caja_nombre.upper()}</code>\n"
            text += f"Deuda reducida: <b>{resultado['monto_descontado']:.2f} {moneda_deuda.upper()}</b>\n"
            if resultado['deuda_restante'] > 0:
                text += f"Deuda restante: <b>{resultado['deuda_restante']:.2f} {moneda_deuda.upper()}</b>"
            else:
                text += f"✅ <b>Deuda completamente pagada</b>"
            
            await reply_html(update, text)
            
            # Limpiar datos
            keys_to_remove = [
                "pagar_cons_vendedor_id", "pagar_cons_moneda_deuda", "pagar_cons_monto",
                "pagar_cons_moneda_pago", "pagar_cons_caja_id"
            ]
            for key in keys_to_remove:
                context.user_data.pop(key, None)
            
            return ConversationHandler.END
        except ValueError as e:
            await reply_text(update, f"❌ {str(e)}")
            return PAGAR_CONS_SEL_CAJA
        except Exception as e:
            logger.error(f"Error registrando pago: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
            return PAGAR_CONS_SEL_CAJA
    
    if data == "pagar_cons:back":
        return await pagar_consignacion_entry(update, context)
    
    if data == "pagar_cons:cancel":
        keys_to_remove = [
            "pagar_cons_vendedor_id", "pagar_cons_moneda_deuda", "pagar_cons_monto",
            "pagar_cons_moneda_pago", "pagar_cons_caja_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operación cancelada.")
        return ConversationHandler.END
    
    return PAGAR_CONS_SEL_VENDEDOR


async def pagar_consignacion_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el monto a pagar."""
    if not update.message:
        return PAGAR_CONS_MONTO
    
    try:
        monto = float((update.message.text or "").strip())
        if monto <= 0:
            await reply_text(update, "❌ El monto debe ser mayor a 0.")
            return PAGAR_CONS_MONTO
        
        context.user_data["pagar_cons_monto"] = monto
        
        vendedor_id = context.user_data.get("pagar_cons_vendedor_id")
        moneda_deuda = context.user_data.get("pagar_cons_moneda_deuda")
        
        if not vendedor_id or not moneda_deuda:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        with get_db_connection() as conn:
            from database.repositories import DeudaRepository
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor['name'], moneda_deuda, 'POR_COBRAR')
        
        text = f"✅ Monto: <b>{monto}</b>\n\n"
        text += f"Vendedor: <code>{vendedor['name']}</code>\n"
        text += f"Deuda: <b>{deuda['monto_pendiente']:.2f} {moneda_deuda.upper()}</b>\n\n"
        text += f"Selecciona la <b>moneda del pago</b>:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"pagar_cons:moneda_pago:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="pagar_cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return PAGAR_CONS_SEL_CAJA
    except ValueError:
        await reply_text(update, "❌ El monto debe ser un número válido.")
        return PAGAR_CONS_MONTO


pagar_consignacion_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("pagar_consignacion", pagar_consignacion_entry),
    ],
    states={
        PAGAR_CONS_SEL_VENDEDOR: [
            CallbackQueryHandler(pagar_consignacion_callback, pattern=r"^pagar_cons:(vend:|cancel)"),
        ],
        PAGAR_CONS_SEL_MONEDA: [
            CallbackQueryHandler(pagar_consignacion_callback, pattern=r"^pagar_cons:(moneda_deuda:|back)"),
        ],
        PAGAR_CONS_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pagar_consignacion_monto_receive),
            CallbackQueryHandler(pagar_consignacion_callback, pattern=r"^pagar_cons:.*"),
        ],
        PAGAR_CONS_SEL_CAJA: [
            CallbackQueryHandler(pagar_consignacion_callback, pattern=r"^pagar_cons:(moneda_pago:|caja:|back)"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="pagar_consignacion_conversation",
    persistent=False,
)

