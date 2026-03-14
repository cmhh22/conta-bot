"""
Handlers refactorizados para gestión de contenedores.
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
from services.contenedores_service import ContenedorService
from services.proveedores_service import ProveedorService

logger = logging.getLogger(__name__)

# Estados de la conversación
MENU, CREAR_NOMBRE, CREAR_NUMERO, CREAR_PROVEEDOR, EDIT_MENU, EDIT_NOMBRE, EDIT_NUMERO, EDIT_PROVEEDOR, CONFIRM_DELETE = range(9)


def _main_menu_kb() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Crear", callback_data="cont:create"),
            InlineKeyboardButton("📋 Listar", callback_data="cont:list"),
        ],
        [InlineKeyboardButton("❌ Cerrar", callback_data="cont:close")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Renderiza la lista de contenedores."""
    from utils.telegram_helpers import reply_html
    
    contenedores = ContenedorService.listar()
    
    if not contenedores:
        text = "📦 <b>Contenedores</b>\n\nAún no hay contenedores registrados."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Crear", callback_data="cont:create")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="cont:back")]
        ])
        await reply_html(update, text, reply_markup=kb)
        return
    
    text = "📦 <b>Contenedores</b>\n\nSelecciona una acción para cada ítem:"
    keyboard: List[List[InlineKeyboardButton]] = []
    for cont in contenedores:
        cont_id = cont["id"]
        nombre = cont["nombre"]
        numero = cont.get("numero_contenedor", "")
        proveedor = cont.get("proveedor_name", "")
        
        # Mostrar información adicional si existe
        display_name = nombre
        if numero:
            display_name += f" ({numero})"
        if proveedor:
            display_name += f" - {proveedor}"
        
        keyboard.append([
            InlineKeyboardButton(f"✏️ {display_name[:40]}", callback_data=f"cont:edit:{cont_id}"),
            InlineKeyboardButton("🗑️", callback_data=f"cont:del:{cont_id}"),
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="cont:back")])
    kb = InlineKeyboardMarkup(keyboard)
    
    await reply_html(update, text, reply_markup=kb)


