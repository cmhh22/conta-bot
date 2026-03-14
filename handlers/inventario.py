import logging
import sqlite3
import datetime
from telegram import Update
from telegram.ext import ContextTypes
# Asegúrate de importar los managers si los vas a usar
from .db_utils import MovimientoManager, DeudaManager, InventarioManager 
from settings import ADMIN_USER_IDS 
from config_vars import VALID_MONEDAS, VALID_CAJAS
import config_vars as cfg

logger = logging.getLogger(__name__)

# --- FASE 9 (MODIFICADA): FUNCIÓN PARA /entrada (Registro de Compra/Stock) ---

async def entrada_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra la entrada de mercancía, actualiza stock/costo y genera la deuda con el proveedor.
    Formato: /entrada [codigo] [cantidad] [costo_unitario] [moneda_costo] [caja] [proveedor] [descripcion]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    try:
        # Formato esperado: [código] [cantidad] [costo_unitario] [moneda_costo] [caja] [proveedor] [desc...]
        if len(context.args) < 7:
            raise ValueError("Faltan argumentos. Uso: /entrada [codigo] [cantidad] [costo_unitario] [moneda] [caja] [proveedor] [desc]")

        codigo = context.args[0].upper()
        cantidad = int(context.args[1])
        costo_unitario = float(context.args[2])
        moneda_costo = context.args[3].lower()
        caja = context.args[4].lower()
        
        # El proveedor será el actor de la deuda. Usamos .upper() para estandarizar.
        proveedor = context.args[5].upper() 
        descripcion_extra = " ".join(context.args[6:])
        
        # Validaciones
        if cantidad <= 0 or costo_unitario <= 0: raise ValueError("Cantidad y costo deben ser positivos.")
        if moneda_costo not in VALID_MONEDAS: raise ValueError(f"Moneda no válida: {moneda_costo}")
        if caja not in VALID_CAJAS: raise ValueError(f"Caja no válida: {caja}")

        fecha_actual = datetime.datetime.now()
        costo_total = cantidad * costo_unitario
        
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. 🌟 ACTUALIZAR / INSERTAR PRODUCTO (Tabla Productos)
        cursor.execute("SELECT stock, costo_unitario, moneda_costo FROM Productos WHERE codigo = ?", (codigo,))
        producto_existente = cursor.fetchone()

        if producto_existente:
            # Producto existe: Calcular nuevo costo promedio ponderado
            stock_anterior, costo_anterior, moneda_anterior = producto_existente
            
            # Nota: Esto asume que el nuevo costo unitario está en la misma moneda que el anterior.
            nuevo_stock = stock_anterior + cantidad
            costo_anterior_total = stock_anterior * costo_anterior
            nuevo_costo_total = costo_anterior_total + costo_total
            
            nuevo_costo_unitario = nuevo_costo_total / nuevo_stock if nuevo_stock > 0 else 0

            cursor.execute(
                "UPDATE Productos SET stock = ?, costo_unitario = ?, moneda_costo = ? WHERE codigo = ?",
                (nuevo_stock, nuevo_costo_unitario, moneda_costo, codigo)
            )
        else:
            # Producto nuevo: Insertar
            cursor.execute(
                "INSERT INTO Productos (codigo, nombre, costo_unitario, moneda_costo, stock) VALUES (?, ?, ?, ?, ?)",
                (codigo, codigo, costo_unitario, moneda_costo, cantidad)
            )
            
        # 2. REGISTRAR DEUDA (Tabla Deudas)
        # La entrada de mercancía genera una deuda POR PAGAR al proveedor.

        # Intentar actualizar una deuda existente (si existe, se suma el costo total)
        cursor.execute(
            """
            UPDATE Deudas 
            SET monto_pendiente = monto_pendiente + ?
            WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_PAGAR'
            """,
            (costo_total, proveedor, moneda_costo)
        )
        
        # Si no se actualizó ninguna fila (deuda nueva), insertamos la deuda
        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO Deudas (fecha, actor_id, tipo, monto_pendiente, moneda)
                VALUES (?, ?, 'POR_PAGAR', ?, ?)
                """,
                (fecha_actual, proveedor, costo_total, moneda_costo)
            )
            
        # 3. ELIMINADO: REGISTRO DE MOVIMIENTO. Ya no es necesario registrar un movimiento de caja 0,
        # la deuda se gestiona enteramente en la tabla Deudas.
            
        conn.commit()

        await update.message.reply_html(
            f"📦 <b>Entrada de Mercancía Registrada!</b>\n\n"
            f"<b>Código:</b> {codigo}\n"
            f"<b>Cantidad:</b> +{cantidad} unidades\n"
            f"<b>Costo Unitario:</b> {costo_unitario:.2f} {moneda_costo.upper()}\n"
            f"<b>Proveedor:</b> {proveedor}\n\n"
            f"💰 <b>DEUDA GENERADA:</b> {costo_total:.2f} {moneda_costo.upper()} añadidos a la Cuenta por Pagar con {proveedor}."
        )
        logger.info(f"Entrada de {cantidad} de {codigo} registrada por {user_id}. Deuda generada con {proveedor}.")

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/entrada [codigo] [cantidad] [costo_unitario] [moneda] [caja] [proveedor] [desc...]</code>\n"
            "Ejemplo: <code>/entrada HUEVOS 100 0.5 usd cfg PEDRO Lote 45</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /entrada: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al registrar la entrada.")
    finally:
        if conn:
            conn.close()

# --- FASE 9.5 (MODIFICADA): FUNCIÓN PARA /stock (Reporte de Inventario) ---
async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /stock: Muestra el inventario actual con la moneda de costo correcta."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # Seleccionamos todos los campos relevantes, incluyendo moneda_costo
        cursor.execute("""
            SELECT codigo, nombre, stock, costo_unitario, moneda_costo
            FROM Productos
            WHERE stock > 0
            ORDER BY codigo
        """)
        
        resultados = cursor.fetchall() 
        conn.close()

        if not resultados:
            await update.message.reply_text("El inventario está actualmente vacío (stock = 0).")
            return

        respuesta = "--- 📋 Inventario Actual (Costo Original) ---\n\n"
        
        # Diccionario para valorizar por moneda (opcional, para el resumen)
        total_valor_costo_por_moneda = {}

        for codigo, nombre, stock, costo_unitario, moneda_costo in resultados:
            
            valor_costo_articulo = stock * costo_unitario
            moneda_upper = moneda_costo.upper()
            
            # Acumular el valor total por moneda
            if moneda_upper not in total_valor_costo_por_moneda:
                total_valor_costo_por_moneda[moneda_upper] = 0.0
            total_valor_costo_por_moneda[moneda_upper] += valor_costo_articulo
            
            respuesta += (
                f"📦 <b>{codigo}</b> ({nombre})\n"
                f"  • Stock: {stock:,.0f} unidades\n"
                f"  • Costo Unitario: {costo_unitario:,.2f} {moneda_upper}\n" 
                f"  • Valor Total (Costo): {valor_costo_articulo:,.2f} {moneda_upper}\n\n"
            )

        respuesta += "--------------------------------------\n"
        respuesta += f"📊 <b>Resumen de Valor de Inventario:</b>\n"
        
        # Mostrar el resumen por cada moneda
        for moneda, total in total_valor_costo_por_moneda.items():
             respuesta += f"Total {moneda}: {total:,.2f} {moneda}\n"


        await update.message.reply_html(respuesta)

    except Exception as e:
        logger.error(f"Error inesperado en /stock: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al generar el reporte de stock.")

# --- FASE 10: FUNCIÓN PARA /venta (Ingreso y Consumo de Stock) - CORREGIDO ---

async def venta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Registra una venta, descontando stock general o liquidando stock consignado y deuda.
    Uso: /venta [código] [unidades] [monto_total] [moneda] [caja] [vendedor/nota...]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    try:
        if len(context.args) < 5:
            raise ValueError("Faltan argumentos. Uso: /venta [código] [unidades] [monto_total] [moneda] [caja] [vendedor/nota...]")

        codigo = context.args[0].upper()
        unidades = float(context.args[1])
        monto_total = float(context.args[2])
        moneda = context.args[3].lower()
        caja = context.args[4].lower() 
        
        # Validaciones básicas
        if unidades <= 0 or monto_total <= 0: raise ValueError("Unidades y monto total deben ser positivos.")
        if moneda not in VALID_MONEDAS: raise ValueError(f"Moneda no válida: {moneda}")
        if caja not in VALID_CAJAS: raise ValueError(f"Caja no válida: {caja}")

        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()
        fecha_actual = datetime.datetime.now()

        # 1. 🔍 Detección de tipo de venta (consignada o estándar)
        vendedor = None
        nota = " ".join(context.args[5:]) if len(context.args) > 5 else "Venta estándar"
        is_consignada = False

        if len(context.args) > 5:
            posible_vendedor = context.args[5].upper()
            # Verificamos si hay stock consignado para este vendedor
            cursor.execute("""
                SELECT stock FROM Consignaciones 
                WHERE codigo = ? AND vendedor = ? AND stock > 0
            """, (codigo, posible_vendedor))
            stock_consignado = cursor.fetchone()
            
            if stock_consignado and stock_consignado[0] >= unidades:
                vendedor = posible_vendedor
                is_consignada = True

        # 2. Procesamiento según tipo de venta
        if is_consignada:
            # --- VENTA CONSIGNADA ---
            logger.info(f"Procesando venta consignada para vendedor {vendedor}")
            
            # 🌟 CORRECCIÓN CLAVE: Seleccionar también la MONEDA 🌟
            cursor.execute("""
                SELECT stock, precio_unitario, moneda 
                FROM Consignaciones 
                WHERE codigo = ? AND vendedor = ?
            """, (codigo, vendedor))
            data_consignada = cursor.fetchone()
            
            if not data_consignada:
                raise ValueError("Error al obtener datos de consignación. Reintente.")
                
            stock_consignado_actual = data_consignada[0]
            precio_unitario_consignado = data_consignada[1]
            moneda_consignacion = data_consignada[2] # 🌟 NUEVA ASIGNACIÓN
            
            # Actualizar stock consignado
            nueva_cantidad_consignada = stock_consignado_actual - unidades
            cursor.execute("""
                UPDATE Consignaciones 
                SET stock = ? 
                WHERE codigo = ? AND vendedor = ?
            """, (nueva_cantidad_consignada, codigo, vendedor))

            # Liquidar deuda (en la moneda de la deuda consignada)
            monto_a_liquidar = unidades * precio_unitario_consignado
            cursor.execute("""
                UPDATE Deudas 
                SET monto_pendiente = CASE 
                    WHEN monto_pendiente - ? < 0 THEN 0 
                    ELSE monto_pendiente - ? 
                END
                WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'
            """, (monto_a_liquidar, monto_a_liquidar, vendedor, moneda_consignacion)) 
            
            # 🌟 CORRECCIÓN: Usar la nueva variable en la descripción
            descripcion_mov = (
                f"VENTA_CONSIGNADA: {unidades} x {codigo} | "
                f"Vendedor: {vendedor} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"DEUDA_LIQUIDADA: {monto_a_liquidar:.2f} {moneda_consignacion.upper()} | "
                f"CAJA: {caja} | "
                f"NOTA: {nota}"
            )

            mensaje_confirmacion = (
                f"✅ <b>Venta Consignada Liquidada!</b>\n\n"
                f"<b>Vendedor:</b> {vendedor}\n"
                f"<b>Producto:</b> {codigo} ({unidades} u.)\n"
                f"<b>Caja de Ingreso:</b> {caja.upper()}\n"
                f"<b>Ingreso Total:</b> {monto_total:.2f} {moneda.upper()}\n"
                f"<b>Deuda Liquidada:</b> {monto_a_liquidar:.2f} {moneda_consignacion.upper()}" # 🌟 USAR NUEVA VARIABLE
            )

        else:
            # --- VENTA ESTÁNDAR ---
            logger.info("Procesando venta estándar")
            
            # Verificar y actualizar stock general
            cursor.execute("SELECT stock, costo_unitario, moneda_costo FROM Productos WHERE codigo = ?", (codigo,))
            producto = cursor.fetchone()

            if not producto:
                raise ValueError(f"El producto {codigo} no existe en el inventario.")

            stock_actual = producto[0]
            if stock_actual < unidades:
                raise ValueError(f"Stock insuficiente en inventario general. Solo quedan {stock_actual} unidades de {codigo}.")

            costo_unitario = producto[1]
            moneda_costo = producto[2]

            # Actualizar stock
            nueva_cantidad = stock_actual - unidades
            cursor.execute("UPDATE Productos SET stock = ? WHERE codigo = ?", (nueva_cantidad, codigo))

            # Calcular el Costo de Mercancía Vendida (CMV)
            costo_total = unidades * costo_unitario
            
            # Usar formato estricto para el parser de /ganancia
            descripcion_mov = (
                f"VENTA: {unidades} x {codigo} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"CMV: {costo_total:.2f} {moneda_costo.upper()} | " 
                f"CAJA: {caja} | "
                f"NOTA: {nota}"
            )

            mensaje_confirmacion = (
                f"✅ <b>Venta Estándar Registrada!</b>\n\n"
                f"<b>Producto:</b> {codigo} ({unidades} u.)\n"
                f"<b>Caja de Ingreso:</b> {caja.upper()}\n"
                f"<b>Ingreso Total:</b> {monto_total:.2f} {moneda.upper()}\n"
                f"<b>CMV (Costo):</b> {costo_total:.2f} {moneda_costo.upper()}"
            )

        # Registrar el movimiento de ingreso de efectivo (tipo='venta')
        cursor.execute(
            "INSERT INTO Movimientos (fecha, tipo, monto, moneda, caja, user_id, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fecha_actual, 'venta', monto_total, moneda, caja, user_id, descripcion_mov)
        )

        conn.commit()
        await update.message.reply_html(mensaje_confirmacion)

    except ValueError as e:
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/venta [código] [unidades] [monto_total] [moneda] [caja] [vendedor/nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /venta: {e}", exc_info=True)
        await update.message.reply_text(f"Ocurrió un error inesperado al registrar la venta: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- FASE 11: FUNCIÓN PARA /ganancia (Reporte de Utilidad) - CORREGIDO ---

async def ganancia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Calcula y muestra el margen de ganancia bruta de las ventas registradas 
    desde el inicio de las operaciones.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS: 
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()

        # 1. Buscar todas las transacciones de VENTA (tipo='venta' es el tipo correcto)
        cursor.execute("""
            SELECT monto, moneda, descripcion 
            FROM Movimientos
            WHERE tipo = 'venta' 
        """)
        
        ventas = cursor.fetchall()
        conn.close()

        if not ventas:
            await update.message.reply_text("No se encontraron ventas registradas para calcular la ganancia.")
            return

        # 2. Inicializar acumuladores
        # Usaremos USD como moneda base para el resumen, aplicando la tasa de conversión.
        total_ingreso_usd = 0.0
        total_costo_usd = 0.0
        
        # 3. Procesar cada venta
        for monto_ingreso, moneda_ingreso, descripcion in ventas:
            
            # 3a. Convertir el Ingreso (Revenue) a USD (moneda base)
            ingreso_usd = monto_ingreso
            if moneda_ingreso in ('cup', 'cup-t'):
                # Si es CUP, lo dividimos por la tasa para llevarlo a USD
                ingreso_usd /= cfg.TASA_USD_CUP
                
            total_ingreso_usd += ingreso_usd

            # 3b. Extraer el Costo de la descripción (CMV)
            # 🌟 CORRECCIÓN: Usar el nuevo formato estricto: | CMV: X.XX MONEDA_COSTO |
            try:
                # Las ventas consignadas no tienen CMV que afecte la ganancia bruta general, 
                # ya que el costo (precio de consignación) se resta de la deuda POR COBRAR.
                if 'VENTA_CONSIGNADA' in descripcion:
                    continue 

                # Buscamos la etiqueta "CMV:"
                costo_start_tag = "CMV:"
                costo_start_index = descripcion.find(costo_start_tag)
                
                if costo_start_index != -1:
                    # Extraer la subcadena que contiene el valor y la moneda
                    # Busca el siguiente delimitador '|'
                    sub_string = descripcion[costo_start_index + len(costo_start_tag):].strip().split(' | ')[0]
                    
                    # Separar el valor del Costo y la moneda
                    costo_parts = sub_string.split()
                    costo_valor = float(costo_parts[0].replace(',', ''))
                    costo_moneda = costo_parts[1].lower()
                    
                    # 3c. Convertir el Costo (CMV) a USD (moneda base)
                    costo_usd = costo_valor
                    if costo_moneda in ('cup', 'cup-t'):
                        costo_usd /= cfg.TASA_USD_CUP
                        
                    total_costo_usd += costo_usd

            except Exception as e:
                # Esto maneja errores si el formato de la descripción es incorrecto
                logger.error(f"Error al parsear CMV en descripción '{descripcion}': {e}")
                
        # 4. Cálculo del Margen Bruto
        margen_bruto_usd = total_ingreso_usd - total_costo_usd
        
        # 5. Generar el reporte
        await update.message.reply_html(
            f"📈 <b>Reporte de Ganancia Bruta Acumulada</b>\n"
            f"<i>(Calculado usando Tasa Fija: 1 USD = {cfg.TASA_USD_CUP} CUP)</i>\n\n"
            f"💰 <b>Ingresos Totales por Ventas:</b> {total_ingreso_usd:,.2f} USD\n"
            f"🛒 <b>Costo Total de Ventas (CMV):</b> {total_costo_usd:,.2f} USD\n"
            f"--- \n"
            f"💵 <b>GANANCIA BRUTA ACUMULADA:</b> <b><u>{margen_bruto_usd:,.2f} USD</u></b>"
        )
        logger.info(f"Reporte de ganancias generado por {user_id}")

    except Exception as e:
        logger.error(f"Error inesperado en /ganancia: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al calcular la ganancia.")
        
# --- FASE 13: FUNCIÓN PARA /consignar ( Consignacion de INventario ) - CORREGIDO ---

async def consignar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Consigna productos a un vendedor, actualiza el stock general y la tabla Consignaciones.
    Uso: /consignar [codigo] [cantidad] [vendedor] [precio_venta] [moneda] [nota]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    conn = None
    try:
        logger.info("Iniciando proceso de consignación...")
        if len(context.args) < 6:
            raise ValueError("Faltan argumentos. Uso: /consignar [codigo] [cantidad] [vendedor] [precio_venta] [moneda] [nota...]")

        codigo = context.args[0].upper()
        cantidad_str = context.args[1]
        vendedor = context.args[2].upper()
        precio_str = context.args[3]
        moneda = context.args[4].lower()
        nota_consignacion = " ".join(context.args[5:])

        cantidad = float(cantidad_str)
        precio_venta = float(precio_str)

        if cantidad <= 0 or precio_venta <= 0: raise ValueError("Cantidad y precio deben ser positivos.")
        if moneda not in VALID_MONEDAS: raise ValueError(f"Moneda no válida: {moneda}")

        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()
        fecha_actual = datetime.datetime.now()

        # 1. ⬇️ Descontar del Stock General (Productos)
        logger.info(f"Verificando stock del producto {codigo}...")
        cursor.execute("SELECT stock, costo_unitario, moneda_costo FROM Productos WHERE codigo = ?", (codigo,))
        producto = cursor.fetchone()

        if not producto or producto[0] < cantidad:
            stock_actual = producto[0] if producto else 0
            logger.error(f"Stock insuficiente para {codigo}. Stock actual: {stock_actual}, Solicitado: {cantidad}")
            await update.message.reply_text(f"Error: Stock insuficiente para consignar. Solo quedan {stock_actual} unidades de {codigo}.")
            return
        
        costo_unitario = producto[1]
        moneda_costo = producto[2]
        
        nueva_cantidad = producto[0] - cantidad
        logger.info(f"Actualizando stock del producto {codigo} de {producto[0]} a {nueva_cantidad}...")
        cursor.execute("UPDATE Productos SET stock = ? WHERE codigo = ?", (nueva_cantidad, codigo))

        # 2. 📝 Insertar/Actualizar en la nueva tabla Consignaciones
        logger.info(f"Registrando consignación para vendedor {vendedor}...")
        # Primero verificamos si ya existe una consignación para este vendedor y producto
        cursor.execute("""
            SELECT stock FROM Consignaciones 
            WHERE codigo = ? AND vendedor = ?
        """, (codigo, vendedor))
        
        consignacion_existente = cursor.fetchone()
        
        if consignacion_existente:
            # Si existe, actualizamos
            nuevo_stock = consignacion_existente[0] + cantidad
            cursor.execute("""
                UPDATE Consignaciones 
                SET stock = ?, fecha_consignacion = ?
                WHERE codigo = ? AND vendedor = ?
            """, (nuevo_stock, fecha_actual, codigo, vendedor))
        else:
            # Si no existe, insertamos
            cursor.execute("""
                INSERT INTO Consignaciones 
                (codigo, vendedor, stock, precio_unitario, moneda, fecha_consignacion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (codigo, vendedor, cantidad, precio_venta, moneda, fecha_actual))

        # 3. 💸 Actualizar/Crear Deuda POR COBRAR (Deudas)
        monto_total_deuda = cantidad * precio_venta
        
        # Verificar si ya existe una deuda para este vendedor
        cursor.execute("""
            SELECT monto_pendiente FROM Deudas 
            WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'
        """, (vendedor, moneda))
        
        deuda_existente = cursor.fetchone()
        
        if deuda_existente:
            nuevo_monto = deuda_existente[0] + monto_total_deuda
            cursor.execute("""
                UPDATE Deudas 
                SET monto_pendiente = ?, fecha = ?
                WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'
            """, (nuevo_monto, fecha_actual, vendedor, moneda))
        else:
            cursor.execute("""
                INSERT INTO Deudas (actor_id, monto_pendiente, moneda, tipo, fecha)
                VALUES (?, ?, ?, 'POR_COBRAR', ?)
            """, (vendedor, monto_total_deuda, moneda, fecha_actual))

        # 4. ELIMINADO: Registro del Movimiento. Ya no es necesario registrar un movimiento de caja.

        conn.commit()

        await update.message.reply_html(
            f"✅ <b>Consignación Registrada!</b>\n\n"
            f"<b>Vendedor:</b> {vendedor}\n"
            f"<b>Producto:</b> {codigo} ({cantidad} u.)\n"
            f"<b>Deuda Por Cobrar:</b> +{monto_total_deuda:.2f} {moneda.upper()}"
        )

    except ValueError as e:
        # ... (manejo de errores) ...
        await update.message.reply_html(
            f"<b>Error de formato o validación:</b> {e}\n"
            "Uso correcto: <code>/consignar [codigo] [cantidad] [vendedor] [precio_venta] [moneda] [nota...]</code>"
        )
    except Exception as e:
        logger.error(f"Error inesperado en /consignar: {str(e)}")
        logger.error(f"Detalles completos del error:", exc_info=True)
        await update.message.reply_text(f"Error al registrar la consignación: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# --- FASE 14: FUNCIÓN PARA /stock_consignado ( Stock vendedor ) ---
async def stock_consignado_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Muestra el stock pendiente por vendedor consultando la tabla Consignaciones (RF6).
    Uso: /stock_consignado [vendedor]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("⛔ No tienes permiso.")
        return

    if not context.args:
        await update.message.reply_html(
            "<b>Error:</b> Debes especificar el nombre del vendedor.\n"
            "Uso: <code>/stock_consignado [vendedor]</code>"
        )
        return
        
    vendedor = context.args[0].upper()
    conn = None
    
    try:
        conn = sqlite3.connect("contabilidad.db")
        cursor = conn.cursor()
        
        # 1. CONSULTAR DIRECTAMENTE LA TABLA CONSIGNACIONES
        cursor.execute("""
            SELECT codigo, stock
            FROM Consignaciones
            WHERE vendedor = ? AND stock > 0
        """, (vendedor,))
        
        stock_items = cursor.fetchall()
        
        # 2. Construir el reporte final
        reporte = f"📦 <b>STOCK CONSIGNADO PENDIENTE: {vendedor}</b> 📦\n\n"
        stock_total_pendiente = 0
        
        if stock_items:
            for codigo, stock_cantidad in stock_items:
                reporte += f"  • <b>{codigo}</b>: {int(stock_cantidad)} unidades\n"
                stock_total_pendiente += stock_cantidad
        
        if stock_total_pendiente == 0:
            reporte += "  <i>El vendedor no tiene stock pendiente de liquidar.</i>"

        await update.message.reply_html(reporte)
        logger.info(f"Reporte de stock consignado para {vendedor} generado por {user_id}")

    except Exception as e:
        logger.error(f"Error inesperado en /stock_consignado: {e}")
        await update.message.reply_text("Ocurrió un error inesperado al generar el reporte de consignación.")
    finally:
        if conn:
            conn.close()