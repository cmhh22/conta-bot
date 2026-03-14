"""
Handlers refactorizados para comandos de inventario.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils.decorators import admin_only
from utils.validators import (
    validate_cantidad, validate_monto, validate_moneda, ValidationError
)
from services.cajas_service import CajaService
from utils.telegram_helpers import reply_html, reply_text
from services.inventario_service import InventarioService
from utils.currency import get_tasa

logger = logging.getLogger(__name__)


@admin_only
async def entrada_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra una entrada de mercancía."""
    try:
        if len(context.args) < 7:
            raise ValueError(
                "Faltan argumentos. Uso: /entrada [codigo] [cantidad] [costo_unitario] "
                "[moneda] [caja] [proveedor] [desc...]"
            )
        
        codigo = context.args[0].upper()
        cantidad = validate_cantidad(context.args[1])
        costo_unitario = validate_monto(context.args[2])
        moneda_costo = validate_moneda(context.args[3])
        caja_nombre = context.args[4].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' no encontrada. Usa /cajas para ver las cajas disponibles.")
        # Nota: caja no se usa en registrar_entrada, solo se valida
        proveedor = context.args[5].upper()
        descripcion_extra = " ".join(context.args[6:])
        
        resultado = InventarioService.registrar_entrada(
            codigo, cantidad, costo_unitario, moneda_costo, proveedor
        )
        
        await reply_html(
            update,
            f"📦 <b>Entrada de Mercancía Registrada!</b>\n\n"
            f"<b>Código:</b> {codigo}\n"
            f"<b>Cantidad:</b> +{cantidad} unidades\n"
            f"<b>Costo Unitario:</b> {costo_unitario:.2f} {moneda_costo.upper()}\n"
            f"<b>Proveedor:</b> {proveedor}\n\n"
            f"💰 <b>DEUDA GENERADA:</b> {resultado['costo_total']:.2f} {moneda_costo.upper()} "
            f"añadidos a la Cuenta por Pagar con {proveedor}."
        )
        logger.info(f"Entrada de {cantidad} de {codigo} registrada")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Uso correcto: <code>/entrada [codigo] [cantidad] [costo_unitario] "
            "[moneda] [caja] [proveedor] [desc...]</code>\n"
            "Ejemplo: <code>/entrada HUEVOS 100 0.5 usd cfg PEDRO Lote 45</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /entrada: {e}", exc_info=True)
        await reply_text(update, "Ocurrió un error inesperado al registrar la entrada.")


@admin_only
async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el inventario actual."""
    try:
        productos = InventarioService.obtener_stock()
        
        if not productos:
            await reply_text(update, "El inventario está actualmente vacío (stock = 0).")
            return
        
        respuesta = "--- 📋 Inventario Actual (Costo Original) ---\n\n"
        total_valor_costo_por_moneda = {}
        
        for producto in productos:
            valor_costo_articulo = producto['stock'] * producto['costo_unitario']
            moneda_upper = producto['moneda_costo'].upper()
            
            if moneda_upper not in total_valor_costo_por_moneda:
                total_valor_costo_por_moneda[moneda_upper] = 0.0
            total_valor_costo_por_moneda[moneda_upper] += valor_costo_articulo
            
            respuesta += (
                f"📦 <b>{producto['codigo']}</b> ({producto['nombre']})\n"
                f"  • Stock: {producto['stock']:,.0f} unidades\n"
                f"  • Costo Unitario: {producto['costo_unitario']:,.2f} {moneda_upper}\n"
                f"  • Valor Total (Costo): {valor_costo_articulo:,.2f} {moneda_upper}\n\n"
            )
        
        respuesta += "--------------------------------------\n"
        respuesta += f"📊 <b>Resumen de Valor de Inventario:</b>\n"
        for moneda, total in total_valor_costo_por_moneda.items():
            respuesta += f"Total {moneda}: {total:,.2f} {moneda}\n"
        
        await reply_html(update, respuesta)
        
    except Exception as e:
        logger.error(f"Error inesperado en /stock: {e}", exc_info=True)
        await reply_text(update, "Ocurrió un error inesperado al generar el reporte de stock.")


@admin_only
async def venta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Registra una venta."""
    try:
        if len(context.args) < 5:
            raise ValueError(
                "Faltan argumentos. Uso: /venta [código] [unidades] [monto_total] "
                "[moneda] [caja] [vendedor/nota...]"
            )
        
        codigo = context.args[0].upper()
        unidades = validate_cantidad(context.args[1])
        monto_total = validate_monto(context.args[2])
        moneda = validate_moneda(context.args[3])
        caja_nombre = context.args[4].lower().strip()
        caja = CajaService.obtener_por_nombre(caja_nombre)
        if not caja:
            raise ValueError(f"Caja '{caja_nombre}' no encontrada. Usa /cajas para ver las cajas disponibles.")
        caja_id = caja['id']
        nota = " ".join(context.args[5:]) if len(context.args) > 5 else "Venta estándar"
        user_id = update.effective_user.id
        
        # Intentar detectar si es venta consignada
        vendedor = None
        if len(context.args) > 5:
            posible_vendedor = context.args[5].upper()
            # Verificar si hay stock consignado
            stock_consignado = InventarioService.obtener_stock_consignado(posible_vendedor)
            for item in stock_consignado:
                if item['codigo'] == codigo and item['stock'] >= unidades:
                    vendedor = posible_vendedor
                    break
        
        if vendedor:
            # Venta consignada
            resultado = InventarioService.registrar_venta_consignada(
                codigo, unidades, monto_total, moneda, caja_id, vendedor, user_id, nota
            )
            
            await reply_html(
                update,
                f"✅ <b>Venta Consignada Liquidada!</b>\n\n"
                f"<b>Vendedor:</b> {vendedor}\n"
                f"<b>Producto:</b> {codigo} ({unidades} u.)\n"
                f"<b>Caja de Ingreso:</b> {caja['nombre'].upper()}\n"
                f"<b>Ingreso Total:</b> {monto_total:.2f} {moneda.upper()}\n"
                f"<b>Deuda Liquidada:</b> {resultado['monto_liquidado']:.2f} "
                f"{resultado['moneda_liquidacion'].upper()}"
            )
        else:
            # Venta estándar
            resultado = InventarioService.registrar_venta_estandar(
                codigo, unidades, monto_total, moneda, caja_id, user_id, nota
            )
            
            await reply_html(
                update,
                f"✅ <b>Venta Estándar Registrada!</b>\n\n"
                f"<b>Producto:</b> {codigo} ({unidades} u.)\n"
                f"<b>Caja de Ingreso:</b> {caja['nombre'].upper()}\n"
                f"<b>Ingreso Total:</b> {monto_total:.2f} {moneda.upper()}\n"
                f"<b>CMV (Costo):</b> {resultado['costo_total']:.2f} "
                f"{resultado['moneda_costo'].upper()}"
            )
        
        logger.info(f"Venta registrada: {codigo} x {unidades}")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Uso correcto: <code>/venta [código] [unidades] [monto_total] "
            "[moneda] [caja] [vendedor/nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /venta: {e}", exc_info=True)
        await reply_text(update, f"Ocurrió un error inesperado al registrar la venta: {str(e)}")


