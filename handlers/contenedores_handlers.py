"""
Handlers refactorizados para management de containeres.
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
from services.containeres_service import ContainerService
from services.proveedores_service import ProveedorService

logger = logging.getLogger(__name__)

# Estados de la conversation
MENU, CREAR_NOMBRE, CREAR_NUMERO, CREAR_PROVEEDOR, EDIT_MENU, EDIT_NOMBRE, EDIT_NUMERO, EDIT_PROVEEDOR, CONFIRM_DELETE = range(9)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del main menu."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create", callback_data="cont:create"),
            InlineKeyboardButton("📋 Listar", callback_data="cont:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="cont:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de containeres."""
    from utils.telegram_helpers import reply_html
    
    containeres = ContainerService.listar()
    
    if not containeres:
        text = "📦 <b>Containeres</b>\n\nStill no hay containeres recordeds."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create", callback_data="cont:create")],
            [InlineKeyboardButton("⬅️ Back", callback_data="cont:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "📦 <b>Containeres</b>\n\nSelect aa action para cada item:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in containeres:
        cont_id = cont["id"]
        nombre = cont["nombre"]
        numero = cont.get("numero_container", "")
        proveedor = cont.get("proveedor_name", "")
        
        # Mostrar informacion adicional si existe
        display_name = nombre
        if numero:
            display_name += f" ({numero})"
        if proveedor:
            display_name += f" - {proveedor}"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {display_name[:40]}", callback_data=f"cont:edit:{cont_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"cont:del:{cont_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="cont:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def containeres_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la management de containeres."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversationes anteriores
    keys_to_remove = [
        "cont_nombre", "cont_numero", "cont_proveedor_id",
        "cont_edit_id", "cont_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "🧰 <b>Management de Containeres</b>\n\n"
        "Administra tus containeres. Usa el menu de abajo."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle callbacks del menu."""
    from utils.telegram_helpers import reply_html, reply_text
    from core.config import ADMIN_USER_IDS
    
    # Verificar permisos manualmente para poder retornar un estado valid
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        q = update.callback_query
        if q:
            await q.answer()
            await q.edit_message_text("⛔ No tienes permiso.")
        return ConversationHandler.END
    
    q = update.callback_query
    data = (q.data if q else "") or ""
    
    if data == "cont:create":
        logger.info(f"Usuario {user_id} iniciando creation de container")
        
        # Limpiar datos previos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        
        # Responder al callback primero
        if q:
            await q.answer()
            try:
                # Intentar editar el mensaje directamente
                await q.edit_message_text(
                    "🆕 <b>Nuevo Container</b>\n\nSend el <b>nombre</b> para el container:",
                    parse_mode="HTML"
                )
                logger.info("Mensaje editado correctamente")
            except Exception as e:
                logger.error(f"Error editando mensaje: {e}", exc_info=True)
                # Si falla editar, enviar nuevo mensaje
                if q.message:
                    await q.message.reply_html(
                        "🆕 <b>Nuevo Container</b>\n\nSend el <b>nombre</b> para el container:"
                    )
        else:
            await reply_html(
                update,
                "🆕 <b>Nuevo Container</b>\n\nSend el <b>nombre</b> para el container:"
            )
        
        logger.info(f"Retornando estado CREAR_NOMBRE ({CREAR_NOMBRE})")
        return CREAR_NOMBRE
    
    # Para otros callbacks, responder primero
    if q:
        await q.answer()
    
    if data == "cont:skip_numero":
        context.user_data["cont_numero"] = None
        # Preguntar por proveedor
        proveedores = ProveedorService.listar()
        if not proveedores:
            return await _finalizar_creacion(update, context)
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, assign supplier", callback_data="cont:si_proveedor")],
            [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_proveedor")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cont:cancel")]
        ])
        await reply_html(
            update,
            f"✅ Nombre: <b>{context.user_data.get('cont_nombre', '')}</b>\n\n"
            "Do you want to asignar un <b>proveedor</b>?",
            reply_markup=kb
        )
        return CREAR_PROVEEDOR
    
    if data == "cont:list":
        await _render_list(update, context)
        return MENU
    
    if data == "cont:back":
        return await containeres_entry(update, context)
    
    if data == "cont:close":
        # Limpiar todos los datos de la conversation
        keys_to_remove = [
            "cont_nombre", "cont_numero", "cont_proveedor_id",
            "cont_edit_id", "cont_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Closed.")
        return ConversationHandler.END
    
    # Actions por item
    if data.startswith("cont:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_edit_id"] = cont_id
        container = ContainerService.obtener_por_id(cont_id)
        if not container:
            await reply_text(update, "❌ Container not found.")
            return MENU
        
        # Mostrar menu de edicion
        nombre = container['nombre']
        numero = container.get('numero_container', 'No asignado')
        proveedor = container.get('proveedor_name', 'No asignado')
        
        msg = (
            f"✏️ <b>Editar Container</b>\n\n"
            f"📦 Nombre: <code>{nombre}</code>\n"
            f"🔢 Numero: <code>{numero}</code>\n"
            f"👥 Supplier: <code>{proveedor}</code>\n\n"
            f"What would you like to edit?"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Nombre", callback_data="cont:edit_nombre")],
            [InlineKeyboardButton("🔢 Numero de Container", callback_data="cont:edit_numero")],
            [InlineKeyboardButton("👥 Supplier", callback_data="cont:edit_proveedor")],
            [InlineKeyboardButton("⬅️ Back", callback_data="cont:back")]
        ])
        
        await reply_html(update, msg, reply_markup=kb)
        return EDIT_MENU
    
    if data == "cont:edit_nombre":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        container = ContainerService.obtener_por_id(cont_id)
        if not container:
            await reply_text(update, "❌ Container not found.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Editar Nombre</b>\n\n"
            f"Actual: <code>{container['nombre']}</code>\n"
            f"Send el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "cont:edit_numero":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        container = ContainerService.obtener_por_id(cont_id)
        if not container:
            await reply_text(update, "❌ Container not found.")
            return MENU
        numero_actual = container.get('numero_container', 'No asignado')
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete numero", callback_data="cont:remove_numero")],
            [InlineKeyboardButton("⬅️ Cancel", callback_data="cont:back")]
        ])
        await reply_html(
            update,
            f"🔢 <b>Editar Numero de Container</b>\n\n"
            f"Actual: <code>{numero_actual}</code>\n"
            f"Send el <b>nuevo numero</b> (o usa el boton para deletelo):",
            reply_markup=kb
        )
        return EDIT_NUMERO
    
    if data == "cont:edit_proveedor":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        container = ContainerService.obtener_por_id(cont_id)
        if not container:
            await reply_text(update, "❌ Container not found.")
            return MENU
        
        proveedor_actual = container["proveedor_name"] if container["proveedor_name"] else "No asignado"
        proveedores = ProveedorService.listar()
        
        keyboard: List[List[InlineKeyboardButton]] = []
        if proveedores:
            for prov in proveedores:
                prov_id = prov["id"]
                nombre = prov["name"]
                # Marcar el proveedor actual si existe
                marker = "✓ " if nombre == proveedor_actual else ""
                keyboard.append([
                    InlineKeyboardButton(f"{marker}{nombre}", callback_data=f"cont:set_prov:{prov_id}")
                ])
        keyboard.append([
            InlineKeyboardButton("🗑️ Remove supplier", callback_data="cont:remove_proveedor"),
            InlineKeyboardButton("⬅️ Cancel", callback_data="cont:back")
        ])
        kb = InlineKeyboardMarkup(keyboard)
        
        await reply_html(
            update,
            f"👥 <b>Editar Supplier</b>\n\n"
            f"Actual: <code>{proveedor_actual}</code>\n\n"
            f"Select a proveedor:",
            reply_markup=kb
        )
        return EDIT_PROVEEDOR
    
    if data == "cont:remove_numero":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        try:
            ContainerService.update(int(cont_id), numero_container="")
            await reply_text(update, "✅ Numero de container deleted.")
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except Exception as e:
            logger.error(f"Error eliminando numero: {e}", exc_info=True)
            await reply_text(update, "❌ Error while delete el numero.")
            return MENU
    
    if data.startswith("cont:set_prov:"):
        # Responder al callback primero
        if q:
            await q.answer()
        
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        
        try:
            prov_id = int(data.split(":")[-1])
            ContainerService.update(int(cont_id), proveedor_id=prov_id)
            proveedor = ProveedorService.obtener_por_id(prov_id)
            nombre_prov = proveedor['name'] if proveedor else "Supplier"
            
            # Editar el mensaje o enviar uno nuevo
            if q:
                try:
                    await q.edit_message_text(
                        f"✅ <b>Supplier asignado</b>\n\nSupplier: <code>{nombre_prov}</code>",
                        parse_mode="HTML"
                    )
                except Exception:
                    if q.message:
                        await q.message.reply_html(f"✅ <b>Supplier asignado</b>\n\nSupplier: <code>{nombre_prov}</code>")
            else:
                await reply_text(update, f"✅ Supplier asignado: {nombre_prov}")
            
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except ValueError as e:
            logger.error(f"Error: validacion asignando proveedor: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {e}")
            return MENU
        except Exception as e:
            logger.error(f"Error asignando proveedor: {e}", exc_info=True)
            await reply_text(update, "❌ Error while assigning supplier.")
            return MENU
    
    if data == "cont:remove_proveedor":
        # Responder al callback primero
        if q:
            await q.answer()
        
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No container en edicion.")
            return MENU
        try:
            # Usar quitar_proveedor=True para establecer proveedor_id a NULL
            ContainerService.update(int(cont_id), quitar_proveedor=True)
            
            # Editar el mensaje o enviar uno nuevo
            if q:
                try:
                    await q.edit_message_text("✅ Supplier quitado del container.")
                except Exception:
                    if q.message:
                        await q.message.reply_text("✅ Supplier quitado del container.")
            else:
                await reply_text(update, "✅ Supplier quitado del container.")
            
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except Exception as e:
            logger.error(f"Error eliminando proveedor: {e}", exc_info=True)
            await reply_text(update, "❌ Error while removing supplier.")
            return MENU
    
    if data.startswith("cont:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_del_id"] = cont_id
        container = ContainerService.obtener_por_id(cont_id)
        if not container:
            await reply_text(update, "❌ Container not found.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, borrar", callback_data="cont:delok"),
             InlineKeyboardButton("↩️ Cancel", callback_data="cont:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar deletion</b>\n\n"
            f"Vas a borrar: <code>{container['nombre']}</code>\n"
            f"Esta action no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "cont:delok":
        from utils.telegram_helpers import reply_text
        
        cont_id = context.user_data.get("cont_del_id")
        if cont_id is None:
            await reply_text(update, "❌ No elemento para delete.")
            await _render_list(update, context)
            return MENU
        try:
            ContainerService.delete(int(cont_id))
            # Limpiar el ID de deletion
            context.user_data.pop("cont_del_id", None)
            # Mostrar mensaje y luego la lista updated
            await reply_text(update, "🗑️ Container deleted correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando container: {e}", exc_info=True)
            await reply_text(update, "❌ Could not delete. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "cont:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def create_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para create un container."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar empty. Send un nombre valid.")
        return CREAR_NOMBRE
    
    # Guardar el nombre en el contexto
    context.user_data["cont_nombre"] = nombre
    
    # Preguntar por numero de container
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_numero")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cont:cancel")]
    ])
    await reply_html(
        update,
        f"✅ Nombre: <b>{nombre}</b>\n\n"
        "Send el <b>numero de container</b> (opcional):",
        reply_markup=kb
    )
    return CREAR_NUMERO


@admin_only
async def create_numero_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el numero de container."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NUMERO
    
    numero = (update.message.text or "").strip()
    context.user_data["cont_numero"] = numero if numero else None
    
    # Preguntar si quiere asignar un proveedor
    proveedores = ProveedorService.listar()
    if not proveedores:
        # No proveedores, create directamente
        return await _finalizar_creacion(update, context)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, assign supplier", callback_data="cont:si_proveedor")],
        [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_proveedor")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cont:cancel")]
    ])
    
    numero_text = f"📦 Numero: <b>{numero}</b>\n" if numero else ""
    await reply_html(
        update,
        f"✅ Nombre: <b>{context.user_data['cont_nombre']}</b>\n"
        f"{numero_text}\n"
        "Do you want to asignar un <b>proveedor</b>?",
        reply_markup=kb
    )
    return CREAR_PROVEEDOR


@admin_only
async def create_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle la selection de proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    logger.info(f"create_proveedor_callback: data={data}")
    
    if data == "cont:skip_proveedor":
        context.user_data["cont_proveedor_id"] = None
        return await _finalizar_creacion(update, context)
    
    if data == "cont:cancel":
        await reply_text(update, "✅ Operation canceled.")
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    
    if data == "cont:si_proveedor":
        # Mostrar lista de proveedores
        proveedores = ProveedorService.listar()
        if not proveedores:
            await reply_text(update, "❌ No suppliers available. Creating container without supplier.")
            context.user_data["cont_proveedor_id"] = None
            return await _finalizar_creacion(update, context)
        
        keyboard: List[List[InlineKeyboardButton]] = []
        for prov in proveedores:
            prov_id = prov["id"]
            nombre = prov["name"]
            keyboard.append([
                InlineKeyboardButton(nombre, callback_data=f"cont:prov:{prov_id}")
            ])
        keyboard.append([
            InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_proveedor"),
            InlineKeyboardButton("❌ Cancel", callback_data="cont:cancel")
        ])
        kb = InlineKeyboardMarkup(keyboard)
        
        # Editar el mensaje si es un callback, o enviar uno nuevo
        if q:
            try:
                await q.edit_message_text(
                    "👥 <b>Select a proveedor:</b>",
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Error editando mensaje: {e}")
                await reply_html(update, "👥 <b>Select a proveedor:</b>", reply_markup=kb)
        else:
            await reply_html(update, "👥 <b>Select a proveedor:</b>", reply_markup=kb)
        return CREAR_PROVEEDOR
    
    if data.startswith("cont:prov:"):
        try:
            prov_id = int(data.split(":")[-1])
            logger.info(f"Asignando proveedor {prov_id} al container")
            context.user_data["cont_proveedor_id"] = prov_id
            return await _finalizar_creacion(update, context)
        except (ValueError, IndexError) as e:
            logger.error(f"Error parseando proveedor_id: {e}, data={data}")
            await reply_text(update, "❌ Error while processing supplier selection.")
            return CREAR_PROVEEDOR
    
    logger.warning(f"Callback no manejado en create_proveedor_callback: {data}")
    return CREAR_PROVEEDOR


async def _finalizar_creacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza la creation del container con todos los datos."""
    from utils.telegram_helpers import reply_html, reply_text
    
    nombre = context.user_data.get("cont_nombre")
    numero = context.user_data.get("cont_numero")
    proveedor_id = context.user_data.get("cont_proveedor_id")
    
    logger.info(f"_finalizar_creacion: nombre={nombre}, numero={numero}, proveedor_id={proveedor_id}")
    
    if not nombre:
        await reply_text(update, "❌ Error: Not found el nombre del container.")
        return ConversationHandler.END
    
    try:
        resultado = ContainerService.create(nombre, numero, proveedor_id)
        
        # Construir mensaje de confirmacion
        msg = f"✅ <b>Container Creado</b>\n\n"
        msg += f"📦 Nombre: <code>{nombre}</code>\n"
        if numero:
            msg += f"🔢 Numero: <code>{numero}</code>\n"
        if proveedor_id:
            proveedor = ProveedorService.obtener_por_id(proveedor_id)
            if proveedor:
                msg += f"👥 Supplier: <code>{proveedor['name']}</code>\n"
        
        # Si es un callback, editar el mensaje, sino enviar uno nuevo
        q = update.callback_query
        if q:
            try:
                await q.edit_message_text(msg, parse_mode="HTML")
                await reply_html(update, "What would you like to do now?", reply_markup=_main_menu_kb())
            except Exception as e:
                logger.error(f"Error editando mensaje en _finalizar_creacion: {e}")
                await reply_html(update, msg)
                await reply_html(update, "What would you like to do now?", reply_markup=_main_menu_kb())
        else:
            await reply_html(update, msg)
            await reply_html(update, "What would you like to do now?", reply_markup=_main_menu_kb())
        
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un container con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        # Limpiar y volver al inicio
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error creando container: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al create. Try again.")
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un container."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    cont_id = context.user_data.get("cont_edit_id")
    if cont_id is None:
        await reply_text(update, "❌ No container en edicion.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar empty. Send un nombre valid.")
        return EDIT_NOMBRE
    
    try:
        ContainerService.update(int(cont_id), nuevo_nombre=nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("cont_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un container con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando container: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al update. Try again.")
        return EDIT_NOMBRE


@admin_only
async def edit_numero_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo numero de container."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    cont_id = context.user_data.get("cont_edit_id")
    if cont_id is None:
        await reply_text(update, "❌ No container en edicion.")
        return MENU
    
    nuevo_numero = (update.message.text or "").strip()
    
    try:
        ContainerService.update(int(cont_id), numero_container=nuevo_numero if nuevo_numero else None)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo numero: <code>{nuevo_numero if nuevo_numero else 'Eliminado'}</code>"
        )
        context.user_data.pop("cont_edit_id", None)
        await _render_list(update, context)
        return MENU
    except Exception as e:
        logger.error(f"Error actualizando numero: {e}", exc_info=True)
        await reply_text(update, "❌ An error occurred al update. Try again.")
        return EDIT_NUMERO


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operation actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversation
    keys_to_remove = [
        "cont_nombre", "cont_numero", "cont_proveedor_id",
        "cont_edit_id", "cont_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operation canceled.")
    return ConversationHandler.END


# ConversationHandler exportable
containeres_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("containeres", containeres_entry),
        CallbackQueryHandler(containeres_entry, pattern=r"^menu:containeres$"),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(create|back|close|cancel)$"),
        ],
        CREAR_NUMERO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_numero_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(skip_numero|cancel)$"),
        ],
        CREAR_PROVEEDOR: [
            CallbackQueryHandler(create_proveedor_callback, pattern=r"^cont:(si_proveedor|skip_proveedor|prov:\d+|cancel)$"),
        ],
        EDIT_MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(edit_nombre|edit_numero|edit_proveedor|back)$"),
        ],
        EDIT_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(back|cancel)$"),
        ],
        EDIT_NUMERO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_numero_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(remove_numero|back|cancel)$"),
        ],
        EDIT_PROVEEDOR: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(set_prov:\d+|remove_proveedor|back|cancel)$"),
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(delok|cancel)$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)],
    name="containeres_conversation",
    persistent=False,
)

