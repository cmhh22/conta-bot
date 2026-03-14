import csv
import logging
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from settings import ADMIN_USER_IDS
from config_vars import VALID_MONEDAS, VALID_CAJAS
import config_vars as cfg


from .db_utils import (
    get_db_connection,
    DeudaManager,
    MovimientoManager
)

logger = logging.getLogger(__name__)


# handlers/contabilidad.py (Añadir al final)

async def set_tasa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Establece la tasa de cambio USD a CUP.
    Uso: /set_tasa 1 [tasa_cup]
    """
    # Usamos config_vars (cfg) como fuente de verdad para la tasa de cambio

    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        if len(context.args) != 2 or context.args[0] != '1':
            raise ValueError("Faltan argumentos o formato incorrecto. Uso: /set_tasa 1 [tasa_cup] (ej: /set_tasa 1 410)")
        
        tasa_str = context.args[1]
        try:
            nueva_tasa = float(tasa_str)
            if nueva_tasa <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: La tasa debe ser un número positivo.")
            return

        # 1. Actualizar la tasa centralizada en config_vars
        cfg.TASA_USD_CUP = nueva_tasa

        # 2. Notificar al usuario
        await update.message.reply_html(
            f"✅ <b>Tasa de Cambio Actualizada</b>\n\n"
            f"Nueva Tasa: <b>1 USD = {cfg.TASA_USD_CUP:.2f} CUP</b>"
        )
        logger.info(f"Tasa de cambio actualizada a 1 USD = {cfg.TASA_USD_CUP} CUP por {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Error de formato:</b> {e}\n"
            "Uso correcto: <code>/set_tasa 1 [tasa_cup]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /set_tasa: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al establecer la tasa.")
        

async def ingreso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /ingreso."""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        if len(context.args) != 3:
            raise ValueError("Formato incorrecto.")

        monto_str = context.args[0]
        moneda = context.args[1].lower()
        caja = context.args[2].lower()

        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: El monto debe ser un número positivo.")
            return

        if moneda not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Moneda '{moneda}' no válida. Usa: {', '.join(VALID_MONEDAS)}")
            return
            
        if caja not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Caja '{caja}' no válida. Usa: {', '.join(VALID_CAJAS)}")
            return

        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()
        fecha_actual = datetime.now()
        
        cursor.execute(
            "INSERT INTO Movimientos (fecha, tipo, monto, moneda, caja, user_id, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fecha_actual, 'ingreso', monto, moneda, caja, user_id, "Ingreso") # Añadimos "Ingreso" como descripción
        )
        
        conn.commit()
        conn.close()

        await update.message.reply_html(
            f"✅ <b>¡Ingreso registrado!</b>\n\n"
            f"<b>Monto:</b> {monto:.2f} {moneda.upper()}\n"
            f"<b>Caja:</b> {caja.upper()}"
        )
        logger.info(f"Ingreso registrado: {monto} {moneda} en {caja} por {user_id}")

    except ValueError:
        await update.message.reply_html(
            "<b>Error de formato.</b>\n"
            "Uso correcto: <code>/ingreso [monto] [moneda] [caja]</code>\n"
            "Ejemplo: <code>/ingreso 100 usd cfg</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /ingreso: {e}")
        await update.message.reply_text("Ocurrió un error inesperado.")
# ----------------------------------------------  
        
# --- FASE 5: NUEVA FUNCIÓN PARA /gasto ---
# handlers/contabilidad.py (Reemplazar la función gasto_command completa)

