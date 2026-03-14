"""
Handlers refactorizados para comandos de contabilidad.
Solo manejan la interaction con Telegram y delegan la logica a los servicios.
"""
import csv
import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from utils.decorators import admin_only
from utils.validators import (
    validate_monto, validate_moneda, validate_days, ValidationError
)
from services.cajas_service import CajaService
from utils.telegram_helpers import reply_html, reply_text
from services.contabilidad_service import ContabilidadService, DeudaService
from database.repositories import DeudaProductoRepository
from database.connection import get_db_connection
from core.config import TASA_USD_CUP

logger = logging.getLogger(__name__)


@admin_only
async def set_tasa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Establece la tasa de cambio USD a CUP."""
    try:
        if len(context.args) != 2 or context.args[0] != '1':
            raise ValueError("Formato incorrecto. Uso: /set_tasa 1 [tasa_cup]")
        
        nueva_tasa = validate_monto(context.args[1])
        
        # Update tasa global (temporal hasta implementar persistencia)
        import core.config as config
        config.TASA_USD_CUP = nueva_tasa
        
        await reply_html(
            update,
            f"✅ <b>Tasa de Cambio Actualizada</b>\n\n"
            f"Nueva Tasa: <b>1 USD = {nueva_tasa:.2f} CUP</b>"
        )
        logger.info(f"Tasa updated a 1 USD = {nueva_tasa} CUP")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/set_tasa 1 [tasa_cup]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /set_tasa: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred.")


@admin_only
async def ingreso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un ingreso. Si no tiene argumentos, inicia el formulario interactivo."""
    # Si no hay argumentos, el ConversationHandler se encargara de iniciar el formulario
    if not context.args or len(context.args) == 0:
        # El ConversationHandler manejara esto
        return
    
    try:
        if len(context.args) != 3:
            raise ValueError("Formato incorrecto. Uso: /ingreso [monto] [moneda] [caja]")
        
        monto = validate_monto(context.args[0])
        moneda = validate_moneda(context.args[1])
        caja_nombre = context.args[2].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' not found. Usa /cajas para ver las cajas disponibles.")
        caja_id = caja['id']
        user_id = update.effective_user.id
        
        resultado = ContabilidadService.registrar_ingreso(
            monto, moneda, caja_id, user_id
        )
        
        await reply_html(
            update,
            f"✅ <b>Ingreso recorded!</b>\n\n"
            f"<b>Monto:</b> {monto:.2f} {moneda.upper()}\n"
            f"<b>Caja:</b> {caja['nombre'].upper()}"
        )
        logger.info(f"Ingreso recorded: {monto} {moneda} en {caja['nombre']} por {user_id}")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/ingreso [monto] [moneda] [caja]</code>\n"
            "Ejemplo: <code>/ingreso 100 usd cfg</code>\n\n"
            "O usa <code>/ingreso</code> sin argumentos para el formulario interactivo."
        )
    except Exception as e:
        logger.error(f"Error inesperado en /ingreso: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred.")


@admin_only
async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un gasto."""
    try:
        if len(context.args) < 4:
            raise ValueError("Missing arguments. Usage: /gasto [monto] [moneda] [caja] [descripcion...]")
        
        monto = validate_monto(context.args[0])
        moneda = validate_moneda(context.args[1])
        caja_nombre = context.args[2].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' not found. Usa /cajas para ver las cajas disponibles.")
        caja_id = caja['id']
        descripcion = " ".join(context.args[3:])
        user_id = update.effective_user.id
        
        resultado = ContabilidadService.registrar_gasto(
            monto, moneda, caja_id, user_id, descripcion
        )
        
        await reply_html(
            update,
            f"💸 <b>Gasto Registrado!</b>\n\n"
            f"<b>Monto:</b> -{monto:.2f} {moneda.upper()} de {caja['nombre'].upper()}\n"
            f"<b>Description:</b> {descripcion}"
        )
        logger.info(f"Gasto de {monto} {moneda} en {caja['nombre']} recorded por {user_id}")
        
    except ValueError as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/gasto [monto] [moneda] [caja] [descripcion...]</code>"
        )
    except (ValidationError, Exception) as e:
        logger.error(f"Error inesperado en /gasto: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al registrar el gasto.")


@admin_only
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show el balance de todas las cajas."""
    try:
        balances = ContabilidadService.obtener_balance()
        
        if not balances:
            await reply_text(update, "No ningun movimiento recorded todavia.")
            return
        
        respuesta = "--- 📊 Balance General ---\n\n"
        
        for caja, monedas in balances.items():
            respuesta += f"<b>CAJA: {caja.upper()}</b>\n"
            for moneda, total in monedas.items():
                respuesta += f"  • {total:,.2f} {moneda.upper()}\n"
            respuesta += "\n"
        
        await reply_html(update, respuesta)
        
    except Exception as e:
        logger.error(f"Error inesperado en /balance: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al calcular el balance.")


