"""
Repositorios para acceso a datos.
Cada repositorio maneja una entidad específica.
"""
import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from database.connection import get_db_connection

logger = logging.getLogger(__name__)


class CajaRepository:
    """Repositorio para operaciones con cajas."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, nombre: str, descripcion: Optional[str] = None) -> int:
        """Crea una nueva caja."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Cajas (nombre, descripcion) VALUES (?, ?)
        """, (nombre.strip(), descripcion.strip() if descripcion else None))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todas las cajas."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, descripcion, fecha_creacion 
            FROM Cajas 
            ORDER BY nombre ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, caja_id: int) -> Optional[sqlite3.Row]:
        """Obtiene una caja por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, descripcion, fecha_creacion 
            FROM Cajas 
            WHERE id = ?
        """, (caja_id,))
        return cursor.fetchone()
    
    @staticmethod
    def obtener_por_nombre(conn: sqlite3.Connection, nombre: str) -> Optional[sqlite3.Row]:
        """Obtiene una caja por su nombre."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, descripcion, fecha_creacion 
            FROM Cajas 
            WHERE nombre = ?
        """, (nombre.strip(),))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, caja_id: int, nuevo_nombre: str, 
                   nueva_descripcion: Optional[str] = None) -> int:
        """Actualiza una caja."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Cajas 
            SET nombre = ?, descripcion = ? 
            WHERE id = ?
        """, (nuevo_nombre.strip(), nueva_descripcion.strip() if nueva_descripcion else None, caja_id))
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, caja_id: int) -> int:
        """Elimina una caja."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Cajas WHERE id = ?", (caja_id,))
        return cursor.rowcount


class CajaExternaRepository:
    """Repositorio para operaciones con cajas externas."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, nombre: str, ubicacion: str, 
              descripcion: Optional[str] = None, porcentaje_envio: float = 0) -> int:
        """Crea una nueva caja externa."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Cajas_Externas (nombre, ubicacion, descripcion, porcentaje_envio)
            VALUES (?, ?, ?, ?)
        """, (nombre.strip(), ubicacion.strip(), descripcion.strip() if descripcion else None, porcentaje_envio))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todas las cajas externas."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, descripcion, porcentaje_envio, fecha_creacion
            FROM Cajas_Externas
            ORDER BY nombre ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, caja_externa_id: int) -> Optional[sqlite3.Row]:
        """Obtiene una caja externa por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, descripcion, porcentaje_envio, fecha_creacion
            FROM Cajas_Externas
            WHERE id = ?
        """, (caja_externa_id,))
        return cursor.fetchone()
    
    @staticmethod
    def obtener_por_nombre(conn: sqlite3.Connection, nombre: str) -> Optional[sqlite3.Row]:
        """Obtiene una caja externa por su nombre."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, descripcion, porcentaje_envio, fecha_creacion
            FROM Cajas_Externas
            WHERE nombre = ?
        """, (nombre.strip(),))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, caja_externa_id: int, nuevo_nombre: str,
                   nueva_ubicacion: str, nueva_descripcion: Optional[str] = None,
                   nuevo_porcentaje_envio: Optional[float] = None) -> int:
        """Actualiza una caja externa."""
        cursor = conn.cursor()
        if nuevo_porcentaje_envio is not None:
            cursor.execute("""
                UPDATE Cajas_Externas
                SET nombre = ?, ubicacion = ?, descripcion = ?, porcentaje_envio = ?
                WHERE id = ?
            """, (nuevo_nombre.strip(), nueva_ubicacion.strip(),
                  nueva_descripcion.strip() if nueva_descripcion else None,
                  nuevo_porcentaje_envio, caja_externa_id))
        else:
            cursor.execute("""
                UPDATE Cajas_Externas
                SET nombre = ?, ubicacion = ?, descripcion = ?
                WHERE id = ?
            """, (nuevo_nombre.strip(), nueva_ubicacion.strip(),
                  nueva_descripcion.strip() if nueva_descripcion else None, caja_externa_id))
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, caja_externa_id: int) -> int:
        """Elimina una caja externa."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Cajas_Externas WHERE id = ?", (caja_externa_id,))
        return cursor.rowcount


