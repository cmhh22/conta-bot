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


# handlers/contabilidad.py (Add at the end)

async def set_tasa_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Set the USD to CUP exchange rate.
    Usage: /set_tasa 1 [cup_rate]
    """
    # Use config_vars (cfg) as the source of truth for the exchange rate

    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    try:
        if len(context.args) != 2 or context.args[0] != '1':
            raise ValueError("Missing arguments or invalid format. Usage: /set_tasa 1 [cup_rate] (e.g., /set_tasa 1 410)")
        
        tasa_str = context.args[1]
        try:
            nueva_tasa = float(tasa_str)
            if nueva_tasa <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: The rate must be a positive number.")
            return

        # 1. Update the centralized rate in config_vars
        cfg.TASA_USD_CUP = nueva_tasa

        # 2. Notify the user
        await update.message.reply_html(
            f"✅ <b>Exchange Rate Updated</b>\n\n"
            f"New Rate: <b>1 USD = {cfg.TASA_USD_CUP:.2f} CUP</b>"
        )
        logger.info(f"Exchange rate updated to 1 USD = {cfg.TASA_USD_CUP} CUP by {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Format error:</b> {e}\n"
            "Correct usage: <code>/set_tasa 1 [cup_rate]</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /set_tasa: {e}")
        await update.message.reply_text("An unexpected error occurred while setting the rate.")
        

async def ingreso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /ingreso command."""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
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
            await update.message.reply_text("Error: The amount must be a positive number.")
            return

        if moneda not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Invalid currency '{moneda}'. Use: {', '.join(VALID_MONEDAS)}")
            return
            
        if caja not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Invalid cash box '{caja}'. Use: {', '.join(VALID_CAJAS)}")
            return

        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()
        fecha_actual = datetime.now()
        
        cursor.execute(
            "INSERT INTO Movimientos (fecha, tipo, monto, moneda, caja, user_id, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fecha_actual, 'ingreso', monto, moneda, caja, user_id, "Income") # Add "Income" as description
        )
        
        conn.commit()
        conn.close()

        await update.message.reply_html(
            f"✅ <b>Income recorded!</b>\n\n"
            f"<b>Amount:</b> {monto:.2f} {moneda.upper()}\n"
            f"<b>Cash Box:</b> {caja.upper()}"
        )
        logger.info(f"Income recorded: {monto} {moneda} in {caja} by {user_id}")

    except ValueError:
        await update.message.reply_html(
            "<b>Format error.</b>\n"
            "Correct usage: <code>/ingreso [amount] [currency] [cash_box]</code>\n"
            "Example: <code>/ingreso 100 usd cfg</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /ingreso: {e}")
        await update.message.reply_text("An unexpected error occurred.")
# ----------------------------------------------  
        
# --- PHASE 5: NEW FUNCTION FOR /gasto ---
# handlers/contabilidad.py (Replace full gasto_command function)

# --- PHASE 6 (FIXED): FUNCTION FOR /gasto (Expense movement) ---
async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Record an expense and validate enough balance in the cash box.
    Usage: /gasto [amount] [currency] [cash_box] [description...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    try:
        # 1. Capture and validate arguments (INSIDE try)
        if len(context.args) < 4:
            raise ValueError("Missing arguments. Usage: /gasto [amount] [currency] [cash_box] [description...]")

        monto_str = context.args[0]
        moneda = context.args[1].lower()
        caja = context.args[2].lower()
        descripcion = " ".join(context.args[3:])
        
        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: The amount must be a positive number.")
            return

        if moneda not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Invalid currency ({moneda}).")
            return
        
        if caja not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Invalid cash box ({caja}).")
            return

        # 2. Open connection and run operations
        with get_db_connection() as conn:
            
            # 🌟 KEY FIX: Negative balance check 🌟
            # 'caja' and 'moneda' are now defined here
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja, moneda)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Insufficient balance</b> in cash box {caja.upper()} ({moneda.upper()}). "
                    f"Available: {saldo_actual:.2f} {moneda.upper()}."
                )
                return

            # 3. Record movement (Expense)
            MovimientoManager.registrar_movimiento(
                conn, 'gasto', monto, moneda, caja, user_id, descripcion
            )
        
        await update.message.reply_html(
            f"💸 <b>Expense Recorded!</b>\n\n"
            f"<b>Amount:</b> -{monto:.2f} {moneda.upper()} from {caja.upper()}\n"
            f"<b>Description:</b> {descripcion}"
        )
        logger.info(f"Expense of {monto} {moneda} in {caja} recorded by {user_id}")

    except ValueError as e:
        # This catch now only handles argument format errors
        # Ensures format error message shows relevant variables
        await update.message.reply_html(
            f"<b>Format error:</b> {e}\n"
            "Correct usage: <code>/gasto [amount] [currency] [cash_box] [description...]</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /gasto: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while recording the expense.")
        
        