@admin_only
async def contenedores_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Punto de entrada para la gestión de contenedores."""
    from utils.telegram_helpers import reply_html
    
    # Limpiar cualquier dato residual de conversaciones anteriores
    keys_to_remove = [
        "cont_nombre", "cont_numero", "cont_proveedor_id",
        "cont_edit_id", "cont_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    msg = (
        "🧰 <b>Gestión de Contenedores</b>\n\n"
        "Administra tus contenedores. Usa el menú de abajo."
    )
    await reply_html(update, msg, reply_markup=_main_menu_kb())
    return MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja los callbacks del menú."""
    from utils.telegram_helpers import reply_html, reply_text
    from core.config import ADMIN_USER_IDS
    
    # Verificar permisos manualmente para poder retornar un estado válido
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
        logger.info(f"Usuario {user_id} iniciando creación de contenedor")
        
        # Limpiar datos previos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        
        # Responder al callback primero
        if q:
            await q.answer()
            try:
                # Intentar editar el mensaje directamente
                await q.edit_message_text(
                    "🆕 <b>Nuevo Contenedor</b>\n\nEnvía el <b>nombre</b> para el contenedor:",
                    parse_mode="HTML"
                )
                logger.info("Mensaje editado correctamente")
            except Exception as e:
                logger.error(f"Error editando mensaje: {e}", exc_info=True)
                # Si falla editar, enviar nuevo mensaje
                if q.message:
                    await q.message.reply_html(
                        "🆕 <b>Nuevo Contenedor</b>\n\nEnvía el <b>nombre</b> para el contenedor:"
                    )
        else:
            await reply_html(
                update,
                "🆕 <b>Nuevo Contenedor</b>\n\nEnvía el <b>nombre</b> para el contenedor:"
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
            [InlineKeyboardButton("✅ Sí, asignar proveedor", callback_data="cont:si_proveedor")],
            [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_proveedor")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cont:cancel")]
        ])
        await reply_html(
            update,
            f"✅ Nombre: <b>{context.user_data.get('cont_nombre', '')}</b>\n\n"
            "¿Deseas asignar un <b>proveedor</b>?",
            reply_markup=kb
        )
        return CREAR_PROVEEDOR
    
    if data == "cont:list":
        await _render_list(update, context)
        return MENU
    
    if data == "cont:back":
        return await contenedores_entry(update, context)
    
    if data == "cont:close":
        # Limpiar todos los datos de la conversación
        keys_to_remove = [
            "cont_nombre", "cont_numero", "cont_proveedor_id",
            "cont_edit_id", "cont_del_id"
        ]
        for key in keys_to_remove:
            context.user_data.pop(key, None)
        await reply_text(update, "✅ Cerrado.")
        return ConversationHandler.END
    
    # Acciones por ítem
    if data.startswith("cont:edit:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_edit_id"] = cont_id
        contenedor = ContenedorService.obtener_por_id(cont_id)
        if not contenedor:
            await reply_text(update, "❌ Contenedor no encontrado.")
            return MENU
        
        # Mostrar menú de edición
        nombre = contenedor['nombre']
        numero = contenedor.get('numero_contenedor', 'No asignado')
        proveedor = contenedor.get('proveedor_name', 'No asignado')
        
        msg = (
            f"✏️ <b>Editar Contenedor</b>\n\n"
            f"📦 Nombre: <code>{nombre}</code>\n"
            f"🔢 Número: <code>{numero}</code>\n"
            f"👥 Proveedor: <code>{proveedor}</code>\n\n"
            f"¿Qué deseas editar?"
        )
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Nombre", callback_data="cont:edit_nombre")],
            [InlineKeyboardButton("🔢 Número de Contenedor", callback_data="cont:edit_numero")],
            [InlineKeyboardButton("👥 Proveedor", callback_data="cont:edit_proveedor")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="cont:back")]
        ])
        
        await reply_html(update, msg, reply_markup=kb)
        return EDIT_MENU
    
    if data == "cont:edit_nombre":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        contenedor = ContenedorService.obtener_por_id(cont_id)
        if not contenedor:
            await reply_text(update, "❌ Contenedor no encontrado.")
            return MENU
        await reply_html(
            update,
            f"✏️ <b>Editar Nombre</b>\n\n"
            f"Actual: <code>{contenedor['nombre']}</code>\n"
            f"Envía el <b>nuevo nombre</b>:"
        )
        return EDIT_NOMBRE
    
    if data == "cont:edit_numero":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        contenedor = ContenedorService.obtener_por_id(cont_id)
        if not contenedor:
            await reply_text(update, "❌ Contenedor no encontrado.")
            return MENU
        numero_actual = contenedor.get('numero_contenedor', 'No asignado')
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Eliminar número", callback_data="cont:remove_numero")],
            [InlineKeyboardButton("⬅️ Cancelar", callback_data="cont:back")]
        ])
        await reply_html(
            update,
            f"🔢 <b>Editar Número de Contenedor</b>\n\n"
            f"Actual: <code>{numero_actual}</code>\n"
            f"Envía el <b>nuevo número</b> (o usa el botón para eliminarlo):",
            reply_markup=kb
        )
        return EDIT_NUMERO
    
    if data == "cont:edit_proveedor":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        contenedor = ContenedorService.obtener_por_id(cont_id)
        if not contenedor:
            await reply_text(update, "❌ Contenedor no encontrado.")
            return MENU
        
        proveedor_actual = contenedor["proveedor_name"] if contenedor["proveedor_name"] else "No asignado"
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
            InlineKeyboardButton("🗑️ Quitar proveedor", callback_data="cont:remove_proveedor"),
            InlineKeyboardButton("⬅️ Cancelar", callback_data="cont:back")
        ])
        kb = InlineKeyboardMarkup(keyboard)
        
        await reply_html(
            update,
            f"👥 <b>Editar Proveedor</b>\n\n"
            f"Actual: <code>{proveedor_actual}</code>\n\n"
            f"Selecciona un proveedor:",
            reply_markup=kb
        )
        return EDIT_PROVEEDOR
    
    if data == "cont:remove_numero":
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        try:
            ContenedorService.actualizar(int(cont_id), numero_contenedor="")
            await reply_text(update, "✅ Número de contenedor eliminado.")
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except Exception as e:
            logger.error(f"Error eliminando número: {e}", exc_info=True)
            await reply_text(update, "❌ Error al eliminar el número.")
            return MENU
    
    if data.startswith("cont:set_prov:"):
        # Responder al callback primero
        if q:
            await q.answer()
        
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        
        try:
            prov_id = int(data.split(":")[-1])
            ContenedorService.actualizar(int(cont_id), proveedor_id=prov_id)
            proveedor = ProveedorService.obtener_por_id(prov_id)
            nombre_prov = proveedor['name'] if proveedor else "Proveedor"
            
            # Editar el mensaje o enviar uno nuevo
            if q:
                try:
                    await q.edit_message_text(
                        f"✅ <b>Proveedor asignado</b>\n\nProveedor: <code>{nombre_prov}</code>",
                        parse_mode="HTML"
                    )
                except Exception:
                    if q.message:
                        await q.message.reply_html(f"✅ <b>Proveedor asignado</b>\n\nProveedor: <code>{nombre_prov}</code>")
            else:
                await reply_text(update, f"✅ Proveedor asignado: {nombre_prov}")
            
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except ValueError as e:
            logger.error(f"Error de validación asignando proveedor: {e}", exc_info=True)
            await reply_text(update, f"❌ Error: {e}")
            return MENU
        except Exception as e:
            logger.error(f"Error asignando proveedor: {e}", exc_info=True)
            await reply_text(update, "❌ Error al asignar el proveedor.")
            return MENU
    
    if data == "cont:remove_proveedor":
        # Responder al callback primero
        if q:
            await q.answer()
        
        cont_id = context.user_data.get("cont_edit_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay contenedor en edición.")
            return MENU
        try:
            # Usar quitar_proveedor=True para establecer proveedor_id a NULL
            ContenedorService.actualizar(int(cont_id), quitar_proveedor=True)
            
            # Editar el mensaje o enviar uno nuevo
            if q:
                try:
                    await q.edit_message_text("✅ Proveedor quitado del contenedor.")
                except Exception:
                    if q.message:
                        await q.message.reply_text("✅ Proveedor quitado del contenedor.")
            else:
                await reply_text(update, "✅ Proveedor quitado del contenedor.")
            
            context.user_data.pop("cont_edit_id", None)
            await _render_list(update, context)
            return MENU
        except Exception as e:
            logger.error(f"Error eliminando proveedor: {e}", exc_info=True)
            await reply_text(update, "❌ Error al eliminar el proveedor.")
            return MENU
    
    if data.startswith("cont:del:"):
        from utils.telegram_helpers import reply_html, reply_text
        
        cont_id = int(data.split(":")[-1])
        context.user_data["cont_del_id"] = cont_id
        contenedor = ContenedorService.obtener_por_id(cont_id)
        if not contenedor:
            await reply_text(update, "❌ Contenedor no encontrado.")
            return MENU
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, borrar", callback_data="cont:delok"),
             InlineKeyboardButton("↩️ Cancelar", callback_data="cont:cancel")]
        ])
        await reply_html(
            update,
            f"⚠️ <b>Confirmar eliminación</b>\n\n"
            f"Vas a borrar: <code>{contenedor['nombre']}</code>\n"
            f"Esta acción no se puede deshacer.",
            reply_markup=kb
        )
        return CONFIRM_DELETE
    
    if data == "cont:delok":
        from utils.telegram_helpers import reply_text
        
        cont_id = context.user_data.get("cont_del_id")
        if cont_id is None:
            await reply_text(update, "❌ No hay elemento para eliminar.")
            await _render_list(update, context)
            return MENU
        try:
            ContenedorService.eliminar(int(cont_id))
            # Limpiar el ID de eliminación
            context.user_data.pop("cont_del_id", None)
            # Mostrar mensaje y luego la lista actualizada
            await reply_text(update, "🗑️ Contenedor eliminado correctamente.")
            await _render_list(update, context)
        except ValueError as e:
            await reply_text(update, f"❌ {e}")
            await _render_list(update, context)
        except Exception as e:
            logger.error(f"Error eliminando contenedor: {e}", exc_info=True)
            await reply_text(update, "❌ No se pudo eliminar. Intenta de nuevo.")
            await _render_list(update, context)
        return MENU
    
    if data == "cont:cancel":
        await _render_list(update, context)
        return MENU
    
    return MENU