# --- FASE 6 (CORREGIDA): FUNCIÓN PARA /gasto (Movimiento de Egreso) ---
async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra un gasto y valida que haya saldo suficiente en la caja.
    Uso: /gasto [monto] [moneda] [caja] [descripcion...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        # 1. Capturar y validar argumentos (DENTRO del try)
        if len(context.args) < 4:
            raise ValueError("Faltan argumentos. Uso: /gasto [monto] [moneda] [caja] [descripcion...]")

        monto_str = context.args[0]
        moneda = context.args[1].lower()
        caja = context.args[2].lower()
        descripcion = " ".join(context.args[3:])
        
        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: El monto debe ser un número positivo.")
            return

        if moneda not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Moneda no válida ({moneda}).")
            return
        
        if caja not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Caja no válida ({caja}).")
            return

        # 2. Abrir conexión y realizar operaciones
        with get_db_connection() as conn:
            
            # 🌟 CORRECCIÓN CLAVE: Chequeo de Saldo Negativo 🌟
            # 'caja' y 'moneda' están ahora definidas aquí
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja, moneda)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Saldo insuficiente</b> en caja {caja.upper()} ({moneda.upper()}). "
                    f"Disponible: {saldo_actual:.2f} {moneda.upper()}."
                )
                return

            # 3. Registrar Movimiento (Gasto)
            MovimientoManager.registrar_movimiento(
                conn, 'gasto', monto, moneda, caja, user_id, descripcion
            )
        
        await update.message.reply_html(
            f"💸 <b>Gasto Registrado!</b>\n\n"
            f"<b>Monto:</b> -{monto:.2f} {moneda.upper()} de {caja.upper()}\n"
            f"<b>Descripción:</b> {descripcion}"
        )
        logger.info(f"Gasto de {monto} {moneda} en {caja} registrado por {user_id}")

    except ValueError as e:
        # Este catch ahora solo maneja errores de formato de argumentos
        # Se asegura de que el mensaje de error de formato muestre las variables relevantes
        await update.message.reply_html(
            f"<b>Error de formato:</b> {e}\n"
            "Uso correcto: <code>/gasto [monto] [moneda] [caja] [descripcion...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /gasto: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error inesperado al registrar el gasto.")
        
        
