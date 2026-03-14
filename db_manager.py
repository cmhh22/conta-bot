import sqlite3
import logging

# Logging configuration (if you had it in bot.py, copy it here)
logger = logging.getLogger(__name__)

def setup_database():
    """Create the DB and the 'Movimientos' and 'Productos' tables if they do not exist."""
    conn = sqlite3.connect("contabilidad.db") 
    cursor = conn.cursor()
    
    # Movimientos table (fixed: removed 'N/A' from the box constraint)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'traspaso', 'venta', 'consignment_finalizada')),
        monto REAL NOT NULL CHECK (monto >= 0),
        moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
        caja TEXT NOT NULL CHECK (caja IN ('cfg', 'sc', 'trd')), 
        user_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL DEFAULT ''
    )
    """)
    
    # 🌟 NEW TABLE: Productos (with moneda_costo column) 
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
    
    # 🌟 NEW TABLE: Deudas (Accounts Payable and Accounts Receivable)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actor_id TEXT NOT NULL,         -- Seller or Supplier ID (e.g.: 'PEDRO', 'MARIA')
        tipo TEXT NOT NULL CHECK (tipo IN ('POR_PAGAR', 'POR_COBRAR')),
        monto_pendiente REAL NOT NULL CHECK (monto_pendiente >= 0),   -- Debt balance
        moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
        UNIQUE(actor_id, moneda, tipo)   -- One actor can have only one debt per currency and type
    )
    """)
    
    # **Add/verify Consignaciones table**
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Consignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            stock REAL NOT NULL CHECK (stock >= 0),
            precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
            moneda TEXT NOT NULL,
            fecha_consignment TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(codigo, vendedor)
        )
    """)
    
    # 🌟 NEW TABLE: Containeres (unique name only)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Containeres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    conn.commit()
    conn.close()