class TransferenciaExternaRepository:
    """Repositorio para operaciones con transferencias externas."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, caja_origen_id: int, caja_externa_id: int,
              producto_codigo: str, monto: float, moneda: str, porcentaje_envio: float,
              monto_envio: float, monto_recibido: float, user_id: int,
              descripcion: Optional[str] = None) -> int:
        """Crea una nueva transferencia externa."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Transferencias_Externas 
            (caja_origen_id, caja_externa_id, producto_codigo, monto, moneda, 
             porcentaje_envio, monto_envio, monto_recibido, user_id, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (caja_origen_id, caja_externa_id, producto_codigo, monto, moneda,
              porcentaje_envio, monto_envio, monto_recibido, user_id, descripcion))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_por_caja_externa(conn: sqlite3.Connection, caja_externa_id: int) -> List[sqlite3.Row]:
        """Obtiene todas las transferencias a una caja externa."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT te.id, te.fecha, te.caja_origen_id, c.nombre as caja_origen_nombre,
                   te.producto_codigo, p.nombre as producto_nombre,
                   te.monto, te.moneda, te.porcentaje_envio, te.monto_envio, te.monto_recibido,
                   te.descripcion
            FROM Transferencias_Externas te
            JOIN Cajas c ON te.caja_origen_id = c.id
            JOIN Productos p ON te.producto_codigo = p.codigo
            WHERE te.caja_externa_id = ?
            ORDER BY te.fecha DESC
        """, (caja_externa_id,))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_producto(conn: sqlite3.Connection, producto_codigo: str) -> List[sqlite3.Row]:
        """Obtiene todas las transferencias de un producto específico."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT te.id, te.fecha, te.caja_origen_id, c.nombre as caja_origen_nombre,
                   ce.nombre as caja_externa_nombre, ce.ubicacion,
                   te.monto, te.moneda, te.porcentaje_envio, te.monto_envio, te.monto_recibido,
                   te.descripcion
            FROM Transferencias_Externas te
            JOIN Cajas c ON te.caja_origen_id = c.id
            JOIN Cajas_Externas ce ON te.caja_externa_id = ce.id
            WHERE te.producto_codigo = ?
            ORDER BY te.fecha DESC
        """, (producto_codigo,))
        return cursor.fetchall()