@admin_only
async def ganancia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Calcula y muestra el margen de ganancia bruta."""
    try:
        ganancias = InventarioService.calcular_ganancias()
        
        await reply_html(
            update,
            f"📈 <b>Reporte de Ganancia Bruta Acumulada</b>\n"
            f"<i>(Calculado usando Tasa Fija: 1 USD = {get_tasa()} CUP)</i>\n\n"
            f"💰 <b>Ingresos Totales por Ventas:</b> {ganancias['ingresos_total_usd']:,.2f} USD\n"
            f"🛒 <b>Costo Total de Ventas (CMV):</b> {ganancias['costos_total_usd']:,.2f} USD\n"
            f"--- \n"
            f"💵 <b>GANANCIA BRUTA ACUMULADA:</b> <b><u>{ganancias['margen_bruto_usd']:,.2f} USD</u></b>"
        )
        logger.info("Reporte de ganancias generado")
        
    except Exception as e:
        logger.error(f"Error inesperado en /ganancia: {e}", exc_info=True)
        await reply_text(update, "Ocurrió un error inesperado al calcular la ganancia.")


@admin_only
async def consignar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Consigna productos a un vendedor."""
    try:
        if len(context.args) < 6:
            raise ValueError(
                "Faltan argumentos. Uso: /consignar [codigo] [cantidad] [vendedor] "
                "[precio_venta] [moneda] [nota...]"
            )
        
        codigo = context.args[0].upper()
        cantidad = validate_cantidad(context.args[1])
        vendedor = context.args[2].upper()
        precio_venta = validate_monto(context.args[3])
        moneda = validate_moneda(context.args[4])
        nota_consignacion = " ".join(context.args[5:])
        
        resultado = InventarioService.consignar_producto(
            codigo, cantidad, vendedor, precio_venta, moneda
        )
        
        await reply_html(
            update,
            f"✅ <b>Consignación Registrada!</b>\n\n"
            f"<b>Vendedor:</b> {vendedor}\n"
            f"<b>Producto:</b> {codigo} ({cantidad} u.)\n"
            f"<b>Deuda Por Cobrar:</b> +{resultado['monto_deuda']:.2f} {moneda.upper()}"
        )
        logger.info(f"Consignación registrada: {codigo} para {vendedor}")
        
    except (ValueError, ValidationError) as e:
        await reply_html(
            update,
            f"<b>Error:</b> {e}\n"
            "Uso correcto: <code>/consignar [codigo] [cantidad] [vendedor] "
            "[precio_venta] [moneda] [nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /consignar: {e}", exc_info=True)
        await reply_text(update, f"Error al registrar la consignación: {str(e)}")


@admin_only
async def stock_consignado_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el stock consignado de un vendedor."""
    try:
        if not context.args:
            await reply_html(
                update,
                "<b>Error:</b> Debes especificar el nombre del vendedor.\n"
                "Uso: <code>/stock_consignado [vendedor]</code>"
            )
            return
        
        vendedor = context.args[0].upper()
        stock_items = InventarioService.obtener_stock_consignado(vendedor)
        
        reporte = f"📦 <b>STOCK CONSIGNADO PENDIENTE: {vendedor}</b> 📦\n\n"
        stock_total_pendiente = 0
        
        if stock_items:
            for item in stock_items:
                reporte += f"  • <b>{item['codigo']}</b>: {int(item['stock'])} unidades\n"
                stock_total_pendiente += item['stock']
        
        if stock_total_pendiente == 0:
            reporte += "  <i>El vendedor no tiene stock pendiente de liquidar.</i>"
        
        await reply_html(update, reporte)
        logger.info(f"Reporte de stock consignado para {vendedor} generado")
        
    except Exception as e:
        logger.error(f"Error inesperado en /stock_consignado: {e}", exc_info=True)
        await reply_text(update, "Ocurrió un error inesperado al generar el reporte de consignación.")