@admin_only
async def crear_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nombre para crear un contenedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NOMBRE
    
    nombre = (update.message.text or "").strip()
    if not nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return CREAR_NOMBRE
    
    # Guardar el nombre en el contexto
    context.user_data["cont_nombre"] = nombre
    
    # Preguntar por número de contenedor
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_numero")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cont:cancel")]
    ])
    await reply_html(
        update,
        f"✅ Nombre: <b>{nombre}</b>\n\n"
        "Envía el <b>número de contenedor</b> (opcional):",
        reply_markup=kb
    )
    return CREAR_NUMERO


@admin_only
async def crear_numero_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el número de contenedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return CREAR_NUMERO
    
    numero = (update.message.text or "").strip()
    context.user_data["cont_numero"] = numero if numero else None
    
    # Preguntar si quiere asignar un proveedor
    proveedores = ProveedorService.listar()
    if not proveedores:
        # No hay proveedores, crear directamente
        return await _finalizar_creacion(update, context)
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, asignar proveedor", callback_data="cont:si_proveedor")],
        [InlineKeyboardButton("⏭️ Omitir", callback_data="cont:skip_proveedor")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cont:cancel")]
    ])
    
    numero_text = f"📦 Número: <b>{numero}</b>\n" if numero else ""
    await reply_html(
        update,
        f"✅ Nombre: <b>{context.user_data['cont_nombre']}</b>\n"
        f"{numero_text}\n"
        "¿Deseas asignar un <b>proveedor</b>?",
        reply_markup=kb
    )
    return CREAR_PROVEEDOR