class MovimientoRepository:
    """Repositorio para operaciones con movimientos."""
    
    @staticmethod
    def get_saldo_caja(conn: sqlite3.Connection, caja_id: int, moneda: str) -> float:
        """Calcula el saldo actual de una caja en una moneda específica."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(
                CASE 
                    WHEN tipo IN ('ingreso', 'venta', 'consignacion_finalizada') THEN monto 
                    WHEN tipo IN ('gasto', 'traspaso') THEN -monto 
                    ELSE 0 
                END
            ) 
            FROM Movimientos 
            WHERE caja_id = ? AND moneda = ?
        """, (caja_id, moneda))
        saldo = cursor.fetchone()[0]
        return saldo if saldo is not None else 0.0
    
    @staticmethod
    def crear(conn: sqlite3.Connection, tipo: str, monto: float, moneda: str, 
              caja_id: int, user_id: int, descripcion: str) -> int:
        """Crea un nuevo movimiento."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Movimientos (fecha, tipo, monto, moneda, caja_id, user_id, descripcion)
            VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
        """, (tipo, monto, moneda, caja_id, user_id, descripcion))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_por_fecha(conn: sqlite3.Connection, fecha_desde: datetime) -> List[sqlite3.Row]:
        """Obtiene movimientos desde una fecha."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.fecha, m.tipo, m.monto, m.moneda, c.nombre as caja, m.descripcion
            FROM Movimientos m
            JOIN Cajas c ON m.caja_id = c.id
            WHERE m.fecha >= ?
            ORDER BY m.fecha DESC
        """, (fecha_desde.strftime('%Y-%m-%d %H:%M:%S'),))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los movimientos."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, c.nombre as caja_nombre
            FROM Movimientos m
            JOIN Cajas c ON m.caja_id = c.id
            ORDER BY m.fecha DESC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_balance_por_caja(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene el balance agrupado por caja y moneda."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.nombre as caja, m.moneda, 
                   SUM(CASE WHEN m.tipo IN ('ingreso', 'venta', 'consignacion_finalizada') THEN m.monto 
                            WHEN m.tipo IN ('gasto', 'traspaso') THEN -m.monto 
                            ELSE 0 END) as total
            FROM Movimientos m
            JOIN Cajas c ON m.caja_id = c.id
            GROUP BY c.id, c.nombre, m.moneda
            ORDER BY c.nombre, m.moneda
        """)
        return cursor.fetchall()


class ProductoRepository:
    """Repositorio para operaciones con productos."""
    
    @staticmethod
    def obtener_por_codigo(conn: sqlite3.Connection, codigo: str) -> Optional[sqlite3.Row]:
        """Obtiene un producto por su código."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, codigo, nombre, stock, costo_unitario, moneda_costo, precio_venta
            FROM Productos
            WHERE codigo = ?
        """, (codigo,))
        return cursor.fetchone()
    
    @staticmethod
    def crear(conn: sqlite3.Connection, codigo: str, nombre: str, costo_unitario: float,
              moneda_costo: str, stock: float = 0) -> int:
        """Crea un nuevo producto."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Productos (codigo, nombre, costo_unitario, moneda_costo, stock)
            VALUES (?, ?, ?, ?, ?)
        """, (codigo, nombre, costo_unitario, moneda_costo, stock))
        return cursor.lastrowid
    
    @staticmethod
    def actualizar_stock(conn: sqlite3.Connection, codigo: str, nuevo_stock: float) -> None:
        """Actualiza el stock de un producto."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Productos SET stock = ? WHERE codigo = ?
        """, (nuevo_stock, codigo))
    
    @staticmethod
    def actualizar_costo(conn: sqlite3.Connection, codigo: str, nuevo_costo: float, 
                        moneda_costo: str) -> None:
        """Actualiza el costo de un producto."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Productos SET costo_unitario = ?, moneda_costo = ? WHERE codigo = ?
        """, (nuevo_costo, moneda_costo, codigo))
    
    @staticmethod
    def obtener_con_stock(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los productos con stock > 0."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo, nombre, stock, costo_unitario, moneda_costo
            FROM Productos
            WHERE stock > 0
            ORDER BY codigo
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los productos."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo, nombre, stock, costo_unitario, moneda_costo, precio_venta
            FROM Productos
            ORDER BY codigo
        """)
        return cursor.fetchall()


