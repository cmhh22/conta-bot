import logging
import sqlite3
from contextlib import contextmanager
from typing import Optional, Union, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

@contextmanager
def get_db_connection():
    """Context manager para manejar conexiones a la base de datos de forma segura."""
    conn = None
    try:
        conn = sqlite3.connect("contabilidad.db")
        # Habilitar foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Retornar tuplas con nombres de columnas
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

class InventarioManager:
    @staticmethod
    def update_stock(
        conn: sqlite3.Connection,
        codigo: str,
        cantidad: float,
        es_entrada: bool = True
    ) -> Dict[str, Any]:
        """
        Actualiza el stock de un producto, validando existencias.
        """
        cursor = conn.cursor()
        
        # Verificar producto
        cursor.execute(
            "SELECT stock, costo_unitario, moneda_costo FROM Productos WHERE codigo = ?", 
            (codigo,)
        )
        producto = cursor.fetchone()
        
        if not producto:
            raise ValueError(f"El producto {codigo} no existe en el inventario.")
        
        stock_actual = producto['stock']
        if not es_entrada and stock_actual < cantidad:
            raise ValueError(
                f"Stock insuficiente para {codigo}. "
                f"Disponible: {stock_actual}, Solicitado: {cantidad}"
            )
        
        # Update stock
        nuevo_stock = stock_actual + cantidad if es_entrada else stock_actual - cantidad
        cursor.execute(
            "UPDATE Productos SET stock = ? WHERE codigo = ?",
            (nuevo_stock, codigo)
        )
        
        return {
            'stock_anterior': stock_actual,
            'stock_nuevo': nuevo_stock,
            'costo_unitario': producto['costo_unitario'],
            'moneda_costo': producto['moneda_costo']
        }

