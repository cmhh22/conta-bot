"""
Handlers para operaciones de logistics (mover productos entre containeres y warehousees).
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
from services.logistics_service import (
    agregar_producto_a_container,
    obtener_productos_de_container,
    mover_producto_container_a_warehouse,
    mover_producto_warehouse_a_warehouse,
    ajustar_inventario_warehouse,
    obtener_inventario_warehouse,
    obtener_resumen_logistics,
    consignar_desde_warehouse,
    mover_consignment_vendedor,
    pagar_consignment,
)
from services.containeres_service import ContainerService
from services.warehousees_service import listar as listar_warehousees, obtener_por_id
from services.vendedores_service import VendedorService
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService
from database.connection import get_db_connection
from database.repositories import ProductoRepository

logger = logging.getLogger(__name__)

# Estados para mover productos (container → warehouse)
MOVER_MENU, MOVER_SEL_CONTENEDOR, MOVER_SEL_ALMACEN, MOVER_SEL_PRODUCTO, MOVER_CANTIDAD = range(5)

# Estados para agregar productos a containeres
AGREGAR_SEL_CONTENEDOR, AGREGAR_SEL_PRODUCTO, AGREGAR_CANTIDAD = range(5, 8)

# Estados para mover entre warehousees
MOVER_ALM_SEL_ORIGEN, MOVER_ALM_SEL_DESTINO, MOVER_ALM_SEL_PRODUCTO, MOVER_ALM_CANTIDAD = range(8, 12)

# Estados para consignar desde warehousees
CONSIGNAR_SEL_ALMACEN, CONSIGNAR_SEL_PRODUCTO, CONSIGNAR_SEL_VENDEDOR, CONSIGNAR_PRECIO, CONSIGNAR_MONEDA, CONSIGNAR_CANTIDAD = range(12, 18)

# Estados para mover consignaciones entre vendedores
MOVER_CONS_SEL_ORIGEN, MOVER_CONS_SEL_PRODUCTO, MOVER_CONS_SEL_DESTINO, MOVER_CONS_CANTIDAD = range(18, 22)

# Estados para pagar consignaciones
PAGAR_CONS_SEL_VENDEDOR, PAGAR_CONS_SEL_MONEDA, PAGAR_CONS_MONTO, PAGAR_CONS_SEL_CAJA = range(22, 26)


@admin_only
async def productos_container_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show los productos de un container."""
    if not context.args or len(context.args) < 1:
        await reply_text(
            update,
            "📦 <b>Productos de Container</b>\n\n"
            "Uso: <code>/productos_container [ID]</code>\n"
            "Ejemplo: <code>/productos_container 1</code>"
        )
        return
    
    try:
        container_id = int(context.args[0])
        productos = obtener_productos_de_container(container_id)
        
        container = ContainerService.obtener_por_id(container_id)
        if not container:
            await reply_text(update, f"❌ No existe un container con ID {container_id}")
            return
        
        if not productos:
            await reply_html(
                update,
                f"📦 <b>Container: {container['nombre']}</b>\n\n"
                f"Este container no tiene productos recordeds."
            )
            return
        
        text = f"📦 <b>Productos en Container: {container['nombre']}</b>\n\n"
        for prod in productos:
            text += (
                f"• <b>{prod['producto_nombre']}</b> ({prod['producto_codigo']})\n"
                f"  Cantidad: {prod['cantidad']}\n\n"
            )
        
        await reply_html(update, text)
    except ValueError:
        await reply_text(update, "❌ El ID debe ser un numero valid.")
    except Exception as e:
        logger.error(f"Error obteniendo productos del container: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def inventario_warehouse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show el inventario de un warehouse."""
    from services.warehousees_service import obtener_por_id
    
    # Si no hay argumentos, mostrar lista de warehousees para selectr
    if not context.args or len(context.args) < 1:
        warehousees = listar_warehousees()
        if not warehousees:
            await reply_text(update, "❌ No warehousees disponibles. Crea uno primero.")
            return
        
        text = "🏢 <b>Select a warehouse para ver su inventario:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in warehousees:
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
        warehouse_id = int(context.args[0])
        inventario = obtener_inventario_warehouse(warehouse_id)
        
        warehouse = obtener_por_id(warehouse_id)
        if not warehouse:
            await reply_text(update, f"❌ No existe un warehouse con ID {warehouse_id}")
            return
        
        if not inventario:
            await reply_html(
                update,
                f"🏢 <b>Warehouse: {warehouse['nombre']}</b>\n\n"
                f"Este warehouse no tiene productos en inventario."
            )
            return
        
        text = f"🏢 <b>Inventario: {warehouse['nombre']}</b>\n\n"
        for item in inventario:
            text += (
                f"• <b>{item['producto_nombre']}</b> ({item['producto_codigo']})\n"
                f"  Cantidad: {item['cantidad']}\n\n"
            )
        
        await reply_html(update, text)
    except ValueError:
        await reply_text(update, "❌ El ID debe ser un numero valid.")
    except Exception as e:
        logger.error(f"Error obteniendo inventario del warehouse: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def inventario_warehouse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle el callback para mostrar inventario de warehouse."""
    from services.warehousees_service import obtener_por_id
    
    q = update.callback_query
    if q:
        await q.answer()
    
    if not q or not q.data:
        return
    
    if q.data.startswith("inv_alm:"):
        try:
            warehouse_id = int(q.data.split(":")[-1])
            inventario = obtener_inventario_warehouse(warehouse_id)
            
            warehouse = obtener_por_id(warehouse_id)
            if not warehouse:
                await reply_text(update, f"❌ No existe un warehouse con ID {warehouse_id}")
                return
            
            if not inventario:
                text = f"📦 <b>Inventario: {warehouse['nombre']}</b>\n\nEste warehouse no tiene productos en inventario."
            else:
                text = f"📦 <b>Inventario: {warehouse['nombre']}</b>\n\n"
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
            await reply_text(update, "❌ El ID debe ser un numero valid.")
        except Exception as e:
            logger.error(f"Error obteniendo inventario del warehouse: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")


@admin_only
async def mover_producto_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover productos de container a warehouse."""
    # Limpiar datos previos
    keys_to_remove = [
        "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    # Listar containeres
    containeres = ContainerService.listar()
    if not containeres:
        await reply_text(update, "❌ No containeres disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Mover Producto: Container → Warehouse</b>\n\nSelect the container:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in containeres:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {cont['nombre']}",
                callback_data=f"log:cont:{cont['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="log:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_SEL_CONTENEDOR


async def mover_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de mover productos."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("log:cont:"):
        container_id = int(data.split(":")[-1])
        context.user_data["log_cont_id"] = container_id
        
        # Obtener productos del container
        try:
            productos = obtener_productos_de_container(container_id)
            if not productos:
                await reply_text(update, "❌ Este container no tiene productos.")
                return ConversationHandler.END
            
            container = ContainerService.obtener_por_id(container_id)
            text = f"📦 <b>Container: {container['nombre']}</b>\n\nSelect the producto:"
            keyboard: List[List[InlineKeyboardButton]] = []
            for prod in productos:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prod['producto_nombre']} ({prod['cantidad']})",
                        callback_data=f"log:prod:{prod['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="log:back")])
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
        
        # Listar warehousees
        warehousees = listar_warehousees()
        if not warehousees:
            await reply_text(update, "❌ No warehousees disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        text = "🏢 <b>Select the warehouse destination:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in warehousees:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {alm['nombre']}",
                    callback_data=f"log:alm:{alm['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="log:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_SEL_ALMACEN
    
    if data.startswith("log:alm:"):
        warehouse_id = int(data.split(":")[-1])
        context.user_data["log_alm_id"] = warehouse_id
        
        cont_id = context.user_data.get("log_cont_id")
        prod_codigo = context.user_data.get("log_prod_codigo")
        
        if not cont_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        productos = obtener_productos_de_container(cont_id)
        producto = next((p for p in productos if p["producto_codigo"] == prod_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto not found en el container.")
            return ConversationHandler.END
        
        container = ContainerService.obtener_por_id(cont_id)
        from services.warehousees_service import obtener_por_id
        warehouse = obtener_por_id(warehouse_id)
        
        await reply_html(
            update,
            f"📦 <b>Mover Producto</b>\n\n"
            f"Container: <code>{container['nombre']}</code>\n"
            f"Producto: <code>{producto['producto_nombre']}</code>\n"
            f"Warehouse: <code>{warehouse['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Send la <b>cantidad</b> a mover:"
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
        await reply_text(update, "✅ Operation canceled.")
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
        resultado = mover_producto_container_a_warehouse(
            cont_id, alm_id, prod_codigo, cantidad, user_id
        )
        
        container = ContainerService.obtener_por_id(cont_id)
        warehouse = obtener_por_id(alm_id)
        
        await reply_html(
            update,
            f"✅ <b>Producto Movido</b>\n\n"
            f"De: <code>{container['nombre']}</code>\n"
            f"A: <code>{warehouse['nombre']}</code>\n"
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
    """Cancela la operation de mover producto."""
    keys_to_remove = [
        "log_cont_id", "log_alm_id", "log_prod_codigo", "log_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    await reply_text(update, "✅ Operation canceled.")
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
async def agregar_producto_container_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para agregar productos a containeres."""
    keys_to_remove = ["agr_cont_id", "agr_prod_codigo", "agr_cantidad"]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    containeres = ContainerService.listar()
    if not containeres:
        await reply_text(update, "❌ No containeres disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Agregar Producto a Container</b>\n\nSelect the container:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in containeres:
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {cont['nombre']}",
                callback_data=f"agr:cont:{cont['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="agr:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return AGREGAR_SEL_CONTENEDOR


async def agregar_producto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de agregar productos."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("agr:cont:"):
        container_id = int(data.split(":")[-1])
        context.user_data["agr_cont_id"] = container_id
        
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_todos(conn)
        
        if not productos:
            await reply_text(update, "❌ No productos disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        container = ContainerService.obtener_por_id(container_id)
        text = f"📦 <b>Container: {container['nombre']}</b>\n\nSelect the producto:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for prod in productos[:20]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{prod['nombre']} ({prod['codigo']})",
                    callback_data=f"agr:prod:{prod['codigo']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="agr:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return AGREGAR_SEL_PRODUCTO
    
    if data.startswith("agr:prod:"):
        producto_codigo = data.split(":")[-1]
        context.user_data["agr_prod_codigo"] = producto_codigo
        
        cont_id = context.user_data.get("agr_cont_id")
        container = ContainerService.obtener_por_id(cont_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Agregar Producto</b>\n\n"
            f"Container: <code>{container['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({producto_codigo})\n\n"
            f"Send la <b>cantidad</b> a agregar:"
        )
        return AGREGAR_CANTIDAD
    
    if data == "agr:back":
        return await agregar_producto_container_entry(update, context)
    
    if data == "agr:cancel":
        keys_to_remove = ["agr_cont_id", "agr_prod_codigo", "agr_cantidad"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation canceled.")
        return ConversationHandler.END
    
    return AGREGAR_SEL_CONTENEDOR


async def agregar_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y agrega el producto al container."""
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
        
        resultado = agregar_producto_a_container(cont_id, prod_codigo, cantidad)
        
        container = ContainerService.obtener_por_id(cont_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"✅ <b>Producto Agregado</b>\n\n"
            f"Container: <code>{container['nombre']}</code>\n"
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
    entry_points=[CommandHandler("agregar_producto_container", agregar_producto_container_entry)],
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


# ========== LOGISTICS REPORTS ==========

@admin_only
async def resumen_logistics_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show un resumen general de la logistics."""
    try:
        resumen = obtener_resumen_logistics()
        
        text = "📊 <b>Logistics Summary</b>\n\n"
        text += f"📦 <b>Containeres:</b>\n"
        text += f"  • Total: {resumen['total_containeres']}\n"
        text += f"  • Productos unicos: {resumen['total_productos_containeres']}\n\n"
        text += f"🏢 <b>Warehousees:</b>\n"
        text += f"  • Total: {resumen['total_warehousees']}\n"
        text += f"  • Productos unicos: {resumen['total_productos_warehousees']}\n"
        
        await reply_html(update, text)
    except Exception as e:
        logger.error(f"Error obteniendo resumen: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")


# ========== MOVER PRODUCTOS ENTRE ALMACENES ==========

@admin_only
async def mover_warehouse_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover productos entre warehousees."""
    keys_to_remove = [
        "mover_alm_source_id", "mover_alm_destination_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    warehousees = listar_warehousees()
    if len(warehousees) < 2:
        await reply_text(update, "❌ Necesitas al menos 2 warehousees para mover productos entre ellos.")
        return ConversationHandler.END
    
    text = "🏢 <b>Mover Producto: Warehouse → Warehouse</b>\n\nSelect the warehouse <b>source</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in warehousees:
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {alm['nombre']}",
                callback_data=f"mover_alm:source:{alm['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="mover_alm:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_ALM_SEL_ORIGEN


async def mover_warehouse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de mover productos entre warehousees."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("mover_alm:source:"):
        warehouse_id = int(data.split(":")[-1])
        context.user_data["mover_alm_source_id"] = warehouse_id
        
        # Listar warehousees destination (excluyendo el source)
        warehousees = listar_warehousees()
        warehousees_destination = [a for a in warehousees if a["id"] != warehouse_id]
        
        if not warehousees_destination:
            await reply_text(update, "❌ No otros warehousees disponibles como destination.")
            return ConversationHandler.END
        
        warehouse_source = obtener_por_id(warehouse_id)
        text = f"🏢 <b>Origen: {warehouse_source['nombre']}</b>\n\nSelect the warehouse <b>destination</b>:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for alm in warehousees_destination:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {alm['nombre']}",
                    callback_data=f"mover_alm:destination:{alm['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="mover_alm:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_ALM_SEL_DESTINO
    
    if data.startswith("mover_alm:destination:"):
        warehouse_id = int(data.split(":")[-1])
        context.user_data["mover_alm_destination_id"] = warehouse_id
        
        source_id = context.user_data.get("mover_alm_source_id")
        if not source_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener productos del warehouse source
        try:
            inventario = obtener_inventario_warehouse(source_id)
            if not inventario:
                await reply_text(update, "❌ El warehouse source no tiene productos en inventario.")
                return ConversationHandler.END
            
            warehouse_source = obtener_por_id(source_id)
            warehouse_destination = obtener_por_id(warehouse_id)
            
            text = (
                f"🏢 <b>Mover Producto</b>\n\n"
                f"Origen: <code>{warehouse_source['nombre']}</code>\n"
                f"Destino: <code>{warehouse_destination['nombre']}</code>\n\n"
                f"Select the producto:"
            )
            keyboard: List[List[InlineKeyboardButton]] = []
            for item in inventario:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{item['producto_nombre']} ({item['cantidad']})",
                        callback_data=f"mover_alm:prod:{item['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="mover_alm:back")])
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
        
        source_id = context.user_data.get("mover_alm_source_id")
        destination_id = context.user_data.get("mover_alm_destination_id")
        
        if not source_id or not destination_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        inventario = obtener_inventario_warehouse(source_id)
        producto = next((p for p in inventario if p["producto_codigo"] == producto_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto not found en el warehouse source.")
            return ConversationHandler.END
        
        warehouse_source = obtener_por_id(source_id)
        warehouse_destination = obtener_por_id(destination_id)
        
        with get_db_connection() as conn:
            prod = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        
        await reply_html(
            update,
            f"🏢 <b>Mover Producto</b>\n\n"
            f"Origen: <code>{warehouse_source['nombre']}</code>\n"
            f"Destino: <code>{warehouse_destination['nombre']}</code>\n"
            f"Producto: <code>{prod['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Send la <b>cantidad</b> a mover:"
        )
        return MOVER_ALM_CANTIDAD
    
    if data == "mover_alm:back":
        return await mover_warehouse_entry(update, context)
    
    if data == "mover_alm:cancel":
        keys_to_remove = [
            "mover_alm_source_id", "mover_alm_destination_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation canceled.")
        return ConversationHandler.END
    
    return MOVER_ALM_SEL_ORIGEN


async def mover_warehouse_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza el movimiento entre warehousees."""
    if not update.message:
        return MOVER_ALM_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return MOVER_ALM_CANTIDAD
        
        source_id = context.user_data.get("mover_alm_source_id")
        destination_id = context.user_data.get("mover_alm_destination_id")
        prod_codigo = context.user_data.get("mover_alm_prod_codigo")
        user_id = update.effective_user.id
        
        if not all([source_id, destination_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar el movimiento
        resultado = mover_producto_warehouse_a_warehouse(
            source_id, destination_id, prod_codigo, cantidad, user_id
        )
        
        warehouse_source = obtener_por_id(source_id)
        warehouse_destination = obtener_por_id(destination_id)
        
        await reply_html(
            update,
            f"✅ <b>Producto Movido</b>\n\n"
            f"De: <code>{warehouse_source['nombre']}</code>\n"
            f"A: <code>{warehouse_destination['nombre']}</code>\n"
            f"Cantidad: <b>{cantidad}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "mover_alm_source_id", "mover_alm_destination_id", "mover_alm_prod_codigo", "mover_alm_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return MOVER_ALM_CANTIDAD
    except Exception as e:
        logger.error(f"Error moviendo producto entre warehousees: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return MOVER_ALM_CANTIDAD


mover_warehouse_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("mover_warehouse", mover_warehouse_entry),
    ],
    states={
        MOVER_ALM_SEL_ORIGEN: [
            CallbackQueryHandler(mover_warehouse_callback, pattern=r"^mover_alm:(source:|cancel)"),
        ],
        MOVER_ALM_SEL_DESTINO: [
            CallbackQueryHandler(mover_warehouse_callback, pattern=r"^mover_alm:(destination:|back)"),
        ],
        MOVER_ALM_SEL_PRODUCTO: [
            CallbackQueryHandler(mover_warehouse_callback, pattern=r"^mover_alm:(prod:|back)"),
        ],
        MOVER_ALM_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mover_warehouse_cantidad_receive),
            CallbackQueryHandler(mover_warehouse_callback, pattern=r"^mover_alm:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="mover_warehouse_conversation",
    persistent=False,
)


# ========== CONSIGNAR DESDE ALMACENES ==========

@admin_only
async def consignar_warehouse_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para consignar productos desde warehousees."""
    keys_to_remove = [
        "cons_alm_id", "cons_prod_codigo", "cons_vendedor_id", "cons_precio", "cons_moneda", "cons_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    warehousees = listar_warehousees()
    if not warehousees:
        await reply_text(update, "❌ No warehousees disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "📦 <b>Consignar Producto desde Warehouse</b>\n\nSelect the warehouse:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for alm in warehousees:
        keyboard.append([
            InlineKeyboardButton(
                f"🏢 {alm['nombre']}",
                callback_data=f"cons:alm:{alm['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return CONSIGNAR_SEL_ALMACEN


async def consignar_warehouse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de consignment."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("cons:alm:"):
        warehouse_id = int(data.split(":")[-1])
        context.user_data["cons_alm_id"] = warehouse_id
        
        # Obtener productos del warehouse
        try:
            inventario = obtener_inventario_warehouse(warehouse_id)
            if not inventario:
                await reply_text(update, "❌ Este warehouse no tiene productos en inventario.")
                return ConversationHandler.END
            
            warehouse = obtener_por_id(warehouse_id)
            text = f"🏢 <b>Warehouse: {warehouse['nombre']}</b>\n\nSelect the producto:"
            keyboard: List[List[InlineKeyboardButton]] = []
            for item in inventario:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{item['producto_nombre']} ({item['cantidad']})",
                        callback_data=f"cons:prod:{item['producto_codigo']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cons:back")])
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
            await reply_text(update, "❌ No vendedores disponibles. Crea uno primero.")
            return ConversationHandler.END
        
        text = "👤 <b>Select the vendedor:</b>"
        keyboard: List[List[InlineKeyboardButton]] = []
        for vend in vendedores:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {vend['name']}",
                    callback_data=f"cons:vend:{vend['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return CONSIGNAR_SEL_VENDEDOR
    
    if data.startswith("cons:vend:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["cons_vendedor_id"] = vendedor_id
        
        warehouse_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        
        if not warehouse_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        warehouse = obtener_por_id(warehouse_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Warehouse: <code>{warehouse['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({prod_codigo})\n"
            f"Seller: <code>{vendedor['name']}</code>\n\n"
            f"Send el <b>precio unitario</b> de venta:"
        )
        return CONSIGNAR_PRECIO
    
    if data == "cons:back":
        return await consignar_warehouse_entry(update, context)
    
    if data == "cons:cancel":
        keys_to_remove = [
            "cons_alm_id", "cons_prod_codigo", "cons_vendedor_id", "cons_precio", "cons_moneda", "cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation canceled.")
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
        text = f"✅ Precio: <b>{precio}</b>\n\nSelect the <b>moneda</b>:"
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"cons:moneda:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return CONSIGNAR_MONEDA
    except ValueError:
        await reply_text(update, "❌ El precio debe ser un numero valid.")
        return CONSIGNAR_PRECIO


async def consignar_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle la selection de moneda."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("cons:moneda:"):
        moneda = data.split(":")[-1]
        context.user_data["cons_moneda"] = moneda
        
        warehouse_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        
        if not warehouse_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Obtener cantidad disponible
        inventario = obtener_inventario_warehouse(warehouse_id)
        producto = next((p for p in inventario if p["producto_codigo"] == prod_codigo), None)
        
        if not producto:
            await reply_text(update, "❌ Producto not found en el warehouse.")
            return ConversationHandler.END
        
        warehouse = obtener_por_id(warehouse_id)
        precio = context.user_data.get("cons_precio")
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Warehouse: <code>{warehouse['nombre']}</code>\n"
            f"Producto: <code>{producto['producto_nombre']}</code>\n"
            f"Precio: <b>{precio} {moneda.upper()}</b>\n\n"
            f"Cantidad disponible: <b>{producto['cantidad']}</b>\n\n"
            f"Send la <b>cantidad</b> a consignar:"
        )
        return CONSIGNAR_CANTIDAD
    
    if data == "cons:back":
        # Back a pedir precio
        warehouse_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        vendedor_id = context.user_data.get("cons_vendedor_id")
        
        if not all([warehouse_id, prod_codigo, vendedor_id]):
            return await consignar_warehouse_entry(update, context)
        
        warehouse = obtener_por_id(warehouse_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        await reply_html(
            update,
            f"📦 <b>Consignar Producto</b>\n\n"
            f"Warehouse: <code>{warehouse['nombre']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({prod_codigo})\n"
            f"Seller: <code>{vendedor['name']}</code>\n\n"
            f"Send el <b>precio unitario</b> de venta:"
        )
        return CONSIGNAR_PRECIO
    
    return CONSIGNAR_MONEDA


async def consignar_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza la consignment."""
    if not update.message:
        return CONSIGNAR_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return CONSIGNAR_CANTIDAD
        
        warehouse_id = context.user_data.get("cons_alm_id")
        prod_codigo = context.user_data.get("cons_prod_codigo")
        vendedor_id = context.user_data.get("cons_vendedor_id")
        precio = context.user_data.get("cons_precio")
        moneda = context.user_data.get("cons_moneda")
        user_id = update.effective_user.id
        
        if not all([warehouse_id, prod_codigo, vendedor_id, precio, moneda]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar la consignment
        resultado = consignar_desde_warehouse(
            warehouse_id, prod_codigo, cantidad, vendedor_id, precio, moneda, user_id
        )
        
        warehouse = obtener_por_id(warehouse_id)
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        
        await reply_html(
            update,
            f"✅ <b>Consignment Completed</b>\n\n"
            f"Warehouse: <code>{warehouse['nombre']}</code>\n"
            f"Producto: <code>{prod_codigo}</code>\n"
            f"Seller: <code>{vendedor['name']}</code>\n"
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


consignar_warehouse_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("consignar_warehouse", consignar_warehouse_entry),
    ],
    states={
        CONSIGNAR_SEL_ALMACEN: [
            CallbackQueryHandler(consignar_warehouse_callback, pattern=r"^cons:(alm:|cancel)"),
        ],
        CONSIGNAR_SEL_PRODUCTO: [
            CallbackQueryHandler(consignar_warehouse_callback, pattern=r"^cons:(prod:|back)"),
        ],
        CONSIGNAR_SEL_VENDEDOR: [
            CallbackQueryHandler(consignar_warehouse_callback, pattern=r"^cons:(vend:|back)"),
        ],
        CONSIGNAR_PRECIO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, consignar_precio_receive),
            CallbackQueryHandler(consignar_warehouse_callback, pattern=r"^cons:.*"),
        ],
        CONSIGNAR_MONEDA: [
            CallbackQueryHandler(consignar_moneda_callback, pattern=r"^cons:(moneda:|back)"),
        ],
        CONSIGNAR_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, consignar_cantidad_receive),
            CallbackQueryHandler(consignar_warehouse_callback, pattern=r"^cons:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="consignar_warehouse_conversation",
    persistent=False,
)


# ========== MOVER CONSIGNACIONES ENTRE VENDEDORES ==========

@admin_only
async def mover_consignment_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para mover consignaciones entre vendedores."""
    keys_to_remove = [
        "mover_cons_source_id", "mover_cons_destination_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    vendedores = VendedorService.listar()
    if len(vendedores) < 2:
        await reply_text(update, "❌ Necesitas al menos 2 vendedores para mover consignaciones.")
        return ConversationHandler.END
    
    text = "🔄 <b>Move Consignment: Seller → Seller</b>\n\nSelect the vendedor <b>source</b>:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {vend['name']}",
                callback_data=f"mover_cons:source:{vend['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="mover_cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return MOVER_CONS_SEL_ORIGEN


async def mover_consignment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de mover consignaciones."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("mover_cons:source:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["mover_cons_source_id"] = vendedor_id
        
        # Obtener consignaciones del vendedor source
        try:
            vendedor = VendedorService.obtener_por_id(vendedor_id)
            with get_db_connection() as conn:
                from database.repositories import ConsignmentRepository
                consignaciones = ConsignmentRepository.obtener_por_vendedor(conn, vendedor['name'])
            
            if not consignaciones:
                await reply_text(update, "❌ This seller has no consigned products.")
                return ConversationHandler.END
            
            text = f"👤 <b>Source Seller: {vendedor['name']}</b>\n\nSelect the product:"
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
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="mover_cons:back")])
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
        
        source_id = context.user_data.get("mover_cons_source_id")
        if not source_id:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Listar vendedores destination (excluyendo el source)
        vendedores = VendedorService.listar()
        vendedores_destination = [v for v in vendedores if v["id"] != source_id]
        
        if not vendedores_destination:
            await reply_text(update, "❌ No otros vendedores disponibles como destination.")
            return ConversationHandler.END
        
        vendedor_source = VendedorService.obtener_por_id(source_id)
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
            from database.repositories import ConsignmentRepository
            consignment = ConsignmentRepository.obtener_por_vendedor_codigo(
                conn, vendedor_source['name'], producto_codigo
            )
        
        text = (
            f"🔄 <b>Move Consignment</b>\n\n"
            f"Origen: <code>{vendedor_source['name']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code> ({producto_codigo})\n"
            f"Stock disponible: <b>{consignment['stock']}</b>\n\n"
            f"Select the vendedor <b>destination</b>:"
        )
        keyboard: List[List[InlineKeyboardButton]] = []
        for vend in vendedores_destination:
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {vend['name']}",
                    callback_data=f"mover_cons:destination:{vend['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="mover_cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return MOVER_CONS_SEL_DESTINO
    
    if data.startswith("mover_cons:destination:"):
        vendedor_id = int(data.split(":")[-1])
        context.user_data["mover_cons_destination_id"] = vendedor_id
        
        source_id = context.user_data.get("mover_cons_source_id")
        prod_codigo = context.user_data.get("mover_cons_prod_codigo")
        
        if not source_id or not prod_codigo:
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        vendedor_source = VendedorService.obtener_por_id(source_id)
        vendedor_destination = VendedorService.obtener_por_id(vendedor_id)
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
            from database.repositories import ConsignmentRepository
            consignment = ConsignmentRepository.obtener_por_vendedor_codigo(
                conn, vendedor_source['name'], prod_codigo
            )
        
        await reply_html(
            update,
            f"🔄 <b>Move Consignment</b>\n\n"
            f"De: <code>{vendedor_source['name']}</code>\n"
            f"A: <code>{vendedor_destination['name']}</code>\n"
            f"Producto: <code>{producto['nombre']}</code>\n\n"
            f"Cantidad disponible: <b>{consignment['stock']}</b>\n\n"
            f"Send la <b>cantidad</b> a mover:"
        )
        return MOVER_CONS_CANTIDAD
    
    if data == "mover_cons:back":
        return await mover_consignment_entry(update, context)
    
    if data == "mover_cons:cancel":
        keys_to_remove = [
            "mover_cons_source_id", "mover_cons_destination_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation canceled.")
        return ConversationHandler.END
    
    return MOVER_CONS_SEL_ORIGEN


async def mover_consignment_cantidad_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la cantidad y realiza el movimiento de consignment."""
    if not update.message:
        return MOVER_CONS_CANTIDAD
    
    try:
        cantidad = float((update.message.text or "").strip())
        if cantidad <= 0:
            await reply_text(update, "❌ La cantidad debe ser mayor a 0.")
            return MOVER_CONS_CANTIDAD
        
        source_id = context.user_data.get("mover_cons_source_id")
        destination_id = context.user_data.get("mover_cons_destination_id")
        prod_codigo = context.user_data.get("mover_cons_prod_codigo")
        user_id = update.effective_user.id
        
        if not all([source_id, destination_id, prod_codigo]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return ConversationHandler.END
        
        # Realizar el movimiento
        resultado = mover_consignment_vendedor(
            source_id, destination_id, prod_codigo, cantidad, user_id
        )
        
        vendedor_source = VendedorService.obtener_por_id(source_id)
        vendedor_destination = VendedorService.obtener_por_id(destination_id)
        
        await reply_html(
            update,
            f"✅ <b>Consignment Moved</b>\n\n"
            f"De: <code>{vendedor_source['name']}</code>\n"
            f"A: <code>{vendedor_destination['name']}</code>\n"
            f"Producto: <code>{prod_codigo}</code>\n"
            f"Cantidad: <b>{cantidad}</b>\n\n"
            f"💰 Deuda transferida: <b>{resultado['monto_movimiento']:.2f} {resultado['moneda'].upper()}</b>"
        )
        
        # Limpiar datos
        keys_to_remove = [
            "mover_cons_source_id", "mover_cons_destination_id", "mover_cons_prod_codigo", "mover_cons_cantidad"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        return ConversationHandler.END
    except ValueError as e:
        await reply_text(update, f"❌ {str(e)}")
        return MOVER_CONS_CANTIDAD
    except Exception as e:
        logger.error(f"Error moviendo consignment: {e}", exc_info=True)
        await reply_text(update, f"❌ Error: {str(e)}")
        return MOVER_CONS_CANTIDAD


mover_consignment_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("mover_consignment", mover_consignment_entry),
    ],
    states={
        MOVER_CONS_SEL_ORIGEN: [
            CallbackQueryHandler(mover_consignment_callback, pattern=r"^mover_cons:(source:|cancel)"),
        ],
        MOVER_CONS_SEL_PRODUCTO: [
            CallbackQueryHandler(mover_consignment_callback, pattern=r"^mover_cons:(prod:|back)"),
        ],
        MOVER_CONS_SEL_DESTINO: [
            CallbackQueryHandler(mover_consignment_callback, pattern=r"^mover_cons:(destination:|back)"),
        ],
        MOVER_CONS_CANTIDAD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mover_consignment_cantidad_receive),
            CallbackQueryHandler(mover_consignment_callback, pattern=r"^mover_cons:.*"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="mover_consignment_conversation",
    persistent=False,
)


# ========== PAGAR CONSIGNACIONES ==========

@admin_only
async def pagar_consignment_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para pagar consignaciones."""
    keys_to_remove = [
        "pagar_cons_vendedor_id", "pagar_cons_moneda_deuda", "pagar_cons_monto", "pagar_cons_moneda_pago", "pagar_cons_caja_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    vendedores = VendedorService.listar()
    if not vendedores:
        await reply_text(update, "❌ No vendedores disponibles. Crea uno primero.")
        return ConversationHandler.END
    
    text = "💰 <b>Pay Consignment</b>\n\nSelect the vendedor:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for vend in vendedores:
        keyboard.append([
            InlineKeyboardButton(
                f"👤 {vend['name']}",
                callback_data=f"pagar_cons:vend:{vend['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="pagar_cons:cancel")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)
    return PAGAR_CONS_SEL_VENDEDOR


async def pagar_consignment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del flujo de pago de consignaciones."""
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
                await reply_text(update, f"❌ The seller {vendedor['name']} has no debts POR_COBRAR.")
                return ConversationHandler.END
            
            text = f"👤 <b>Seller: {vendedor['name']}</b>\n\n<b>Deudas:</b>\n"
            for deuda in deudas_vendedor:
                text += f"• {deuda['monto_pendiente']:.2f} {deuda['moneda'].upper()}\n"
            text += "\nSelect the <b>moneda de la deuda</b> a pagar:"
            
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
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="pagar_cons:back")])
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
            f"💰 <b>Pay Consignment</b>\n\n"
            f"Seller: <code>{vendedor['name']}</code>\n"
            f"Deuda: <b>{deuda['monto_pendiente']:.2f} {moneda_deuda.upper()}</b>\n\n"
            f"Send el <b>monto</b> a pagar:"
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
        
        text = f"💰 <b>Pay Consignment</b>\n\n"
        text += f"Seller: <code>{vendedor['name']}</code>\n"
        text += f"Monto: <b>{monto} {moneda_pago.upper()}</b>\n\n"
        text += f"Select the <b>caja</b> donde se recibe el pago:"
        
        cajas = CajaService.listar()
        if not cajas:
            await reply_text(update, "❌ No cajas disponibles. Crea una primero.")
            return ConversationHandler.END
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for caja in cajas:
            keyboard.append([
                InlineKeyboardButton(
                    caja['nombre'].upper(),
                    callback_data=f"pagar_cons:caja:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="pagar_cons:back")])
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
            resultado = pagar_consignment(
                vendedor_id, moneda_deuda, monto, moneda_pago, caja_id, user_id
            )
            
            caja_obj = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja_obj['nombre'] if caja_obj else str(caja_id)
            
            vendedor = VendedorService.obtener_por_id(vendedor_id)
            
            text = f"✅ <b>Pago Registrado</b>\n\n"
            text += f"Seller: <code>{vendedor['name']}</code>\n"
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
        return await pagar_consignment_entry(update, context)
    
    if data == "pagar_cons:cancel":
        keys_to_remove = [
            "pagar_cons_vendedor_id", "pagar_cons_moneda_deuda", "pagar_cons_monto",
            "pagar_cons_moneda_pago", "pagar_cons_caja_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Operation canceled.")
        return ConversationHandler.END
    
    return PAGAR_CONS_SEL_VENDEDOR


async def pagar_consignment_monto_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        text += f"Seller: <code>{vendedor['name']}</code>\n"
        text += f"Deuda: <b>{deuda['monto_pendiente']:.2f} {moneda_deuda.upper()}</b>\n\n"
        text += f"Select the <b>moneda del pago</b>:"
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"pagar_cons:moneda_pago:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="pagar_cons:back")])
        kb = InlineKeyboardMarkup(keyboard)
        await reply_html(update, text, reply_markup=kb)
        return PAGAR_CONS_SEL_CAJA
    except ValueError:
        await reply_text(update, "❌ El monto debe ser un numero valid.")
        return PAGAR_CONS_MONTO


pagar_consignment_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("pagar_consignment", pagar_consignment_entry),
    ],
    states={
        PAGAR_CONS_SEL_VENDEDOR: [
            CallbackQueryHandler(pagar_consignment_callback, pattern=r"^pagar_cons:(vend:|cancel)"),
        ],
        PAGAR_CONS_SEL_MONEDA: [
            CallbackQueryHandler(pagar_consignment_callback, pattern=r"^pagar_cons:(moneda_deuda:|back)"),
        ],
        PAGAR_CONS_MONTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, pagar_consignment_monto_receive),
            CallbackQueryHandler(pagar_consignment_callback, pattern=r"^pagar_cons:.*"),
        ],
        PAGAR_CONS_SEL_CAJA: [
            CallbackQueryHandler(pagar_consignment_callback, pattern=r"^pagar_cons:(moneda_pago:|caja:|back)"),
        ],
    },
    fallbacks=[CommandHandler("cancel", mover_cancel_command)],
    name="pagar_consignment_conversation",
    persistent=False,
)