class DeudaRepository:
    """Repositorio para operaciones con deudas."""
    
    @staticmethod
    def obtener_por_actor(conn: sqlite3.Connection, actor_id: str, moneda: str, 
                         tipo: str) -> Optional[sqlite3.Row]:
        """Obtiene una deuda específica."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, actor_id, tipo, monto_pendiente, moneda, fecha
            FROM Deudas
            WHERE actor_id = ? AND moneda = ? AND tipo = ?
        """, (actor_id, moneda, tipo))
        return cursor.fetchone()
    
    @staticmethod
    def crear(conn: sqlite3.Connection, actor_id: str, monto: float, moneda: str, 
              tipo: str) -> int:
        """Crea una nueva deuda."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Deudas (actor_id, monto_pendiente, moneda, tipo, fecha)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (actor_id, monto, moneda, tipo))
        return cursor.lastrowid
    
    @staticmethod
    def actualizar_monto(conn: sqlite3.Connection, actor_id: str, moneda: str, 
                         tipo: str, nuevo_monto: float) -> int:
        """Actualiza el monto de una deuda."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Deudas 
            SET monto_pendiente = ?, fecha = CURRENT_TIMESTAMP
            WHERE actor_id = ? AND moneda = ? AND tipo = ?
        """, (nuevo_monto, actor_id, moneda, tipo))
        return cursor.rowcount
    
    @staticmethod
    def obtener_pendientes(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todas las deudas pendientes (monto > 0)."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT actor_id, tipo, monto_pendiente, moneda
            FROM Deudas
            WHERE monto_pendiente > 0
            ORDER BY tipo DESC, moneda, actor_id
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, deuda_id: int) -> Optional[sqlite3.Row]:
        """Obtiene una deuda por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, actor_id, tipo, monto_pendiente, moneda, fecha
            FROM Deudas
            WHERE id = ?
        """, (deuda_id,))
        return cursor.fetchone()


class DeudaProductoRepository:
    """Repositorio para operaciones con deudas-productos."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, deuda_id: int, producto_codigo: str,
              cantidad: float, costo_unitario: float, monto_total: float) -> int:
        """Crea un registro de producto asociado a una deuda."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Deudas_Productos (deuda_id, producto_codigo, cantidad, costo_unitario, monto_total, fecha)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (deuda_id, producto_codigo, cantidad, costo_unitario, monto_total))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_por_deuda(conn: sqlite3.Connection, deuda_id: int) -> List[sqlite3.Row]:
        """Obtiene todos los productos asociados a una deuda."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dp.id, dp.producto_codigo, p.nombre as producto_nombre,
                   dp.cantidad, dp.costo_unitario, dp.monto_total, dp.fecha
            FROM Deudas_Productos dp
            JOIN Productos p ON dp.producto_codigo = p.codigo
            WHERE dp.deuda_id = ?
            ORDER BY dp.fecha DESC
        """, (deuda_id,))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_proveedor(conn: sqlite3.Connection, actor_id: str, moneda: str) -> List[sqlite3.Row]:
        """Obtiene todos los productos de deudas de un proveedor específico."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dp.id, dp.producto_codigo, p.nombre as producto_nombre,
                   dp.cantidad, dp.costo_unitario, dp.monto_total, dp.fecha,
                   d.actor_id, d.moneda
            FROM Deudas_Productos dp
            JOIN Productos p ON dp.producto_codigo = p.codigo
            JOIN Deudas d ON dp.deuda_id = d.id
            WHERE d.actor_id = ? AND d.moneda = ? AND d.tipo = 'POR_PAGAR'
            ORDER BY dp.fecha DESC
        """, (actor_id, moneda))
        return cursor.fetchall()


class ConsignacionRepository:
    """Repositorio para operaciones con consignaciones."""
    
    @staticmethod
    def obtener_por_vendedor_codigo(conn: sqlite3.Connection, vendedor: str, 
                                    codigo: str) -> Optional[sqlite3.Row]:
        """Obtiene una consignación específica."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, codigo, vendedor, stock, precio_unitario, moneda, fecha_consignacion
            FROM Consignaciones
            WHERE codigo = ? AND vendedor = ?
        """, (codigo, vendedor))
        return cursor.fetchone()
    
    @staticmethod
    def crear(conn: sqlite3.Connection, codigo: str, vendedor: str, stock: float,
              precio_unitario: float, moneda: str) -> int:
        """Crea una nueva consignación."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Consignaciones (codigo, vendedor, stock, precio_unitario, moneda, fecha_consignacion)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (codigo, vendedor, stock, precio_unitario, moneda))
        return cursor.lastrowid
    
    @staticmethod
    def actualizar_stock(conn: sqlite3.Connection, codigo: str, vendedor: str, 
                        nuevo_stock: float) -> None:
        """Actualiza el stock consignado."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Consignaciones 
            SET stock = ?, fecha_consignacion = CURRENT_TIMESTAMP
            WHERE codigo = ? AND vendedor = ?
        """, (nuevo_stock, codigo, vendedor))
    
    @staticmethod
    def obtener_por_vendedor(conn: sqlite3.Connection, vendedor: str) -> List[sqlite3.Row]:
        """Obtiene todas las consignaciones de un vendedor con stock > 0."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo, stock
            FROM Consignaciones
            WHERE vendedor = ? AND stock > 0
        """, (vendedor,))
        return cursor.fetchall()