# --- FASE 6: NUEVA FUNCIÓN PARA /balance ---
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /balance."""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return
    
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. La consulta SQL "Mágica"
        # Suma todos los 'ingreso' y resta (ELSE -monto) todos los 'gasto'
        # Agrupados por caja y moneda
        cursor.execute("""
            SELECT caja, moneda, SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE -monto END) as total
            FROM Movimientos
            GROUP BY caja, moneda
            ORDER BY caja, moneda
        """)
        
        resultados = cursor.fetchall() # Obtiene todas las filas (ej: [('cfg', 'usd', 100.0), ('cfg', 'cup', 5000.0)])
        conn.close()

        if not resultados:
            await update.message.reply_text("No hay ningún movimiento registrado todavía.")
            return

        # 2. Formatear la respuesta
        respuesta = "--- 📊 Balance General ---\n\n"
        
        balances_por_caja = {} # Usamos un diccionario para agrupar
        
        # Agrupamos los resultados por caja
        for caja, moneda, total in resultados:
            if caja not in balances_por_caja:
                balances_por_caja[caja] = []
            
            # Guardamos el texto formateado de la moneda
            balances_por_caja[caja].append(f"  • {total:,.2f} {moneda.upper()}")

        # 3. Construimos el texto final
        for caja, lineas in balances_por_caja.items():
            respuesta += f"<b>CAJA: {caja.upper()}</b>\n"
            respuesta += "\n".join(lineas) # Unimos todas las líneas de esa caja
            respuesta += "\n\n" # Añadimos un espacio antes de la siguiente caja

        await update.message.reply_html(respuesta)

    except Exception as e:
        logger.error(f"Error inesperado en /balance: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al calcular el balance.")
# ----------------------------------------------

# --- FASE 7 (REFACTORIZADA): FUNCIÓN PARA /cambio (Conversión Automática) ---
# --- FASE 7 (CORREGIDA): FUNCIÓN PARA /cambio (Traspaso entre Cajas) ---
async def cambio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra un traspaso de efectivo entre cajas, actuando como gasto en origen e ingreso en destino.
    Uso: /cambio [monto] [moneda_origen] [caja_origen] [moneda_destino] [caja_destino] [motivo...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        # 1. Capturar y validar argumentos (DENTRO del try)
        if len(context.args) < 6:
            raise ValueError("Faltan argumentos. Uso: /cambio [monto] [moneda_origen] [caja_origen] [moneda_destino] [caja_destino] [motivo...]")

        monto_str = context.args[0]
        moneda_origen = context.args[1].lower()
        caja_origen = context.args[2].lower()
        moneda_destino = context.args[3].lower()
        caja_destino = context.args[4].lower()
        motivo = " ".join(context.args[5:])

        # Validaciones de variables
        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: El monto debe ser un número positivo.")
            return

        if moneda_origen not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Moneda de origen no válida ({moneda_origen}).")
            return
        
        if caja_origen not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Caja de origen no válida ({caja_origen}).")
            return

        if moneda_destino not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Moneda de destino no válida ({moneda_destino}).")
            return

        if caja_destino not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Caja de destino no válida ({caja_destino}).")
            return
        
        if caja_origen == caja_destino and moneda_origen == moneda_destino:
            await update.message.reply_html("⛔ Error: Las cajas y monedas de origen y destino no pueden ser iguales para un traspaso.")
            return

        # 2. Abrir conexión y realizar operaciones
        with get_db_connection() as conn:
            
            # 🌟 CORRECCIÓN CLAVE: Chequeo de Saldo Negativo 🌟
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja_origen, moneda_origen)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Saldo insuficiente</b> en caja de origen {caja_origen.upper()} ({moneda_origen.upper()}). "
                    f"Disponible: {saldo_actual:.2f} {moneda_origen.upper()}. No se pudo realizar el traspaso."
                )
                return

            # 3. Registrar Movimiento de Egreso (tipo='traspaso', gasto de origen)
            MovimientoManager.registrar_movimiento(
                conn, 'traspaso', monto, moneda_origen, caja_origen, user_id, 
                f"TRASPASO (Egreso): A {caja_destino.upper()}/{moneda_destino.upper()} - Motivo: {motivo}"
            )

            # 4. Calcular el monto en la moneda de destino
            if moneda_origen == moneda_destino:
                monto_destino = monto
            else:
                tasa = cfg.TASA_USD_CUP # Tasa centralizada en config_vars.py

                if moneda_origen == 'usd' and moneda_destino in ['cup', 'cup-t']:
                    monto_destino = monto * tasa
                elif moneda_destino == 'usd' and moneda_origen in ['cup', 'cup-t']:
                    monto_destino = monto / tasa
                else: # Conversión entre CUP y CUP-T es 1:1, pero se registra si hay cambio de caja
                    monto_destino = monto

            # 5. Registrar Movimiento de Ingreso (tipo='traspaso', ingreso en destino)
            MovimientoManager.registrar_movimiento(
                conn, 'traspaso', monto_destino, moneda_destino, caja_destino, user_id, 
                f"TRASPASO (Ingreso): Desde {caja_origen.upper()}/{moneda_origen.upper()} - Motivo: {motivo}"
            )
        
        # 6. Mensaje de confirmación
        await update.message.reply_html(
            f"✅ <b>Traspaso Registrado!</b>\n\n"
            f"<b>Origen:</b> -{monto:.2f} {moneda_origen.upper()} de {caja_origen.upper()}\n"
            f"<b>Destino:</b> +{monto_destino:.2f} {moneda_destino.upper()} a {caja_destino.upper()}\n"
            f"<b>Motivo:</b> {motivo}"
        )
        logger.info(f"Traspaso de {monto} {moneda_origen} a {monto_destino} {moneda_destino} registrado por {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/cambio [monto] [moneda_origen] [caja_origen] [moneda_destino] [caja_destino] [motivo...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /cambio: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error inesperado al registrar el traspaso.")
        
async def pago_vendedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra el pago de un vendedor (liquidando una deuda POR COBRAR) e ingresa el monto en caja.
    Uso: /pago_vendedor [vendedor] [monto] [moneda] [caja] [nota...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        if len(context.args) < 4:
            raise ValueError("Faltan argumentos. Uso: /pago_vendedor [vendedor] [monto] [moneda] [caja] [nota...]")

        vendedor = context.args[0].upper()
        monto_str = context.args[1]
        moneda = context.args[2].lower()
        caja = context.args[3].lower()
        nota = " ".join(context.args[4:])

        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: El monto debe ser un número positivo.")
            return

        if moneda not in VALID_MONEDAS:
            raise ValueError(f"Moneda no válida: {moneda}. Use una de: {', '.join(VALID_MONEDAS)}")
        if caja not in VALID_CAJAS:
            raise ValueError(f"Caja no válida: {caja.upper()}. Use una de: {', '.join(VALID_CAJAS).upper()}")

        # ⭐️ USO CRÍTICO DEL CONTEXT MANAGER ⭐️
        with get_db_connection() as conn:
            
            # 1. Reducir la deuda del vendedor (POR_COBRAR)
            # El manager se encarga de la conversión de moneda a USD para el cálculo de la liquidación.
            monto_liquidado_usd = DeudaManager.liquidar_deuda_con_pago(
                conn=conn, 
                actor_id=vendedor, 
                monto_pagado=monto, 
                moneda_pago=moneda,
                tasa_cambio=cfg.TASA_USD_CUP
            )
            
            # 2. Registrar el Ingreso en caja
            MovimientoManager.registrar_movimiento(
                conn=conn,
                tipo='ingreso',
                monto=monto,
                moneda=moneda,
                caja=caja,
                user_id=user_id,
                descripcion=f"PAGO VENDEDOR: {vendedor}. Liquidó deuda por {monto_liquidado_usd:.2f} USD. Nota: {nota}"
            )
            
        await update.message.reply_html(
            f"✅ <b>Pago Registrado!</b>\n\n"
            f"<b>Vendedor:</b> {vendedor}\n"
            f"<b>Ingreso en caja {caja.upper()}:</b> +{monto:.2f} {moneda.upper()}\n"
            f"<b>Deuda POR COBRAR liquidada (USD):</b> {monto_liquidado_usd:.2f} USD"
        )

        logger.info(f"Pago de {vendedor} registrado por {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/pago_vendedor [vendedor] [monto] [moneda] [caja] [nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /pago_vendedor: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al registrar el pago.")
        
            
# --- FASE 12 (CORREGIDA): FUNCIÓN PARA /pago_proveedor (Pago a Proveedor) ---
# handlers/contabilidad.py (Reemplazar la función completa)

# --- FASE 12 (CORREGIDA): FUNCIÓN PARA /pago_proveedor (Pago a Proveedor) ---
async def pago_proveedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra un pago a proveedor (gasto) y reduce la deuda POR PAGAR,
    previniendo saldos negativos.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    # conn = None # Ya no es necesario inicializar conn=None

    try:
        if len(context.args) < 5:
            raise ValueError("Faltan argumentos. Uso: /pago_proveedor [proveedor] [monto] [moneda] [caja] [motivo...]")

        # 1. Asignar y validar argumentos (fuera del bloque with)
        proveedor = context.args[0].upper()
        monto_str = context.args[1]
        moneda = context.args[2].lower()
        caja = context.args[3].lower()
        motivo = " ".join(context.args[4:])

        monto = float(monto_str)
        if monto <= 0: raise ValueError("El monto debe ser positivo.")
        if moneda not in VALID_MONEDAS: raise ValueError(f"Moneda no válida: {moneda}")
        if caja not in VALID_CAJAS: raise ValueError(f"Caja no válida: {caja}")

        fecha_actual = datetime.now()
        descripcion = f"PAGO a Proveedor: {proveedor} - Motivo: {motivo}"

        # 2. Utilizar el manejador de contexto para la conexión (incluye commit/rollback)
        with get_db_connection() as conn:
            
            # 🌟 2a. CHEQUEO DE SALDO NEGATIVO (CORRECCIÓN CLAVE) 🌟
            # Aquí MovimientoManager.get_saldo_caja tiene acceso a 'conn', 'caja' y 'moneda'
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja, moneda)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Saldo insuficiente</b> en caja {caja.upper()} ({moneda.upper()}). "
                    f"Disponible: {saldo_actual:.2f} {moneda.upper()}. No se pudo realizar el pago."
                )
                # El return sale de la función, sin hacer commit.
                return
            
            # 2b. Registro del GASTO (Movimientos)
            # Usamos el método estático de MovimientoManager para mayor claridad y consistencia.
            MovimientoManager.registrar_movimiento(
                conn, 'gasto', monto, moneda, caja, user_id, descripcion
            )
            
            # 2c. AJUSTE DE LA DEUDA (Lógica Mejorada)
            rows_updated = DeudaManager.actualizar_deuda(
                conn, proveedor, monto, moneda, 'POR_PAGAR', es_incremento=False
            )

        # 3. Confirmación mejorada (fuera del bloque with)
        if rows_updated > 0:
            mensaje_deuda = f"<b>Deuda Actualizada:</b> Monto {monto:.2f} {moneda.upper()} restado de POR PAGAR."
        else:
            mensaje_deuda = "<b>Aviso:</b> No se encontró deuda 'POR PAGAR' para este proveedor."

        await update.message.reply_html(
            f"💸 <b>Pago a Proveedor Registrado!</b>\n\n"
            f"<b>Proveedor:</b> {proveedor}\n"
            f"<b>Monto:</b> -{monto:.2f} {moneda.upper()} de {caja.upper()}\n"
            f"<b>Motivo:</b> {motivo}\n"
            f"{mensaje_deuda}"
        )
        logger.info(f"Pago a Proveedor {proveedor} registrado. Filas de deuda actualizadas: {rows_updated}")

    except ValueError as e:
        # Se asegura que el mensaje de error de formato muestre las variables relevantes
        # Solo mostrará e si es una de las excepciones de validación (ej. "El monto debe ser positivo.")
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/pago_proveedor [proveedor] [monto] [moneda] [caja] [motivo...]</code>"
        )
    except Exception as e:
        # Esto captura cualquier otro error inesperado, incluyendo si conn falla en conectarse
        logger.error(f"Error inesperado en /pago_proveedor: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error inesperado al registrar el pago.")
    # finally ya no es necesario si se usa get_db_connection
            

# --- FASE 13 : FUNCIÓN PARA /deudas_command (Consulta de Deudas) ---
async def deudas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra el saldo actual de las cuentas por pagar (proveedores) y por cobrar (vendedores).
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. Seleccionar todas las deudas activas (monto_pendiente > 0)
        cursor.execute("""
            SELECT actor_id, tipo, monto_pendiente, moneda
            FROM Deudas
            WHERE monto_pendiente > 0
            ORDER BY tipo DESC, moneda, actor_id
        """)
        
        resultados = cursor.fetchall()
        
        if not resultados:
            await update.message.reply_text("✅ No hay deudas pendientes (por pagar o por cobrar).")
            return

        # 2. Estructurar el reporte
        reporte_por_pagar = ""
        reporte_por_cobrar = ""
        total_por_pagar = {}
        total_por_cobrar = {}
        
        for actor_id, tipo, monto, moneda in resultados:
            moneda_upper = moneda.upper()
            
            if tipo == 'POR_PAGAR':
                reporte_por_pagar += f"  • {actor_id}: -{monto:,.2f} {moneda_upper}\n"
                total_por_pagar[moneda] = total_por_pagar.get(moneda, 0) + monto
            
            elif tipo == 'POR_COBRAR':
                reporte_por_cobrar += f"  • {actor_id}: +{monto:,.2f} {moneda_upper}\n"
                total_por_cobrar[moneda] = total_por_cobrar.get(moneda, 0) + monto

        # 3. Construir el mensaje final
        respuesta = "📊 <b>ESTADO DE DEUDAS PENDIENTES</b> 📊\n\n"
        
        # --- A. Cuentas POR PAGAR (Proveedores) ---
        respuesta += "❌ <b>CUENTAS POR PAGAR (Proveedores)</b>\n"
        if reporte_por_pagar:
            respuesta += reporte_por_pagar
            respuesta += "  --- TOTALES POR PAGAR ---\n"
            for moneda, total in total_por_pagar.items():
                respuesta += f"  Total {moneda.upper()}: -{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No hay deudas con proveedores pendientes.</i>\n"
            
        respuesta += "\n"
        
        # --- B. Cuentas POR COBRAR (Vendedores) ---
        respuesta += "✅ <b>CUENTAS POR COBRAR (Vendedores)</b>\n"
        if reporte_por_cobrar:
            respuesta += reporte_por_cobrar
            respuesta += "  --- TOTALES POR COBRAR ---\n"
            for moneda, total in total_por_cobrar.items():
                respuesta += f"  Total {moneda.upper()}: +{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>No hay deudas de vendedores pendientes.</i>\n"

        await update.message.reply_html(respuesta)

    except Exception as e:
        logger.error(f"Error inesperado en /deudas: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al generar el reporte de deudas.")
    finally:
        if conn:
            conn.close()


# --- FASE 13: FUNCIÓN PARA /historial_command ( Historial de Movimientos ) ---
async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra el historial de movimientos de la base de datos de los últimos N días.
    Uso: /historial [dias] (ej: /historial 30)
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    dias = 7  # Valor por defecto: últimos 7 días
    
    try:
        # 1. Parsear el número de días
        if context.args:
            try:
                dias = int(context.args[0])
                if dias <= 0: raise ValueError
            except ValueError:
                await update.message.reply_text("El número de días debe ser un entero positivo.")
                return

        # 2. Calcular la fecha de inicio
        fecha_limite = datetime.now() - timedelta(days=dias)
        
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 3. Consultar los movimientos dentro del rango de fechas
        cursor.execute("""
            SELECT fecha, tipo, monto, moneda, caja, descripcion
            FROM Movimientos
            WHERE fecha >= ?
            ORDER BY fecha DESC
        """, (fecha_limite.strftime('%Y-%m-%d %H:%M:%S'),))
        
        movimientos = cursor.fetchall()
        
        if not movimientos:
            await update.message.reply_text(f"✅ No se encontraron movimientos registrados en los últimos {dias} días.")
            return

        # 4. Construir el reporte
        reporte = f"⏳ <b>HISTORIAL DE MOVIMIENTOS ({dias} días)</b> 📜\n\n"
        
        for fecha_str, tipo, monto, moneda, caja, descripcion in movimientos:
            
            # Formateo de monto (añadir signo y color)
            simbolo = "+" if tipo in ('ingreso', 'pago') else "-"
            color = ""
            if tipo in ('ingreso', 'pago'):
                color = "🟢"
            elif tipo in ('gasto', 'pago_proveedor'):
                color = "🔴"
            else: # Otros como 'traspaso'
                color = "🔵"
            
            # Formateo de fecha
            try:
                fecha_dt = datetime.strptime(fecha_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                fecha_formateada = fecha_dt.strftime('%d/%m %H:%M')
            except:
                fecha_formateada = fecha_str[:10]
            
            # Construir la línea del movimiento
            reporte += (
                f"{color} <code>{fecha_formateada}</code> | "
                f"<b>{simbolo}{monto:,.2f} {moneda.upper()}</b> en {caja.upper()}\n"
                f"  Tipo: {tipo.upper()} ({descripcion[:60]}...)\n"
            )

        await update.message.reply_html(reporte)
        logger.info(f"Reporte histórico de {dias} días generado por {user_id}")

    except Exception as e:
        logger.error(f"Error inesperado en /historial: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al generar el historial.")
    finally:
        if conn:
            conn.close()
            
# --- FASE 15: FUNCIÓN PARA /exportar_command ( Exportar CSV ) ---
async def exportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Exporta todos los datos de la tabla Movimientos a un archivo CSV y lo envía. (RF11)
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    csv_file_path = 'movimientos_export.csv'
    
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. Obtener todos los datos de la tabla Movimientos
        cursor.execute("SELECT * FROM Movimientos ORDER BY fecha DESC")
        movimientos = cursor.fetchall()
        
        if not movimientos:
            await update.message.reply_text("No hay movimientos registrados para exportar.")
            return

        # 2. Obtener los nombres de las columnas
        column_names = [description[0] for description in cursor.description]

        # 3. Escribir los datos en el archivo CSV
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(column_names) # Escribir cabeceras
            csv_writer.writerows(movimientos) # Escribir datos

        # 4. Enviar el archivo al usuario
        with open(csv_file_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=csv_file_path,
                caption="✅ Exportación Completa: Todos los Movimientos Contables."
            )
        
        logger.info(f"Exportación de movimientos completada y enviada a {user_id}")

    except Exception as e:
        logger.error(f"Error inesperado en /exportar: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al exportar los datos.")
    finally:
        if conn:
            conn.close()
        # Opcional: limpiar el archivo local después de enviarlo (aunque para pruebas es mejor dejarlo)
        # os.remove(csv_file_path)