class DeudaManager:
    @staticmethod
    def liquidar_deuda_con_pago(
        conn: sqlite3.Connection,
        actor_id: str,
        monto_pagado: float,
        moneda_pago: str,
        tasa_cambio: float
    ) -> float:
        """
        Liquida una deuda POR COBRAR (vendedor) con un pago en efectivo, 
        convirtiendo la moneda de pago a la moneda de la deuda (USD). 
        Retorna el monto liquidado en USD.
        """
        cursor = conn.cursor()
        
        # 1. Convertir el monto pagado a USD (Moneda base de la deuda)
        if moneda_pago == 'cup' or moneda_pago == 'cup-t':
            monto_liquidado_usd = monto_pagado / tasa_cambio
        elif moneda_pago == 'usd':
            monto_liquidado_usd = monto_pagado
        else:
            raise ValueError("Moneda de pago no soportada para liquidacion.")
            
        # 2. Reducir la deuda POR_COBRAR (asumiendo que la deuda esta en USD)
        tipo_deuda = 'POR_COBRAR'
        
        cursor.execute("""
            UPDATE Deudas 
            SET monto_pendiente = monto_pendiente - ?
            WHERE actor_id = ? AND tipo = ? AND moneda = 'usd'
        """, (monto_liquidado_usd, actor_id, tipo_deuda))

        if cursor.rowcount == 0:
            logger.warning(
                f"No se pudo liquidar la deuda POR_COBRAR. "
                f"Actor: {actor_id}, Monto liquidado: {monto_liquidado_usd} USD"
            )

        return monto_liquidado_usd
    
    @staticmethod
    def liquidar_deuda_por_venta(
        conn: sqlite3.Connection,
        vendedor: str,
        codigo: str,
        cantidad_vendida: float
    ) -> float:
        """
        Liquida la deuda POR COBRAR del vendedor por la cantidad vendida.
        Usa el precio unitario de consignacion para calcular el monto a descontar.
        """
        cursor = conn.cursor()
        
        # 1. Obtener los detalles de la consignacion (incluye el precio de consignacion)
        cursor.execute("""
            SELECT precio_unitario, moneda FROM Consignaciones
            WHERE vendedor = ? AND codigo = ?
        """, (vendedor, codigo))
        consignacion_data = cursor.fetchone()

        if not consignacion_data:
            raise ValueError(f"Error: No se encontro el precio de consignacion para {codigo} de {vendedor}.")
        
        precio_unitario = consignacion_data['precio_unitario']
        moneda_deuda = consignacion_data['moneda'] # La moneda de la deuda original
        
        # 2. Calcular el monto a descontar de la deuda
        monto_a_liquidar = cantidad_vendida * precio_unitario
        
        # 3. Descontar la deuda POR COBRAR
        cursor.execute("""
            UPDATE Deudas 
            SET monto_pendiente = monto_pendiente - ?
            WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'
        """, (monto_a_liquidar, vendedor, moneda_deuda))

        # 4. Verificar que se haya updated alguna fila
        if cursor.rowcount == 0:
            logger.warning(f"No se pudo liquidar la deuda por venta. Vendedor: {vendedor}, Monto: {monto_a_liquidar} {moneda_deuda}")
            return 0.0

        return monto_a_liquidar # Retorna el monto original de la deuda liquidada


    @staticmethod
    def update_deuda(
        conn: sqlite3.Connection,
        actor_id: str,
        monto: float,
        moneda: str,
        tipo: str,
        es_incremento: bool = True
    ) -> float:
        """
        Actualiza el saldo de una deuda, creandola si no existe.
        """
        cursor = conn.cursor()
        
        # Validar tipo de deuda
        if tipo not in ('POR_PAGAR', 'POR_COBRAR'):
            raise ValueError("Tipo de deuda invalid")
        
        # Buscar deuda existente
        cursor.execute("""
            SELECT monto_pendiente 
            FROM Deudas 
            WHERE actor_id = ? AND moneda = ? AND tipo = ?
        """, (actor_id, moneda, tipo))
        
        deuda = cursor.fetchone()
        
        if deuda:
            # Update deuda existente
            nuevo_monto = deuda['monto_pendiente']
            if es_incremento:
                nuevo_monto += monto
            else:
                nuevo_monto = max(0, nuevo_monto - monto)  # Evitar saldo negativo
            
            cursor.execute("""
                UPDATE Deudas 
                SET monto_pendiente = ?, 
                    fecha = CURRENT_TIMESTAMP
                WHERE actor_id = ? AND moneda = ? AND tipo = ?
            """, (nuevo_monto, actor_id, moneda, tipo))
        else:
            # Create nueva deuda
            if not es_incremento:
                raise ValueError(f"No existe deuda {tipo} para {actor_id} en {moneda}")
            
            nuevo_monto = monto
            cursor.execute("""
                INSERT INTO Deudas (actor_id, monto_pendiente, moneda, tipo, fecha)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (actor_id, nuevo_monto, moneda, tipo))
        
        return nuevo_monto

class MovimientoManager:
    # 🌟 NUEVO METODO CRITICO: Obtener Saldo para evitar Negativos
    @staticmethod
    def get_saldo_caja(conn: sqlite3.Connection, caja: str, moneda: str) -> float:
        """Calcula el saldo actual de una caja en una moneda especifica."""
        cursor = conn.cursor()
        # Nota: 'venta' y 'consignacion_finalizada' son tipos de 'ingreso' de efectivo en caja.
        # 'gasto', 'traspaso' (salida) y 'pago_proveedor' (que usa gasto) son salidas.
        # Asumimos que los tipos en Movimientos reflejan correctamente el flujo (Ingreso=+, Gasto/-=).
        cursor.execute("""
            SELECT SUM(
                CASE 
                    WHEN tipo IN ('ingreso', 'venta', 'consignacion_finalizada') THEN monto 
                    WHEN tipo IN ('gasto', 'traspaso') THEN -monto 
                    ELSE 0 
                END
            ) 
            FROM Movimientos 
            WHERE caja = ? AND moneda = ?
        """, (caja, moneda))
        saldo = cursor.fetchone()[0]
        return saldo if saldo is not None else 0.0

    @staticmethod
    def registrar_movimiento(
        conn: sqlite3.Connection,
        tipo: str,
        monto: float,
        moneda: str,
        caja: str,
        user_id: int,
        descripcion: str
    ) -> int:
        """
        Registra un movimiento en la base de datos.
        """
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Movimientos (
                fecha, tipo, monto, moneda, caja, user_id, descripcion
            ) VALUES (
                CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?
            )
        """, (tipo, monto, moneda, caja, user_id, descripcion))
        
        return cursor.lastrowid