class ProveedorRepository:
    """Repositorio para operaciones con proveedores."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, name: str) -> int:
        """Crea un nuevo proveedor."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Proveedores (name) VALUES (?)
        """, (name.strip(),))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los proveedores."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Proveedores 
            ORDER BY name ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, proveedor_id: int) -> Optional[sqlite3.Row]:
        """Obtiene un proveedor por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Proveedores 
            WHERE id = ?
        """, (proveedor_id,))
        return cursor.fetchone()
    
    @staticmethod
    def obtener_por_nombre(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
        """Obtiene un proveedor por su nombre."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Proveedores 
            WHERE name = ?
        """, (name.strip(),))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, proveedor_id: int, nuevo_name: str) -> int:
        """Actualiza el nombre de un proveedor."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Proveedores SET name = ? WHERE id = ?
        """, (nuevo_name.strip(), proveedor_id))
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, proveedor_id: int) -> int:
        """Elimina un proveedor."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Proveedores WHERE id = ?", (proveedor_id,))
        return cursor.rowcount


class VendedorRepository:
    """Repositorio para operaciones con vendedores."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, name: str) -> int:
        """Crea un nuevo vendedor."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Vendedores (name) VALUES (?)
        """, (name.strip(),))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los vendedores."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Vendedores 
            ORDER BY name ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, vendedor_id: int) -> Optional[sqlite3.Row]:
        """Obtiene un vendedor por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Vendedores 
            WHERE id = ?
        """, (vendedor_id,))
        return cursor.fetchone()
    
    @staticmethod
    def obtener_por_nombre(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
        """Obtiene un vendedor por su nombre."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, fecha_creacion 
            FROM Vendedores 
            WHERE name = ?
        """, (name.strip(),))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, vendedor_id: int, nuevo_name: str) -> int:
        """Actualiza el nombre de un vendedor."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Vendedores SET name = ? WHERE id = ?
        """, (nuevo_name.strip(), vendedor_id))
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, vendedor_id: int) -> int:
        """Elimina un vendedor."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Vendedores WHERE id = ?", (vendedor_id,))
        return cursor.rowcount