@admin_only
async def crear_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de proveedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    logger.info(f"crear_proveedor_callback: data={data}")
    
    if data == "cont:skip_proveedor":
        context.user_data["cont_proveedor_id"] = None
        return await _finalizar_creacion(update, context)
    
    if data == "cont:cancel":
        await reply_text(update, "✅ Operación cancelada.")
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    
    if data == "cont:si_proveedor":
        # Mostrar lista de proveedores
        proveedores = ProveedorService.listar()
        if not proveedores:
            await reply_text(update, "❌ No hay proveedores disponibles. Creando contenedor sin proveedor.")
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
            InlineKeyboardButton("❌ Cancelar", callback_data="cont:cancel")
        ])
        kb = InlineKeyboardMarkup(keyboard)
        
        # Editar el mensaje si es un callback, o enviar uno nuevo
        if q:
            try:
                await q.edit_message_text(
                    "👥 <b>Selecciona un proveedor:</b>",
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except Exception as e:
                logger.error(f"Error editando mensaje: {e}")
                await reply_html(update, "👥 <b>Selecciona un proveedor:</b>", reply_markup=kb)
        else:
            await reply_html(update, "👥 <b>Selecciona un proveedor:</b>", reply_markup=kb)
        return CREAR_PROVEEDOR
    
    if data.startswith("cont:prov:"):
        try:
            prov_id = int(data.split(":")[-1])
            logger.info(f"Asignando proveedor {prov_id} al contenedor")
            context.user_data["cont_proveedor_id"] = prov_id
            return await _finalizar_creacion(update, context)
        except (ValueError, IndexError) as e:
            logger.error(f"Error parseando proveedor_id: {e}, data={data}")
            await reply_text(update, "❌ Error al procesar la selección del proveedor.")
            return CREAR_PROVEEDOR
    
    logger.warning(f"Callback no manejado en crear_proveedor_callback: {data}")
    return CREAR_PROVEEDOR


async def _finalizar_creacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finaliza la creación del contenedor con todos los datos."""
    from utils.telegram_helpers import reply_html, reply_text
    
    nombre = context.user_data.get("cont_nombre")
    numero = context.user_data.get("cont_numero")
    proveedor_id = context.user_data.get("cont_proveedor_id")
    
    logger.info(f"_finalizar_creacion: nombre={nombre}, numero={numero}, proveedor_id={proveedor_id}")
    
    if not nombre:
        await reply_text(update, "❌ Error: No se encontró el nombre del contenedor.")
        return ConversationHandler.END
    
    try:
        resultado = ContenedorService.crear(nombre, numero, proveedor_id)
        
        # Construir mensaje de confirmación
        msg = f"✅ <b>Contenedor Creado</b>\n\n"
        msg += f"📦 Nombre: <code>{nombre}</code>\n"
        if numero:
            msg += f"🔢 Número: <code>{numero}</code>\n"
        if proveedor_id:
            proveedor = ProveedorService.obtener_por_id(proveedor_id)
            if proveedor:
                msg += f"👥 Proveedor: <code>{proveedor['name']}</code>\n"
        
        # Si es un callback, editar el mensaje, sino enviar uno nuevo
        q = update.callback_query
        if q:
            try:
                await q.edit_message_text(msg, parse_mode="HTML")
                await reply_html(update, "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb())
            except Exception as e:
                logger.error(f"Error editando mensaje en _finalizar_creacion: {e}")
                await reply_html(update, msg)
                await reply_html(update, "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb())
        else:
            await reply_html(update, msg)
            await reply_html(update, "¿Qué deseas hacer ahora?", reply_markup=_main_menu_kb())
        
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un contenedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        # Limpiar y volver al inicio
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error creando contenedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al crear. Intenta nuevamente.")
        # Limpiar datos
        for key in ["cont_nombre", "cont_numero", "cont_proveedor_id"]:
            context.user_data.pop(key, None)
        return ConversationHandler.END


@admin_only
async def edit_nombre_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo nombre para editar un contenedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    cont_id = context.user_data.get("cont_edit_id")
    if cont_id is None:
        await reply_text(update, "❌ No hay contenedor en edición.")
        return MENU
    
    nuevo_nombre = (update.message.text or "").strip()
    if not nuevo_nombre:
        await reply_text(update, "❌ El nombre no puede estar vacío. Envía un nombre válido.")
        return EDIT_NOMBRE
    
    try:
        ContenedorService.actualizar(int(cont_id), nuevo_nombre=nuevo_nombre)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo nombre: <code>{nuevo_nombre}</code>"
        )
        context.user_data.pop("cont_edit_id", None)
        await _render_list(update, context)
        return MENU
    except ValueError as e:
        if "UNIQUE" in str(e) or "ya existe" in str(e).lower():
            await reply_text(update, "⚠️ Ya existe un contenedor con ese nombre. Usa otro nombre.")
        else:
            await reply_text(update, f"❌ {e}")
        return EDIT_NOMBRE
    except Exception as e:
        logger.error(f"Error actualizando contenedor: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NOMBRE


@admin_only
async def edit_numero_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el nuevo número de contenedor."""
    from utils.telegram_helpers import reply_html, reply_text
    
    if not update.message:
        return MENU
    
    cont_id = context.user_data.get("cont_edit_id")
    if cont_id is None:
        await reply_text(update, "❌ No hay contenedor en edición.")
        return MENU
    
    nuevo_numero = (update.message.text or "").strip()
    
    try:
        ContenedorService.actualizar(int(cont_id), numero_contenedor=nuevo_numero if nuevo_numero else None)
        await reply_html(
            update,
            f"✅ <b>Actualizado</b>\n\nNuevo número: <code>{nuevo_numero if nuevo_numero else 'Eliminado'}</code>"
        )
        context.user_data.pop("cont_edit_id", None)
        await _render_list(update, context)
        return MENU
    except Exception as e:
        logger.error(f"Error actualizando número: {e}", exc_info=True)
        await reply_text(update, "❌ Ocurrió un error al actualizar. Intenta nuevamente.")
        return EDIT_NUMERO


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual."""
    from utils.telegram_helpers import reply_text
    
    # Limpiar todos los datos de la conversación
    keys_to_remove = [
        "cont_nombre", "cont_numero", "cont_proveedor_id",
        "cont_edit_id", "cont_del_id"
    ]
    for key in keys_to_remove:
        context.user_data.pop(key, None)
    
    await reply_text(update, "✅ Operación cancelada.")
    return ConversationHandler.END


# ConversationHandler exportable
contenedores_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("contenedores", contenedores_entry),
        CallbackQueryHandler(contenedores_entry, pattern=r"^menu:contenedores$"),
    ],
    states={
        MENU: [
            CallbackQueryHandler(menu_callback, pattern=r"^cont:.*"),
        ],
        CREAR_NOMBRE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_nombre_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(create|back|close|cancel)$"),
        ],
        CREAR_NUMERO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, crear_numero_receive),
            CallbackQueryHandler(menu_callback, pattern=r"^cont:(skip_numero|cancel)$"),
        ],
        CREAR_PROVEEDOR: [
            CallbackQueryHandler(crear_proveedor_callback, pattern=r"^cont:(si_proveedor|skip_proveedor|prov:\d+|cancel)$"),
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
    name="contenedores_conversation",
    persistent=False,
)