@admin_only
async def cambio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un traspaso entre cajas."""
    try:
        if len(context.args) < 6:
            raise ValueError(
                "Missing arguments. Usage: /cambio [monto] [moneda_source] [caja_source] "
                "[moneda_destination] [caja_destination] [motivo...]"
            )
        
        monto = validate_monto(context.args[0])
        moneda_source = validate_moneda(context.args[1])
        caja_source_nombre = context.args[2].lower().strip()
        caja_source_obj = CajaService.obtener_por_nombre(caja_source_nombre)
        if not caja_source_obj:
            raise ValueError(f"Caja source '{caja_source_nombre}' not found.")
        caja_source_id = caja_source_obj['id']
        
        moneda_destination = validate_moneda(context.args[3])
        caja_destination_nombre = context.args[4].lower().strip()
        caja_destination_obj = CajaService.obtener_por_nombre(caja_destination_nombre)
        if not caja_destination_obj:
            raise ValueError(f"Caja destination '{caja_destination_nombre}' not found.")
        caja_destination_id = caja_destination_obj['id']
        
        motivo = " ".join(context.args[5:])
        user_id = update.effective_user.id
        
        resultado = ContabilidadService.registrar_traspaso(
            monto, moneda_source, caja_source_id, moneda_destination, caja_destination_id, user_id, motivo
        )
        
        await reply_html(
            update,
            f"✅ <b>Traspaso Registrado!</b>\n\n"
            f"<b>Origen:</b> -{resultado['monto_source']:.2f} {resultado['moneda_source'].upper()} "
            f"de {caja_source_obj['nombre'].upper()}\n"
            f"<b>Destino:</b> +{resultado['monto_destination']:.2f} {resultado['moneda_destination'].upper()} "
            f"a {caja_destination_obj['nombre'].upper()}\n"
            f"<b>Reason:</b> {motivo}"
        )
        logger.info(f"Traspaso recorded por {user_id}")
        
    except ValueError as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/cambio [monto] [moneda_source] [caja_source] "
            "[moneda_destination] [caja_destination] [motivo...]</code>"
        )
    except (ValidationError, Exception) as e:
        logger.error(f"Error inesperado en /cambio: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al registrar el traspaso.")


@admin_only
async def pago_vendedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra el pago de un vendedor."""
    try:
        if len(context.args) < 4:
            raise ValueError("Missing arguments. Usage: /pago_vendedor [vendedor] [monto] [moneda] [caja] [nota...]")
        
        vendedor = context.args[0].upper()
        monto = validate_monto(context.args[1])
        moneda = validate_moneda(context.args[2])
        caja_nombre = context.args[3].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' not found. Usa /cajas para ver las cajas disponibles.")
        caja_id = caja['id']
        nota = " ".join(context.args[4:]) if len(context.args) > 4 else ""
        user_id = update.effective_user.id
        
        # Liquidar deuda
        monto_liquidado_usd = DeudaService.liquidar_deuda_vendedor(vendedor, monto, moneda)
        
        # Registrar ingreso
        ContabilidadService.registrar_ingreso(
            monto, moneda, caja_id, user_id,
            f"PAGO VENDEDOR: {vendedor}. Liquido debt by {monto_liquidado_usd:.2f} USD. Nota: {nota}"
        )
        
        await reply_html(
            update,
            f"✅ <b>Pago Registrado!</b>\n\n"
            f"<b>Seller:</b> {vendedor}\n"
            f"<b>Ingreso en caja {caja['nombre'].upper()}:</b> +{monto:.2f} {moneda.upper()}\n"
            f"<b>Deuda POR COBRAR liquidada (USD):</b> {monto_liquidado_usd:.2f} USD"
        )
        logger.info(f"Pago de {vendedor} recorded por {user_id}")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/pago_vendedor [vendedor] [monto] [moneda] [caja] [nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /pago_vendedor: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al registrar el pago.")


@admin_only
async def pago_proveedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra un pago a proveedor."""
    try:
        if len(context.args) < 5:
            raise ValueError("Missing arguments. Usage: /pago_proveedor [proveedor] [monto] [moneda] [caja] [motivo...]")
        
        proveedor = context.args[0].upper()
        monto = validate_monto(context.args[1])
        moneda = validate_moneda(context.args[2])
        caja_nombre = context.args[3].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' not found. Usa /cajas para ver las cajas disponibles.")
        caja_id = caja['id']
        motivo = " ".join(context.args[4:])
        user_id = update.effective_user.id
        
        # Registrar gasto
        ContabilidadService.registrar_gasto(
            monto, moneda, caja_id, user_id, f"PAGO a Supplier: {proveedor} - Reason: {motivo}"
        )
        
        # Update deuda
        try:
            DeudaService.update_deuda(proveedor, monto, moneda, 'POR_PAGAR', es_incremento=False)
            mensaje_deuda = f"<b>Deuda Actualizada:</b> Monto {monto:.2f} {moneda.upper()} restado de POR PAGAR."
        except ValueError:
            mensaje_deuda = "<b>Notice:</b> Not found deuda 'POR PAGAR' para este proveedor."
        
        await reply_html(
            update,
            f"💸 <b>Pago a Supplier Registrado!</b>\n\n"
            f"<b>Supplier:</b> {proveedor}\n"
            f"<b>Monto:</b> -{monto:.2f} {moneda.upper()} de {caja['nombre'].upper()}\n"
            f"<b>Reason:</b> {motivo}\n"
            f"{mensaje_deuda}"
        )
        logger.info(f"Pago a Supplier {proveedor} recorded por {user_id}")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Correct usage: <code>/pago_proveedor [proveedor] [monto] [moneda] [caja] [motivo...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /pago_proveedor: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al registrar el pago.")


@admin_only
async def deudas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show el estado de pending debts."""
    try:
        deudas = DeudaService.obtener_deudas_pendientes()
        
        if not deudas['por_pagar'] and not deudas['por_cobrar']:
            await reply_text(update, "✅ No pending debts (por pagar o por cobrar).")
            return
        
        respuesta = "📊 <b>PENDING DEBT STATUS</b> 📊\n\n"
        
        # Cuentas por pagar
        respuesta += "❌ <b>CUENTAS POR PAGAR (Supplieres)</b>\n"
        if deudas['por_pagar']:
            totales_por_pagar = {}
            with get_db_connection() as conn:
                for deuda in deudas['por_pagar']:
                    actor_id = deuda['actor_id']
                    moneda = deuda['moneda']
                    monto_total = deuda['monto']
                    
                    # Obtener productos asociados a esta deuda
                    productos = DeudaProductoRepository.obtener_por_proveedor(conn, actor_id, moneda)
                    
                    respuesta += f"\n  🏢 <b>{actor_id}</b>: -{monto_total:,.2f} {moneda.upper()}\n"
                    
                    if productos:
                        respuesta += "    📦 <b>Merchandise:</b>\n"
                        for prod in productos:
                            codigo = prod['producto_codigo']
                            nombre = prod['producto_nombre']
                            cantidad = prod['cantidad']
                            costo_unit = prod['costo_unitario']
                            monto_prod = prod['monto_total']
                            respuesta += f"      • {codigo} - {nombre}\n"
                            respuesta += f"        Cantidad: {cantidad:.2f} | Costo: {costo_unit:.2f} {moneda.upper()} | Total: {monto_prod:.2f} {moneda.upper()}\n"
                    else:
                        respuesta += "    <i>Sin productos recordeds</i>\n"
                    
                    totales_por_pagar[moneda] = totales_por_pagar.get(moneda, 0) + monto_total
            
            respuesta += "\n  --- TOTALES POR PAGAR ---\n"
            for moneda, total in totales_por_pagar.items():
                respuesta += f"  Total {moneda.upper()}: -{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No deudas with supplieres pendientes.</i>\n"
        
        respuesta += "\n"
        
        # Cuentas por cobrar
        respuesta += "✅ <b>CUENTAS POR COBRAR (Selleres)</b>\n"
        if deudas['por_cobrar']:
            totales_por_cobrar = {}
            for deuda in deudas['por_cobrar']:
                respuesta += f"  • {deuda['actor_id']}: +{deuda['monto']:,.2f} {deuda['moneda'].upper()}\n"
                totales_por_cobrar[deuda['moneda']] = totales_por_cobrar.get(deuda['moneda'], 0) + deuda['monto']
            respuesta += "  --- TOTALES POR COBRAR ---\n"
            for moneda, total in totales_por_cobrar.items():
                respuesta += f"  Total {moneda.upper()}: +{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No deudas de vendedores pendientes.</i>\n"
        
        await reply_html(update, respuesta)
        
    except Exception as e:
        logger.error(f"Error inesperado en /deudas: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al generar el reporte de deudas.")


@admin_only
async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show el transaction history."""
    try:
        days = validate_days(context.args[0] if context.args else None)
        movimientos = ContabilidadService.obtener_historial(days)
        
        if not movimientos:
            await reply_text(update, f"✅ No se encontraron movimientos recordeds en los ultimos {days} days.")
            return
        
        reporte = f"⏳ <b>TRANSACTION HISTORY ({days} days)</b> 📜\n\n"
        
        for mov in movimientos:
            tipo = mov['tipo']
            simbolo = "+" if tipo in ('ingreso', 'venta') else "-"
            color = "🟢" if tipo in ('ingreso', 'venta') else "🔴" if tipo in ('gasto',) else "🔵"
            
            try:
                fecha_dt = datetime.strptime(mov['fecha'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                fecha_formateada = fecha_dt.strftime('%d/%m %H:%M')
            except:
                fecha_formateada = mov['fecha'][:10]
            
            reporte += (
                f"{color} <code>{fecha_formateada}</code> | "
                f"<b>{simbolo}{mov['monto']:,.2f} {mov['moneda'].upper()}</b> en {mov['caja'].upper()}\n"
                f"  Tipo: {tipo.upper()} ({mov['descripcion'][:60]}...)\n"
            )
        
        await reply_html(update, reporte)
        logger.info(f"Reporte historico de {days} days generado")
        
    except (ValueError, ValidationError) as e:
        await reply_text(update, f"Error: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en /historial: {e}", exc_info=True)
        await reply_text(update, "An unexpected error occurred al generar el historial.")


@admin_only
async def exportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu de opciones de exportacion."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = "💾 <b>Exportar Datos</b>\n\n"
    text += "Select the formato y tipo de datos a exportar:"
    
    keyboard = [
        [
            InlineKeyboardButton("📄 PDF - Movimientos", callback_data="export:movimientos:pdf"),
            InlineKeyboardButton("📊 Excel - Movimientos", callback_data="export:movimientos:excel"),
        ],
        [
            InlineKeyboardButton("📄 PDF - Inventario", callback_data="export:inventario:pdf"),
            InlineKeyboardButton("📊 Excel - Inventario", callback_data="export:inventario:excel"),
        ],
        [
            InlineKeyboardButton("📄 PDF - Deudas", callback_data="export:deudas:pdf"),
            InlineKeyboardButton("📊 Excel - Deudas", callback_data="export:deudas:excel"),
        ],
        [
            InlineKeyboardButton("📄 CSV - Movimientos", callback_data="export:movimientos:csv"),
        ],
        [
            InlineKeyboardButton("↩️ Back", callback_data="menu:main"),
        ],
    ]
    
    await reply_html(update, text, reply_markup=InlineKeyboardMarkup(keyboard))


@admin_only
async def export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks de exportacion."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from utils.exporters import (
        export_movimientos_pdf, export_movimientos_excel,
        export_inventario_pdf, export_inventario_excel,
        export_deudas_pdf, export_deudas_excel
    )
    from services.inventario_service import InventarioService
    from database.repositories import ProductoRepository
    from database.connection import get_db_connection
    
    q = update.callback_query
    if q:
        await q.answer()
    data = (q.data if q else "") or ""
    
    if not data.startswith("export:"):
        return
    
    try:
        parts = data.split(":")
        tipo = parts[1]  # movimientos, inventario, deudas
        formato = parts[2]  # pdf, excel, csv
        
        if tipo == "movimientos":
            movimientos = ContabilidadService.exportar_movimientos()
            if not movimientos:
                await reply_text(update, "❌ No movimientos para exportar.")
                return
            
            if formato == "pdf":
                filepath = export_movimientos_pdf(movimientos)
                caption = "✅ <b>Export PDF:</b> Movimientos Contables"
            elif formato == "excel":
                filepath = export_movimientos_excel(movimientos)
                caption = "✅ <b>Export Excel:</b> Movimientos Contables"
            elif formato == "csv":
                # Export CSV (mantener compatibilidad)
                csv_file_path = 'movimientos_export.csv'
                column_names = list(movimientos[0].keys())
                with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerow(column_names)
                    for mov in movimientos:
                        csv_writer.writerow([mov.get(col, '') for col in column_names])
                filepath = csv_file_path
                caption = "✅ <b>Export CSV:</b> Movimientos Contables"
            else:
                await reply_text(update, "❌ Formato no valid.")
                return
        
        elif tipo == "inventario":
            with get_db_connection() as conn:
                productos = ProductoRepository.obtener_todos(conn)
            productos_dict = [dict(prod) for prod in productos]
            
            if not productos_dict:
                await reply_text(update, "❌ No productos en el inventario.")
                return
            
            if formato == "pdf":
                filepath = export_inventario_pdf(productos_dict)
                caption = "✅ <b>Export PDF:</b> Inventario de Productos"
            elif formato == "excel":
                filepath = export_inventario_excel(productos_dict)
                caption = "✅ <b>Export Excel:</b> Inventario de Productos"
            else:
                await reply_text(update, "❌ Formato no valid.")
                return
        
        elif tipo == "deudas":
            deudas = DeudaService.obtener_deudas_pendientes()
            
            if not deudas.get('por_pagar') and not deudas.get('por_cobrar'):
                await reply_text(update, "❌ No deudas para exportar.")
                return
            
            if formato == "pdf":
                filepath = export_deudas_pdf(deudas)
                caption = "✅ <b>Export PDF:</b> Estado de Deudas"
            elif formato == "excel":
                filepath = export_deudas_excel(deudas)
                caption = "✅ <b>Export Excel:</b> Estado de Deudas"
            else:
                await reply_text(update, "❌ Formato no valid.")
                return
        
        else:
            await reply_text(update, "❌ Tipo de exportacion no valid.")
            return
        
        # Enviar archivo
        with open(filepath, 'rb') as f:
            if update.message:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption=caption,
                    parse_mode='HTML'
                )
            elif update.callback_query:
                await update.callback_query.message.reply_document(
                    document=f,
                    filename=os.path.basename(filepath),
                    caption=caption,
                    parse_mode='HTML'
                )
        
        logger.info(f"Export {formato.upper()} de {tipo} completada")
        
    except ImportError as e:
        error_msg = str(e)
        if "reportlab" in error_msg:
            await reply_text(
                update,
                "❌ Para exportar a PDF, instala reportlab:\n"
                "<code>pip install reportlab</code>"
            )
        elif "openpyxl" in error_msg:
            await reply_text(
                update,
                "❌ Para exportar a Excel, instala openpyxl:\n"
                "<code>pip install openpyxl</code>"
            )
        else:
            await reply_text(update, f"❌ Error: importacion: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en exportacion: {e}", exc_info=True)
        await reply_text(update, f"❌ An error occurred al exportar: {e}")