class ContenedorRepository:
    """Repositorio para operaciones con contenedores."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, nombre: str, numero_contenedor: Optional[str] = None, proveedor_id: Optional[int] = None) -> int:
        """Crea un nuevo contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Contenedores (nombre, numero_contenedor, proveedor_id) 
            VALUES (?, ?, ?)
        """, (nombre.strip(), numero_contenedor.strip() if numero_contenedor else None, proveedor_id))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los contenedores con información del proveedor."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id, 
                c.nombre, 
                c.numero_contenedor,
                c.proveedor_id,
                c.fecha_creacion,
                p.name as proveedor_name
            FROM Contenedores c
            LEFT JOIN Proveedores p ON c.proveedor_id = p.id
            ORDER BY c.nombre ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, cont_id: int) -> Optional[sqlite3.Row]:
        """Obtiene un contenedor por su ID con información del proveedor."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id, 
                c.nombre, 
                c.numero_contenedor,
                c.proveedor_id,
                c.fecha_creacion,
                p.name as proveedor_name
            FROM Contenedores c
            LEFT JOIN Proveedores p ON c.proveedor_id = p.id
            WHERE c.id = ?
        """, (cont_id,))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, cont_id: int, nuevo_nombre: Optional[str] = None, 
                   numero_contenedor: Optional[str] = None, proveedor_id: Optional[int] = None,
                   quitar_proveedor: bool = False) -> int:
        """Actualiza un contenedor.
        
        Args:
            quitar_proveedor: Si es True, establece proveedor_id a NULL (ignora proveedor_id si está presente)
        """
        cursor = conn.cursor()
        
        # Construir la query dinámicamente según los campos a actualizar
        updates = []
        params = []
        
        if nuevo_nombre is not None:
            updates.append("nombre = ?")
            params.append(nuevo_nombre.strip())
        
        if numero_contenedor is not None:
            updates.append("numero_contenedor = ?")
            params.append(numero_contenedor.strip() if numero_contenedor else None)
        
        # Manejar proveedor_id: si quitar_proveedor es True, establecer a NULL
        # Si quitar_proveedor es False y proveedor_id no es None, actualizar con el valor
        if quitar_proveedor:
            updates.append("proveedor_id = NULL")
        elif proveedor_id is not None:
            updates.append("proveedor_id = ?")
            params.append(proveedor_id)
        
        if not updates:
            return 0
        
        params.append(cont_id)
        query = f"UPDATE Contenedores SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, cont_id: int) -> int:
        """Elimina un contenedor."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Contenedores WHERE id = ?", (cont_id,))
        return cursor.rowcount
    
    @staticmethod
    def obtener_por_proveedor(conn: sqlite3.Connection, proveedor_id: int) -> List[sqlite3.Row]:
        """Obtiene todos los contenedores asociados a un proveedor (relación muchos a uno)."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                c.id, 
                c.nombre, 
                c.numero_contenedor,
                c.proveedor_id,
                c.fecha_creacion,
                p.name as proveedor_name
            FROM Contenedores c
            LEFT JOIN Proveedores p ON c.proveedor_id = p.id
            WHERE c.proveedor_id = ?
            ORDER BY c.nombre ASC
        """, (proveedor_id,))
        return cursor.fetchall()


class AlmacenRepository:
    """Repositorio para operaciones con almacenes."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, nombre: str, ubicacion: Optional[str] = None) -> int:
        """Crea un nuevo almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Almacenes (nombre, ubicacion)
            VALUES (?, ?)
        """, (nombre.strip(), ubicacion.strip() if ubicacion else None))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_todos(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Obtiene todos los almacenes."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, fecha_creacion
            FROM Almacenes
            ORDER BY nombre ASC
        """)
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_id(conn: sqlite3.Connection, almacen_id: int) -> Optional[sqlite3.Row]:
        """Obtiene un almacén por su ID."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, fecha_creacion
            FROM Almacenes
            WHERE id = ?
        """, (almacen_id,))
        return cursor.fetchone()
    
    @staticmethod
    def obtener_por_nombre(conn: sqlite3.Connection, nombre: str) -> Optional[sqlite3.Row]:
        """Obtiene un almacén por su nombre."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nombre, ubicacion, fecha_creacion
            FROM Almacenes
            WHERE nombre = ?
        """, (nombre.strip(),))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar(conn: sqlite3.Connection, almacen_id: int, nuevo_nombre: Optional[str] = None,
                   nueva_ubicacion: Optional[str] = None) -> int:
        """Actualiza un almacén."""
        cursor = conn.cursor()
        updates = []
        params = []
        
        if nuevo_nombre is not None:
            updates.append("nombre = ?")
            params.append(nuevo_nombre.strip())
        
        if nueva_ubicacion is not None:
            updates.append("ubicacion = ?")
            params.append(nueva_ubicacion.strip() if nueva_ubicacion else None)
        
        if not updates:
            return 0
        
        params.append(almacen_id)
        query = f"UPDATE Almacenes SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        return cursor.rowcount
    
    @staticmethod
    def eliminar(conn: sqlite3.Connection, almacen_id: int) -> int:
        """Elimina un almacén."""
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Almacenes WHERE id = ?", (almacen_id,))
        return cursor.rowcount