class ConsignacionManager:
    @staticmethod
    def update_consignacion(
        conn: sqlite3.Connection,
        codigo: str,
        vendedor: str,
        cantidad: float,
        precio_unitario: Optional[float] = None,
        moneda: Optional[str] = None,
        es_incremento: bool = True
    ) -> Dict[str, Any]:
        """
        Actualiza o crea una consignacion.
        """
        cursor = conn.cursor()
        
        # Verificar consignacion existente
        cursor.execute("""
            SELECT stock, precio_unitario, moneda
            FROM Consignaciones 
            WHERE codigo = ? AND vendedor = ?
        """, (codigo, vendedor))
        
        consignacion = cursor.fetchone()
        
        if consignacion:
            stock_actual = consignacion['stock']
            if not es_incremento and stock_actual < cantidad:
                raise ValueError(
                    f"Stock consignado insuficiente para {vendedor}. "
                    f"Disponible: {stock_actual}, Solicitado: {cantidad}"
                )
            
            nuevo_stock = stock_actual + cantidad if es_incremento else stock_actual - cantidad
            
            cursor.execute("""
                UPDATE Consignaciones 
                SET stock = ?,
                    fecha_consignacion = CURRENT_TIMESTAMP
                WHERE codigo = ? AND vendedor = ?
            """, (nuevo_stock, codigo, vendedor))
            
            precio_unitario = consignacion['precio_unitario']
            moneda = consignacion['moneda']
            
        else:
            if not es_incremento:
                raise ValueError(f"No existe consignacion de {codigo} para {vendedor}")
            
            if precio_unitario is None or moneda is None:
                raise ValueError("Precio y moneda son requeridos para nueva consignacion")
            
            nuevo_stock = cantidad
            
            cursor.execute("""
                INSERT INTO Consignaciones (
                    codigo, vendedor, stock, precio_unitario, moneda, fecha_consignacion
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (codigo, vendedor, nuevo_stock, precio_unitario, moneda))
        
        return {
            'stock_nuevo': nuevo_stock,
            'precio_unitario': precio_unitario,
            'moneda': moneda
        }

class ContainerManager:
    @staticmethod
    def create(conn: sqlite3.Connection, nombre: str) -> int:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Contenedores (nombre) VALUES (?)",
            (nombre.strip(),)
        )
        return cursor.lastrowid

    @staticmethod
    def listar(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, fecha_creacion FROM Contenedores ORDER BY nombre ASC")
        return cursor.fetchall()

    @staticmethod
    def get_by_id(conn: sqlite3.Connection, cont_id: int) -> Optional[sqlite3.Row]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, fecha_creacion FROM Contenedores WHERE id = ?", (cont_id,))
        return cursor.fetchone()

    @staticmethod
    def update(conn: sqlite3.Connection, cont_id: int, nuevo_nombre: str) -> None:
        cursor = conn.cursor()
        cursor.execute("UPDATE Contenedores SET nombre = ? WHERE id = ?", (nuevo_nombre.strip(), cont_id))
        if cursor.rowcount == 0:
            raise ValueError("Contenedor not found")

    @staticmethod
    def delete(conn: sqlite3.Connection, cont_id: int) -> None:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Contenedores WHERE id = ?", (cont_id,))
        if cursor.rowcount == 0:
            raise ValueError("Contenedor not found")
