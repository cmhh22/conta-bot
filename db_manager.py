import sqlite3
import logging

# Configuración de logging (si la tenías en bot.py, cópiala aquí)
logger = logging.getLogger(__name__)

def setup_database():
    """Crea la BD y las tablas 'Movimientos' y 'Productos' si no existen."""
    conn = sqlite3.connect("contabilidad.db") 
    cursor = conn.cursor()
    
    # Tabla Movimientos (Corregida: Eliminado 'N/A' de la restricción de caja)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'traspaso', 'venta', 'consignacion_finalizada')),
        monto REAL NOT NULL CHECK (monto >= 0),
        moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
        caja TEXT NOT NULL CHECK (caja IN ('cfg', 'sc', 'trd')), 
        user_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL DEFAULT ''
    )
    """)
    
    # 🌟 NUEVA TABLA: Productos (con columna moneda_costo) 
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,      
        nombre TEXT NOT NULL,
        costo_unitario REAL NOT NULL CHECK (costo_unitario >= 0),     
        moneda_costo TEXT NOT NULL DEFAULT 'usd',
        precio_venta REAL CHECK (precio_venta IS NULL OR precio_venta >= 0),          
        stock REAL NOT NULL DEFAULT 0 CHECK (stock >= 0)
    )
    """)
    
    # 🌟 NUEVA TABLA: Deudas (Cuentas por Pagar y por Cobrar)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actor_id TEXT NOT NULL,         -- ID del Vendedor o Proveedor (ej: 'PEDRO', 'MARIA')
        tipo TEXT NOT NULL CHECK (tipo IN ('POR_PAGAR', 'POR_COBRAR')),
        monto_pendiente REAL NOT NULL CHECK (monto_pendiente >= 0),   -- El saldo de la deuda
        moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
        UNIQUE(actor_id, moneda, tipo)   -- Un actor solo puede tener una deuda por moneda y tipo
    )
    """)
    
    # **Añadir/Verificar la tabla Consignaciones**
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Consignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            stock REAL NOT NULL CHECK (stock >= 0),
            precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
            moneda TEXT NOT NULL,
            fecha_consignacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(codigo, vendedor)
        )
    """)
    
    # 🌟 NUEVA TABLA: Contenedores (solo nombre único)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Contenedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    conn.commit()
    conn.close()