class ContenedorProductoRepository:
    """Repositorio para operaciones con productos en contenedores."""
    
    @staticmethod
    def agregar_producto(conn: sqlite3.Connection, contenedor_id: int, producto_codigo: str,
                         cantidad: float) -> int:
        """Agrega o actualiza un producto en un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Contenedor_Productos (contenedor_id, producto_codigo, cantidad)
            VALUES (?, ?, ?)
            ON CONFLICT(contenedor_id, producto_codigo) 
            DO UPDATE SET cantidad = cantidad + ?
        """, (contenedor_id, producto_codigo, cantidad, cantidad))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_productos_por_contenedor(conn: sqlite3.Connection, contenedor_id: int) -> List[sqlite3.Row]:
        """Obtiene todos los productos de un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                cp.id,
                cp.contenedor_id,
                cp.producto_codigo,
                cp.cantidad,
                cp.fecha_ingreso,
                p.nombre as producto_nombre
            FROM Contenedor_Productos cp
            JOIN Productos p ON cp.producto_codigo = p.codigo
            WHERE cp.contenedor_id = ?
            ORDER BY p.nombre ASC
        """, (contenedor_id,))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_producto_en_contenedor(conn: sqlite3.Connection, contenedor_id: int,
                                      producto_codigo: str) -> Optional[sqlite3.Row]:
        """Obtiene un producto específico en un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, contenedor_id, producto_codigo, cantidad, fecha_ingreso
            FROM Contenedor_Productos
            WHERE contenedor_id = ? AND producto_codigo = ?
        """, (contenedor_id, producto_codigo))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar_cantidad(conn: sqlite3.Connection, contenedor_id: int, producto_codigo: str,
                           nueva_cantidad: float) -> int:
        """Actualiza la cantidad de un producto en un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Contenedor_Productos
            SET cantidad = ?
            WHERE contenedor_id = ? AND producto_codigo = ?
        """, (nueva_cantidad, contenedor_id, producto_codigo))
        return cursor.rowcount
    
    @staticmethod
    def reducir_cantidad(conn: sqlite3.Connection, contenedor_id: int, producto_codigo: str,
                        cantidad: float) -> int:
        """Reduce la cantidad de un producto en un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Contenedor_Productos
            SET cantidad = cantidad - ?
            WHERE contenedor_id = ? AND producto_codigo = ?
            AND cantidad >= ?
        """, (cantidad, contenedor_id, producto_codigo, cantidad))
        return cursor.rowcount
    
    @staticmethod
    def eliminar_producto(conn: sqlite3.Connection, contenedor_id: int, producto_codigo: str) -> int:
        """Elimina un producto de un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Contenedor_Productos
            WHERE contenedor_id = ? AND producto_codigo = ?
        """, (contenedor_id, producto_codigo))
        return cursor.rowcount


class InventarioAlmacenRepository:
    """Repositorio para operaciones con inventario de almacenes."""
    
    @staticmethod
    def agregar_producto(conn: sqlite3.Connection, almacen_id: int, producto_codigo: str,
                         cantidad: float) -> int:
        """Agrega o actualiza un producto en el inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Inventario_Almacen (almacen_id, producto_codigo, cantidad)
            VALUES (?, ?, ?)
            ON CONFLICT(almacen_id, producto_codigo) 
            DO UPDATE SET cantidad = cantidad + ?, fecha_actualizacion = CURRENT_TIMESTAMP
        """, (almacen_id, producto_codigo, cantidad, cantidad))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_inventario_por_almacen(conn: sqlite3.Connection, almacen_id: int) -> List[sqlite3.Row]:
        """Obtiene todo el inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                ia.id,
                ia.almacen_id,
                ia.producto_codigo,
                ia.cantidad,
                ia.fecha_actualizacion,
                p.nombre as producto_nombre
            FROM Inventario_Almacen ia
            JOIN Productos p ON ia.producto_codigo = p.codigo
            WHERE ia.almacen_id = ?
            ORDER BY p.nombre ASC
        """, (almacen_id,))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_producto_en_almacen(conn: sqlite3.Connection, almacen_id: int,
                                    producto_codigo: str) -> Optional[sqlite3.Row]:
        """Obtiene un producto específico en el inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, almacen_id, producto_codigo, cantidad, fecha_actualizacion
            FROM Inventario_Almacen
            WHERE almacen_id = ? AND producto_codigo = ?
        """, (almacen_id, producto_codigo))
        return cursor.fetchone()
    
    @staticmethod
    def actualizar_cantidad(conn: sqlite3.Connection, almacen_id: int, producto_codigo: str,
                           nueva_cantidad: float) -> int:
        """Actualiza la cantidad de un producto en el inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Inventario_Almacen
            SET cantidad = ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE almacen_id = ? AND producto_codigo = ?
        """, (nueva_cantidad, almacen_id, producto_codigo))
        return cursor.rowcount
    
    @staticmethod
    def reducir_cantidad(conn: sqlite3.Connection, almacen_id: int, producto_codigo: str,
                        cantidad: float) -> int:
        """Reduce la cantidad de un producto en el inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Inventario_Almacen
            SET cantidad = cantidad - ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE almacen_id = ? AND producto_codigo = ?
            AND cantidad >= ?
        """, (cantidad, almacen_id, producto_codigo, cantidad))
        return cursor.rowcount
    
    @staticmethod
    def eliminar_producto(conn: sqlite3.Connection, almacen_id: int, producto_codigo: str) -> int:
        """Elimina un producto del inventario de un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Inventario_Almacen
            WHERE almacen_id = ? AND producto_codigo = ?
        """, (almacen_id, producto_codigo))
        return cursor.rowcount


