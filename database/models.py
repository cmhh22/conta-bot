"""
Modelos de datos y esquemas de base de datos.
"""
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime


def setup_database(conn: sqlite3.Connection) -> None:
    """
    Crea todas las tablas necesarias si no existen.
    """
    cursor = conn.cursor()
    
    # Tabla Cajas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Cajas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Cajas_Externas (cajas fuera de Cuba, ej: USA)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Cajas_Externas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            ubicacion TEXT NOT NULL,
            descripcion TEXT,
            porcentaje_envio REAL NOT NULL DEFAULT 0 CHECK (porcentaje_envio >= 0 AND porcentaje_envio <= 100),
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Movimientos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'traspaso', 'venta', 'consignment_finalizada')),
            monto REAL NOT NULL CHECK (monto >= 0),
            moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
            caja_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(caja_id) REFERENCES Cajas(id) ON DELETE RESTRICT
        )
    """)
    
    # Tabla Productos
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
    
    # Tabla Deudas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Deudas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actor_id TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('POR_PAGAR', 'POR_COBRAR')),
            monto_pendiente REAL NOT NULL CHECK (monto_pendiente >= 0),
            moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
            UNIQUE(actor_id, moneda, tipo)
        )
    """)
    
    # Tabla Deudas_Productos (relacion de deudas con productos especificos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Deudas_Productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deuda_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad > 0),
            costo_unitario REAL NOT NULL CHECK (costo_unitario >= 0),
            monto_total REAL NOT NULL CHECK (monto_total >= 0),
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(deuda_id) REFERENCES Deudas(id) ON DELETE CASCADE,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT
        )
    """)
    
    # Tabla Consignaciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Consignaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            stock REAL NOT NULL CHECK (stock >= 0),
            precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
            moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
            fecha_consignment TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(codigo, vendedor)
        )
    """)
    
    # Tabla Supplieres
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Supplieres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Selleres
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Selleres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Containeres
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Containeres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            numero_container TEXT,
            proveedor_id INTEGER,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(proveedor_id) REFERENCES Supplieres(id) ON DELETE SET NULL
        )
    """)
    
    # Tabla Warehousees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Warehousees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            ubicacion TEXT,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Container_Productos (relacion muchos a muchos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Container_Productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad >= 0),
            fecha_ingreso TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(container_id) REFERENCES Containeres(id) ON DELETE CASCADE,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(container_id, producto_codigo)
        )
    """)
    
    # Tabla Inventario_Warehouse (inventario por warehouse)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Inventario_Warehouse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warehouse_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad >= 0),
            fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(warehouse_id) REFERENCES Warehousees(id) ON DELETE CASCADE,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(warehouse_id, producto_codigo)
        )
    """)
    
    # Tabla Movimientos_Inventario (transaction history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movimientos_Inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL CHECK (tipo IN ('container_a_warehouse', 'warehouse_a_warehouse', 'ajuste', 'venta_warehouse')),
            source_tipo TEXT NOT NULL CHECK (source_tipo IN ('container', 'warehouse')),
            source_id INTEGER NOT NULL,
            destination_tipo TEXT CHECK (destination_tipo IN ('warehouse', NULL)),
            destination_id INTEGER,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad > 0),
            user_id INTEGER NOT NULL,
            descripcion TEXT,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT
        )
    """)
    
    # Tabla Transferencias_Externas (transferencias a cajas externas con producto especifico)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transferencias_Externas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            caja_source_id INTEGER NOT NULL,
            caja_externa_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            monto REAL NOT NULL CHECK (monto >= 0),
            moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
            porcentaje_envio REAL NOT NULL CHECK (porcentaje_envio >= 0 AND porcentaje_envio <= 100),
            monto_envio REAL NOT NULL CHECK (monto_envio >= 0),
            monto_recibido REAL NOT NULL CHECK (monto_recibido >= 0),
            user_id INTEGER NOT NULL,
            descripcion TEXT,
            FOREIGN KEY(caja_source_id) REFERENCES Cajas(id) ON DELETE RESTRICT,
            FOREIGN KEY(caja_externa_id) REFERENCES Cajas_Externas(id) ON DELETE RESTRICT,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT
        )
    """)
    
    conn.commit()

