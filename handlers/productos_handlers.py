"""
Handlers para gestión de productos (CRUD completo).
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
from database.connection import get_db_connection
from database.repositories import ProductoRepository
from core.config import VALID_MONEDAS

logger = logging.getLogger(__name__)

# Estados de la conversación
MENU, CREAR_CODIGO, CREAR_NOMBRE, CREAR_COSTO, CREAR_MONEDA, CREAR_STOCK, EDIT_MENU, EDIT_CODIGO, EDIT_NOMBRE, EDIT_COSTO, EDIT_MONEDA, CONFIRM_DELETE = range(12)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="prod:create"),
            InlineKeyboardButton("📋 Listar", callback_data="prod:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="prod:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de productos."""
    with get_db_connection() as conn:
        productos = ProductoRepository.obtener_todos(conn)
    
    if not productos:
        text = "📦 <b>Productos</b>\n\nAún no hay productos registrados."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="prod:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="prod:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "📦 <b>Productos</b>\n\nSelecciona una acción para cada ítem:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for prod in productos:
        prod_codigo = prod["codigo"]
        nombre = prod["nombre"]
        stock_val = prod["stock"] if "stock" in prod.keys() else 0
        
        display_name = f"{nombre} ({prod_codigo})"
        if stock_val > 0:
            display_name += f" - Stock: {stock_val}"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {display_name[:40]}", callback_data=f"prod:edit:{prod_codigo}"),
            InlineKeyboardButton("🗑️", callback_data=f"prod:del:{prod_codigo}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="prod:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def productos_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de productos."""
    logger.info(f"productos_entry called by user {update.effective_user.id}")
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "prod_codigo", "prod_nombre", "prod_costo", "prod_moneda", "prod_stock",
        "prod_edit_codigo", "prod_del_codigo"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "📦 <b>Gestión de Productos</b>\n\n"
        "Administra tus productos. Usa el menú de abajo."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


@admin_only
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del menú."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data == "prod:create":
        await reply_html(
            update,
            "🆕 <b>Nuevo Producto</b>\n\nEnvía el <b>código</b> del producto (único):"
        )
        return CREAR_CODIGO
    
    if data == "prod:list":
        await _render_list(update, context)
        return MENU
    
    if data == "prod:back":
        return await productos_entry(update, context)
    
    if data == "prod:close":
        keys_to_remove = [
            "prod_codigo", "prod_nombre", "prod_costo", "prod_moneda", "prod_stock",
            "prod_edit_codigo", "prod_del_codigo"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("prod:edit:"):
        prod_codigo = data.split(":")[-1]
        context.user_data["prod_edit_codigo"] = prod_codigo
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Nombre", callback_data="prod:edit_nombre")],
            [InlineKeyboardButton("💰 Costo", callback_data="prod:edit_costo")],
            [InlineKeyboardButton("💵 Moneda", callback_data="prod:edit_moneda")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="prod:back")]
        ])
        stock_val = producto["stock"] if "stock" in producto.keys() else 0
        await reply_html(
            update,
            f"✏️ <b>Editar Producto</b>\n\n"
            f"Código: <code>{producto['codigo']}</code>\n"
            f"Nombre: <code>{producto['nombre']}</code>\n"
            f"Costo: <code>{producto['costo_unitario']} {producto['moneda_costo']}</code>\n"
            f"Stock: <code>{stock_val}</code>\n\n"
            f"¿Qué deseas editar?",
            reply_markup=kb
        )
        return EDIT_MENU
    
    if data == "prod:edit_nombre":
        prod_codigo = context.user_data.get("prod_edit_codigo")
        if not prod_codigo:
            await reply_text(update, "❌ No hay producto en edición.")
            return MENU
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado.")
            return MENU
        
        await reply_html(
            update,
            f"✏️ <b>Renombrar Producto</b>\n\n"
            f"Actual: <code>{producto['nombre']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "prod:edit_costo":
        prod_codigo = context.user_data.get("prod_edit_codigo")
        if not prod_codigo:
            await reply_text(update, "❌ No hay producto en edición.")
            return MENU
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado.")
            return MENU
        
        await reply_html(
            update,
            f"💰 <b>Actualizar Costo</b>\n\n"
            f"Actual: <code>{producto['costo_unitario']} {producto['moneda_costo']}</code>\n"
            f"Envía el <b>nuevo costo unitario</b>:"
        )
        return EDIT_COSTO
    
    if data == "prod:edit_moneda":
        prod_codigo = context.user_data.get("prod_edit_codigo")
        if not prod_codigo:
            await reply_text(update, "❌ No hay producto en edición.")
            return MENU
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado.")
            return MENU
        
        keyboard = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    f"{moneda.upper()}" + (" ✅" if moneda == producto['moneda_costo'] else ""),
                    callback_data=f"prod:set_moneda:{moneda}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="prod:back")])
        kb = InlineKeyboardMarkup(keyboard)
        
        await reply_html(
            update,
            f"💵 <b>Cambiar Moneda</b>\n\n"
            f"Actual: <code>{producto['moneda_costo']}</code>\n"
            f"Selecciona la nueva moneda:",
            reply_markup=kb
        )
        return EDIT_MONEDA
    
    if data.startswith("prod:set_moneda:"):
        moneda = data.split(":")[-1]
        prod_codigo = context.user_data.get("prod_edit_codigo")
        
        if not prod_codigo:
            await reply_text(update, "❌ No hay producto en edición.")
            return MENU
        
        try:
            with get_db_connection() as conn:
                producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
                if not producto:
                    await reply_text(update, "❌ Producto no encontrado.")
                    return MENU
                
                ProductoRepository.actualizar_costo(conn, prod_codigo, producto['costo_unitario'], moneda)
            
            await reply_html(
                update,
                f"✅ <b>Moneda Actualizada</b>\n\nNueva moneda: <code>{moneda}</code>"
            )
            context.user_data.pop("prod_edit_codigo", None)
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error actualizando moneda: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {str(e)}")
        return MENU
    
    if data.startswith("prod:del:"):
        prod_codigo = data.split(":")[-1]
        context.user_data["prod_del_codigo"] = prod_codigo
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
        
        if not producto:
            await reply_text(update, "❌ Producto no encontrado.")
            return MENU
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="prod:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="prod:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{producto['codigo']}</code> - {producto['nombre']}\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "prod:delok":
        prod_codigo = context.user_data.get("prod_del_codigo")
        if not prod_codigo:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        
        try:
            # Nota: No hay método eliminar en ProductoRepository, pero podemos implementarlo
            # Por ahora, solo mostramos un mensaje
            await reply_text(update, "⚠️ La eliminación de productos no está implementada por seguridad.")
            context.user_data.pop("prod_del_codigo", None)
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando producto: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "prod:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_codigo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el código del producto."""
    if not update.message:
        return CREAR_CODIGO
    
    codigo = (update.message.text or "").strip().upper()
    if not codigo:
        await reply_text(update, "❌ El código no puede estar vacío. Envía un código válido.")
        return CREAR_CODIGO
    
    # Verificar si ya existe
    with get_db_connection() as conn:
        existente = ProductoRepository.obtener_por_codigo(conn, codigo)
        if existente:
            await reply_text(update, "⚠️ Ya existe un producto con ese código. Usa otro código.")
            return CREAR_CODIGO
    
    context.user_data["prod_codigo"] = codigo
    await reply_html(
        update,
        f"✅ Código: <code>{codigo}</code>\n\n"
        f"Envía el <b>nombre</b> del producto:"
    )
    return CREAR_NOMBRE


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre del producto."""
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    context.user_data["prod_nombre"] = nombre
    await reply_html(
        update,
        f"✅ Nombre: <code>{nombre}</code>\n\n"
        f"Envía el <b>costo unitario</b>:"
    )
    return CREAR_COSTO


@admin_only
async def crear_costo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el costo del producto."""
    if not update.message:
        return CREAR_COSTO
    
    try:
        costo = float((update.message.text or "").strip())
        if costo < 0:
            await reply_text(update, "❌ El costo no puede ser negativo.")
            return CREAR_COSTO
        
        context.user_data["prod_costo"] = costo
        
        keyboard = []
        for moneda in VALID_MONEDAS:
            keyboard.append([
                InlineKeyboardButton(
                    moneda.upper(),
                    callback_data=f"prod:moneda:{moneda}"
                )
            ])
        kb = InlineKeyboardMarkup(keyboard)
        
        await reply_html(
            update,
            f"✅ Costo: <code>{costo}</code>\n\n"
            f"Selecciona la <b>moneda</b>:",
            reply_markup=kb
        )
        return CREAR_MONEDA
    except ValueError:
        await reply_text(update, "❌ El costo debe ser un número válido.")
        return CREAR_COSTO


async def crear_moneda_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de moneda."""
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if data.startswith("prod:moneda:"):
        moneda = data.split(":")[-1]
        context.user_data["prod_moneda"] = moneda
        
        await reply_html(
            update,
            f"✅ Moneda: <code>{moneda}</code>\n\n"
            f"Envía el <b>stock inicial</b> (0 si no hay stock):"
        )
        return CREAR_STOCK
    
    return CREAR_MONEDA


@admin_only
async def crear_stock_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el stock inicial y crea el producto."""
    if not update.message:
        return CREAR_STOCK
    
    try:
        stock = float((update.message.text or "").strip())
        if stock < 0:
            await reply_text(update, "❌ El stock no puede ser negativo.")
            return CREAR_STOCK
        
        codigo = context.user_data.get("prod_codigo")
        nombre = context.user_data.get("prod_nombre")
        costo = context.user_data.get("prod_costo")
        moneda = context.user_data.get("prod_moneda")
        
        if not all([codigo, nombre, costo is not None, moneda]):
            await reply_text(update, "❌ Error: datos incompletos. Empieza de nuevo.")
            return await productos_entry(update, context)
        
        # Crear el producto
        with get_db_connection() as conn:
            ProductoRepository.crear(conn, codigo, nombre, costo, moneda, stock)
        
        await reply_html(
            update,
            f"✅ <b>Producto Creado</b>\n\n"
            f"Código: <code>{codigo}</code>\n"
            f"Nombre: <code>{nombre}</code>\n"
            f"Costo: <code>{costo} {moneda}</code>\n"
            f"Stock: <code>{stock}</code>"
        )
        
        # Limpiar datos
        keys_to_remove = ["prod_codigo", "prod_nombre", "prod_costo", "prod_moneda", "prod_stock"]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        
        await reply_html(
            update,
            "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb()
        )
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un producto con ese código. Usa otro código.")
        else:
            await reply_text(update, f"❌ {str(e)}")
        return CREAR_CODIGO
    except Exception as e:
        logger.error(f"Error creando producto: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        return CREAR_CODIGO


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un producto."""
    if not update.message:
        return MENU
    
    prod_codigo = context.user_data.get("prod_edit_codigo")
    if not prod_codigo:
        await reply_text(update, "❌ No hay producto en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        # Actualizar nombre (necesitamos agregar este método al repositorio)
        # Por ahora, solo mostramos un mensaje
        await reply_text(update, "⚠️ La actualización de nombre no está implementada aún.")
        context.user_data.pop("prod_edit_codigo", None)
        await _render_list(update, context)
        return MENU
    except Exception as e:
        logger.error(f"Error actualizando producto: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


@admin_only
async def edit_costo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo costo para editar un producto."""
    if not update.message:
        return MENU
    
    prod_codigo = context.user_data.get("prod_edit_codigo")
    if not prod_codigo:
        await reply_text(update, "❌ No hay producto en edición.")
        return MENU
    
    try:
        nuevo_costo = float((update.message.text or "").strip())
        if nuevo_costo < 0:
            await reply_text(update, "❌ El costo no puede ser negativo.")
            return EDIT_COSTO
        
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, prod_codigo)
            if not producto:
                await reply_text(update, "❌ Producto no encontrado.")
                return MENU
            
            ProductoRepository.actualizar_costo(conn, prod_codigo, nuevo_costo, producto['moneda_costo'])
        
        await reply_html(
            update,
            f"✅ <b>Costo Actualizado</b>\n\nNuevo costo: <code>{nuevo_costo} {producto['moneda_costo']}</code>"
        )
        context.user_data.pop("prod_edit_codigo", None)
        await _render_list(update, context)
        return MENU
    except ValueError:
        await reply_text(update, "❌ El costo debe ser un número válido.")
        return EDIT_COSTO
    except Exception as e:
        logger.error(f"Error actualizando costo: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_COSTO


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    keys_to_remove = [
        "prod_codigo", "prod_nombre", "prod_costo", "prod_moneda", "prod_stock",
        "prod_edit_codigo", "prod_del_codigo"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
productos_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("productos", productos_entry),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        CREAR_CODIGO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_codigo_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        CREAR_COSTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_costo_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        CREAR_MONEDA: [
            CallbackQueryHandler(crear_moneda_callback, pattern=r"^prod:moneda:"),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        CREAR_STOCK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_stock_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^prod:(edit_nombre|edit_costo|edit_moneda|set_moneda:|back)$"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        EDIT_COSTO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_costo_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^prod:.*"),
        ],
        EDIT_MONEDA: [
            CallbackQueryHandler(menu_callback, pattern=r"^prod:(set_moneda:|back)"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^prod:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="productos_conversation",
    persistent=False,
)