class MovimientoInventarioRepository:
    """Repositorio para operaciones con movimientos de inventario."""
    
    @staticmethod
    def crear(conn: sqlite3.Connection, tipo: str, origen_tipo: str, origen_id: int,
              producto_codigo: str, cantidad: float, user_id: int,
              destino_tipo: Optional[str] = None, destino_id: Optional[int] = None,
              descripcion: Optional[str] = None) -> int:
        """Crea un nuevo movimiento de inventario."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Movimientos_Inventario 
            (tipo, origen_tipo, origen_id, destino_tipo, destino_id, producto_codigo, cantidad, user_id, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tipo, origen_tipo, origen_id, destino_tipo, destino_id, producto_codigo, cantidad, user_id, descripcion))
        return cursor.lastrowid
    
    @staticmethod
    def obtener_por_almacen(conn: sqlite3.Connection, almacen_id: int, limite: int = 50) -> List[sqlite3.Row]:
        """Obtiene los movimientos relacionados con un almacén."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                mi.id,
                mi.fecha,
                mi.tipo,
                mi.origen_tipo,
                mi.origen_id,
                mi.destino_tipo,
                mi.destino_id,
                mi.producto_codigo,
                mi.cantidad,
                mi.user_id,
                mi.descripcion,
                p.nombre as producto_nombre
            FROM Movimientos_Inventario mi
            JOIN Productos p ON mi.producto_codigo = p.codigo
            WHERE (mi.origen_tipo = 'almacen' AND mi.origen_id = ?)
               OR (mi.destino_tipo = 'almacen' AND mi.destino_id = ?)
            ORDER BY mi.fecha DESC
            LIMIT ?
        """, (almacen_id, almacen_id, limite))
        return cursor.fetchall()
    
    @staticmethod
    def obtener_por_contenedor(conn: sqlite3.Connection, contenedor_id: int, limite: int = 50) -> List[sqlite3.Row]:
        """Obtiene los movimientos relacionados con un contenedor."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                mi.id,
                mi.fecha,
                mi.tipo,
                mi.origen_tipo,
                mi.origen_id,
                mi.destino_tipo,
                mi.destino_id,
                mi.producto_codigo,
                mi.cantidad,
                mi.user_id,
                mi.descripcion,
                p.nombre as producto_nombre
            FROM Movimientos_Inventario mi
            JOIN Productos p ON mi.producto_codigo = p.codigo
            WHERE mi.origen_tipo = 'contenedor' AND mi.origen_id = ?
            ORDER BY mi.fecha DESC
            LIMIT ?
        """, (contenedor_id, limite))
        return cursor.fetchall()