# --- PHASE 6: NEW FUNCTION FOR /balance ---
async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /balance command."""
    user_id = update.effective_user.id

    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return
    
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. The "magic" SQL query
        # Add all 'ingreso' and subtract (ELSE -monto) all 'gasto'
        # Grouped by cash box and currency
        cursor.execute("""
            SELECT caja, moneda, SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE -monto END) as total
            FROM Movimientos
            GROUP BY caja, moneda
            ORDER BY caja, moneda
        """)
        
        resultados = cursor.fetchall() # Gets all rows (e.g., [('cfg', 'usd', 100.0), ('cfg', 'cup', 5000.0)])
        conn.close()

        if not resultados:
            await update.message.reply_text("There are no recorded movements yet.")
            return

        # 2. Format response
        respuesta = "--- 📊 Overall Balance ---\n\n"
        
        balances_por_caja = {} # Use a dictionary for grouping
        
        # Group results by cash box
        for caja, moneda, total in resultados:
            if caja not in balances_por_caja:
                balances_por_caja[caja] = []
            
            # Save formatted currency text
            balances_por_caja[caja].append(f"  • {total:,.2f} {moneda.upper()}")

        # 3. Build final text
        for caja, lineas in balances_por_caja.items():
            respuesta += f"<b>CASH BOX: {caja.upper()}</b>\n"
            respuesta += "\n".join(lineas) # Join all lines for this cash box
            respuesta += "\n\n" # Add spacing before the next cash box

        await update.message.reply_html(respuesta)

    except Exception as e:
        logger.error(f"Unexpected error in /balance: {e}")
        await update.message.reply_text("An unexpected error occurred while calculating the balance.")
# ----------------------------------------------

# --- PHASE 7 (REFACTORED): FUNCTION FOR /cambio (Automatic conversion) ---
# --- PHASE 7 (FIXED): FUNCTION FOR /cambio (Transfer between cash boxes) ---
async def cambio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Record a cash transfer between cash boxes, acting as origin expense and destination income.
    Usage: /cambio [amount] [origin_currency] [origin_cash_box] [destination_currency] [destination_cash_box] [reason...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    try:
        # 1. Capture and validate arguments (INSIDE try)
        if len(context.args) < 6:
            raise ValueError("Missing arguments. Usage: /cambio [amount] [origin_currency] [origin_cash_box] [destination_currency] [destination_cash_box] [reason...]")

        monto_str = context.args[0]
        moneda_origen = context.args[1].lower()
        caja_origen = context.args[2].lower()
        moneda_destino = context.args[3].lower()
        caja_destino = context.args[4].lower()
        motivo = " ".join(context.args[5:])

        # Variable validations
        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: The amount must be a positive number.")
            return

        if moneda_origen not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Invalid origin currency ({moneda_origen}).")
            return
        
        if caja_origen not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Invalid origin cash box ({caja_origen}).")
            return

        if moneda_destino not in VALID_MONEDAS:
            await update.message.reply_text(f"Error: Invalid destination currency ({moneda_destino}).")
            return

        if caja_destino not in VALID_CAJAS:
            await update.message.reply_text(f"Error: Invalid destination cash box ({caja_destino}).")
            return
        
        if caja_origen == caja_destino and moneda_origen == moneda_destino:
            await update.message.reply_html("⛔ Error: Origin and destination cash box/currency cannot be the same for a transfer.")
            return

        # 2. Open connection and run operations
        with get_db_connection() as conn:
            
            # 🌟 KEY FIX: Negative balance check 🌟
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja_origen, moneda_origen)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Insufficient balance</b> in origin cash box {caja_origen.upper()} ({moneda_origen.upper()}). "
                    f"Available: {saldo_actual:.2f} {moneda_origen.upper()}. Transfer could not be completed."
                )
                return

            # 3. Record expense movement (type='traspaso', origin expense)
            MovimientoManager.registrar_movimiento(
                conn, 'traspaso', monto, moneda_origen, caja_origen, user_id, 
                f"TRANSFER (Expense): To {caja_destino.upper()}/{moneda_destino.upper()} - Reason: {motivo}"
            )

            # 4. Calculate amount in destination currency
            if moneda_origen == moneda_destino:
                monto_destino = monto
            else:
                tasa = cfg.TASA_USD_CUP # Centralized rate in config_vars.py

                if moneda_origen == 'usd' and moneda_destino in ['cup', 'cup-t']:
                    monto_destino = monto * tasa
                elif moneda_destino == 'usd' and moneda_origen in ['cup', 'cup-t']:
                    monto_destino = monto / tasa
                else: # Conversion between CUP and CUP-T is 1:1, but register if cash box changes
                    monto_destino = monto

            # 5. Record income movement (type='traspaso', destination income)
            MovimientoManager.registrar_movimiento(
                conn, 'traspaso', monto_destino, moneda_destino, caja_destino, user_id, 
                f"TRANSFER (Income): From {caja_origen.upper()}/{moneda_origen.upper()} - Reason: {motivo}"
            )
        
        # 6. Confirmation message
        await update.message.reply_html(
            f"✅ <b>Transfer Recorded!</b>\n\n"
            f"<b>Origin:</b> -{monto:.2f} {moneda_origen.upper()} from {caja_origen.upper()}\n"
            f"<b>Destination:</b> +{monto_destino:.2f} {moneda_destino.upper()} to {caja_destino.upper()}\n"
            f"<b>Reason:</b> {motivo}"
        )
        logger.info(f"Transfer from {monto} {moneda_origen} to {monto_destino} {moneda_destino} recorded by {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Format or validation error:</b> {e}\n"
            "Correct usage: <code>/cambio [amount] [origin_currency] [origin_cash_box] [destination_currency] [destination_cash_box] [reason...]</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /cambio: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while recording the transfer.")
        
async def pago_vendedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Record a seller payment (settling an ACCOUNTS RECEIVABLE debt) and add amount to cash box.
    Usage: /pago_vendedor [seller] [amount] [currency] [cash_box] [note...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    try:
        if len(context.args) < 4:
            raise ValueError("Missing arguments. Usage: /pago_vendedor [seller] [amount] [currency] [cash_box] [note...]")

        vendedor = context.args[0].upper()
        monto_str = context.args[1]
        moneda = context.args[2].lower()
        caja = context.args[3].lower()
        nota = " ".join(context.args[4:])

        try:
            monto = float(monto_str)
            if monto <= 0: raise ValueError()
        except ValueError:
            await update.message.reply_text("Error: The amount must be a positive number.")
            return

        if moneda not in VALID_MONEDAS:
            raise ValueError(f"Invalid currency: {moneda}. Use one of: {', '.join(VALID_MONEDAS)}")
        if caja not in VALID_CAJAS:
            raise ValueError(f"Invalid cash box: {caja.upper()}. Use one of: {', '.join(VALID_CAJAS).upper()}")

        # ⭐️ CRITICAL USE OF CONTEXT MANAGER ⭐️
        with get_db_connection() as conn:
            
            # 1. Reduce seller debt (POR_COBRAR)
            # The manager handles currency conversion to USD for settlement calculation.
            monto_liquidado_usd = DeudaManager.liquidar_deuda_con_pago(
                conn=conn, 
                actor_id=vendedor, 
                monto_pagado=monto, 
                moneda_pago=moneda,
                tasa_cambio=cfg.TASA_USD_CUP
            )
            
            # 2. Record income in cash box
            MovimientoManager.registrar_movimiento(
                conn=conn,
                tipo='ingreso',
                monto=monto,
                moneda=moneda,
                caja=caja,
                user_id=user_id,
                descripcion=f"SELLER PAYMENT: {vendedor}. Settled debt for {monto_liquidado_usd:.2f} USD. Note: {nota}"
            )
            
        await update.message.reply_html(
            f"✅ <b>Payment Recorded!</b>\n\n"
            f"<b>Seller:</b> {vendedor}\n"
            f"<b>Income in cash box {caja.upper()}:</b> +{monto:.2f} {moneda.upper()}\n"
            f"<b>ACCOUNTS RECEIVABLE debt settled (USD):</b> {monto_liquidado_usd:.2f} USD"
        )

        logger.info(f"Payment from {vendedor} recorded by {user_id}")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Format or validation error:</b> {e}\n"
            "Correct usage: <code>/pago_vendedor [seller] [amount] [currency] [cash_box] [note...]</code>"
        )
    except Exception as e:
        logger.error(f"Unexpected error in /pago_vendedor: {e}")
        await update.message.reply_text("An unexpected error occurred while recording the payment.")
        
            
# --- PHASE 12 (FIXED): FUNCTION FOR /pago_proveedor (Supplier payment) ---
# handlers/contabilidad.py (Replace complete function)

# --- PHASE 12 (FIXED): FUNCTION FOR /pago_proveedor (Supplier payment) ---
async def pago_proveedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Record a supplier payment (expense) and reduce ACCOUNTS PAYABLE debt,
    preventing negative balances.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    # conn = None # No longer necessary to initialize conn=None

    try:
        if len(context.args) < 5:
            raise ValueError("Missing arguments. Usage: /pago_proveedor [supplier] [amount] [currency] [cash_box] [reason...]")

        # 1. Assign and validate arguments (outside with block)
        proveedor = context.args[0].upper()
        monto_str = context.args[1]
        moneda = context.args[2].lower()
        caja = context.args[3].lower()
        motivo = " ".join(context.args[4:])

        monto = float(monto_str)
        if monto <= 0: raise ValueError("Amount must be positive.")
        if moneda not in VALID_MONEDAS: raise ValueError(f"Invalid currency: {moneda}")
        if caja not in VALID_CAJAS: raise ValueError(f"Invalid cash box: {caja}")

        fecha_actual = datetime.now()
        descripcion = f"PAYMENT to Supplier: {proveedor} - Reason: {motivo}"

        # 2. Use context manager for connection (includes commit/rollback)
        with get_db_connection() as conn:
            
            # 🌟 2a. NEGATIVE BALANCE CHECK (KEY FIX) 🌟
            # Here MovimientoManager.get_saldo_caja has access to 'conn', 'caja' and 'moneda'
            saldo_actual = MovimientoManager.get_saldo_caja(conn, caja, moneda)
            
            if saldo_actual < monto:
                await update.message.reply_html(
                    f"⛔ <b>Insufficient balance</b> in cash box {caja.upper()} ({moneda.upper()}). "
                    f"Available: {saldo_actual:.2f} {moneda.upper()}. Payment could not be completed."
                )
                # Return exits function without commit.
                return
            
            # 2b. Record EXPENSE (Movements)
            # Use static method from MovimientoManager for clarity and consistency.
            MovimientoManager.registrar_movimiento(
                conn, 'gasto', monto, moneda, caja, user_id, descripcion
            )
            
            # 2c. DEBT ADJUSTMENT (Improved logic)
            rows_updated = DeudaManager.update_deuda(
                conn, proveedor, monto, moneda, 'POR_PAGAR', es_incremento=False
            )

        # 3. Improved confirmation (outside with block)
        if rows_updated > 0:
            mensaje_deuda = f"<b>Debt Updated:</b> Amount {monto:.2f} {moneda.upper()} subtracted from ACCOUNTS PAYABLE."
        else:
            mensaje_deuda = "<b>Notice:</b> No 'POR_PAGAR' debt found for this supplier."

        await update.message.reply_html(
            f"💸 <b>Supplier Payment Recorded!</b>\n\n"
            f"<b>Supplier:</b> {proveedor}\n"
            f"<b>Amount:</b> -{monto:.2f} {moneda.upper()} from {caja.upper()}\n"
            f"<b>Reason:</b> {motivo}\n"
            f"{mensaje_deuda}"
        )
        logger.info(f"Supplier payment {proveedor} recorded. Debt rows updated: {rows_updated}")

    except ValueError as e:
        # Ensure format error message shows relevant variables
        # It only shows e for validation exceptions (e.g., "Amount must be positive.")
        await update.message.reply_html(
            f"<b>Format or validation error:</b> {e}\n"
            "Correct usage: <code>/pago_proveedor [supplier] [amount] [currency] [cash_box] [reason...]</code>"
        )
    except Exception as e:
        # This captures any other unexpected error, including connection failures
        logger.error(f"Unexpected error in /pago_proveedor: {e}", exc_info=True)
        await update.message.reply_text("An unexpected error occurred while recording the payment.")
    # finally is no longer required when using get_db_connection
            

# --- PHASE 13 : FUNCTION FOR /deudas_command (Debt query) ---
async def deudas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display current balance of accounts payable (suppliers) and accounts receivable (sellers).
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    conn = None
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. Select all active debts (monto_pendiente > 0)
        cursor.execute("""
            SELECT actor_id, tipo, monto_pendiente, moneda
            FROM Deudas
            WHERE monto_pendiente > 0
            ORDER BY tipo DESC, moneda, actor_id
        """)
        
        resultados = cursor.fetchall()
        
        if not resultados:
            await update.message.reply_text("✅ There are no pending debts (accounts payable or receivable).")
            return

        # 2. Structure report
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

        # 3. Build final message
        respuesta = "📊 <b>PENDING DEBT STATUS</b> 📊\n\n"
        
        # --- A. ACCOUNTS PAYABLE (Suppliers) ---
        respuesta += "❌ <b>ACCOUNTS PAYABLE (Suppliers)</b>\n"
        if reporte_por_pagar:
            respuesta += reporte_por_pagar
            respuesta += "  --- TOTAL ACCOUNTS PAYABLE ---\n"
            for moneda, total in total_por_pagar.items():
                respuesta += f"  Total {moneda.upper()}: -{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>There are no pending supplier debts.</i>\n"
            
        respuesta += "\n"
        
        # --- B. ACCOUNTS RECEIVABLE (Sellers) ---
        respuesta += "✅ <b>ACCOUNTS RECEIVABLE (Sellers)</b>\n"
        if reporte_por_cobrar:
            respuesta += reporte_por_cobrar
            respuesta += "  --- TOTAL ACCOUNTS RECEIVABLE ---\n"
            for moneda, total in total_por_cobrar.items():
                respuesta += f"  Total {moneda.upper()}: +{total:,.2f} {moneda.upper()}\n"
        else:
            respuesta += "  <i>There are no pending seller debts.</i>\n"

        await update.message.reply_html(respuesta)

    except Exception as e:
        logger.error(f"Unexpected error in /deudas: {e}")
        await update.message.reply_text("An unexpected error occurred while generating the debt report.")
    finally:
        if conn:
            conn.close()


# --- PHASE 13: FUNCTION FOR /historial_command (Movement history) ---
async def historial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Show movement history from the database for the last N days.
    Usage: /historial [days] (e.g., /historial 30)
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    conn = None
    dias = 7  # Default value: last 7 days
    
    try:
        # 1. Parse number of days
        if context.args:
            try:
                dias = int(context.args[0])
                if dias <= 0: raise ValueError
            except ValueError:
                await update.message.reply_text("The number of days must be a positive integer.")
                return

        # 2. Calculate start date
        fecha_limite = datetime.now() - timedelta(days=dias)
        
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 3. Query movements within date range
        cursor.execute("""
            SELECT fecha, tipo, monto, moneda, caja, descripcion
            FROM Movimientos
            WHERE fecha >= ?
            ORDER BY fecha DESC
        """, (fecha_limite.strftime('%Y-%m-%d %H:%M:%S'),))
        
        movimientos = cursor.fetchall()
        
        if not movimientos:
            await update.message.reply_text(f"✅ No recorded movements were found in the last {dias} days.")
            return

        # 4. Build report
        reporte = f"⏳ <b>MOVEMENT HISTORY ({dias} days)</b> 📜\n\n"
        
        for fecha_str, tipo, monto, moneda, caja, descripcion in movimientos:
            
            # Amount formatting (add sign and color)
            simbolo = "+" if tipo in ('ingreso', 'pago') else "-"
            color = ""
            if tipo in ('ingreso', 'pago'):
                color = "🟢"
            elif tipo in ('gasto', 'pago_proveedor'):
                color = "🔴"
            else: # Others such as 'traspaso'
                color = "🔵"
            
            # Date formatting
            try:
                fecha_dt = datetime.strptime(fecha_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                fecha_formateada = fecha_dt.strftime('%d/%m %H:%M')
            except:
                fecha_formateada = fecha_str[:10]
            
            # Build movement line
            reporte += (
                f"{color} <code>{fecha_formateada}</code> | "
                f"<b>{simbolo}{monto:,.2f} {moneda.upper()}</b> en {caja.upper()}\n"
                f"  Type: {tipo.upper()} ({descripcion[:60]}...)\n"
            )

        await update.message.reply_html(reporte)
        logger.info(f"Historical report for {dias} days generated by {user_id}")

    except Exception as e:
        logger.error(f"Unexpected error in /historial: {e}")
        await update.message.reply_text("An unexpected error occurred while generating history.")
    finally:
        if conn:
            conn.close()
            
# --- PHASE 15: FUNCTION FOR /exportar_command (Export CSV) ---
async def exportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Export all rows from Movimientos table to a CSV file and send it. (RF11)
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ You don't have permission.")
        return

    conn = None
    csv_file_path = 'movimientos_export.csv'
    
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. Get all rows from Movimientos table
        cursor.execute("SELECT * FROM Movimientos ORDER BY fecha DESC")
        movimientos = cursor.fetchall()
        
        if not movimientos:
            await update.message.reply_text("There are no recorded movements to export.")
            return

        # 2. Get column names
        column_names = [description[0] for description in cursor.description]

        # 3. Write data to CSV file
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(column_names) # Write headers
            csv_writer.writerows(movimientos) # Write data

        # 4. Send file to user
        with open(csv_file_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=csv_file_path,
                caption="✅ Export Complete: All Accounting Movements."
            )
        
        logger.info(f"Movement export completed and sent to {user_id}")

    except Exception as e:
        logger.error(f"Unexpected error in /exportar: {e}")
        await update.message.reply_text("An unexpected error occurred while exporting data.")
    finally:
        if conn:
            conn.close()
        # Optional: remove local file after sending (for testing it's better to keep it)
        # os.remove(csv_file_path)