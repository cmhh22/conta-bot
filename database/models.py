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
            tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'traspaso', 'venta', 'consignacion_finalizada')),
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
    
    # Tabla Deudas_Productos (relación de deudas con productos específicos)
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
            fecha_consignacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(codigo, vendedor)
        )
    """)
    
    # Tabla Proveedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Vendedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Vendedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Contenedores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Contenedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            numero_contenedor TEXT,
            proveedor_id INTEGER,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(proveedor_id) REFERENCES Proveedores(id) ON DELETE SET NULL
        )
    """)
    
    # Tabla Almacenes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Almacenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            ubicacion TEXT,
            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla Contenedor_Productos (relación muchos a muchos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Contenedor_Productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contenedor_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad >= 0),
            fecha_ingreso TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(contenedor_id) REFERENCES Contenedores(id) ON DELETE CASCADE,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(contenedor_id, producto_codigo)
        )
    """)
    
    # Tabla Inventario_Almacen (inventario por almacén)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Inventario_Almacen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            almacen_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad >= 0),
            fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(almacen_id) REFERENCES Almacenes(id) ON DELETE CASCADE,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT,
            UNIQUE(almacen_id, producto_codigo)
        )
    """)
    
    # Tabla Movimientos_Inventario (historial de movimientos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Movimientos_Inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            tipo TEXT NOT NULL CHECK (tipo IN ('contenedor_a_almacen', 'almacen_a_almacen', 'ajuste', 'venta_almacen')),
            origen_tipo TEXT NOT NULL CHECK (origen_tipo IN ('contenedor', 'almacen')),
            origen_id INTEGER NOT NULL,
            destino_tipo TEXT CHECK (destino_tipo IN ('almacen', NULL)),
            destino_id INTEGER,
            producto_codigo TEXT NOT NULL,
            cantidad REAL NOT NULL CHECK (cantidad > 0),
            user_id INTEGER NOT NULL,
            descripcion TEXT,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT
        )
    """)
    
    # Tabla Transferencias_Externas (transferencias a cajas externas con producto específico)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transferencias_Externas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            caja_origen_id INTEGER NOT NULL,
            caja_externa_id INTEGER NOT NULL,
            producto_codigo TEXT NOT NULL,
            monto REAL NOT NULL CHECK (monto >= 0),
            moneda TEXT NOT NULL CHECK (moneda IN ('usd', 'cup', 'cup-t', 'eur')),
            porcentaje_envio REAL NOT NULL CHECK (porcentaje_envio >= 0 AND porcentaje_envio <= 100),
            monto_envio REAL NOT NULL CHECK (monto_envio >= 0),
            monto_recibido REAL NOT NULL CHECK (monto_recibido >= 0),
            user_id INTEGER NOT NULL,
            descripcion TEXT,
            FOREIGN KEY(caja_origen_id) REFERENCES Cajas(id) ON DELETE RESTRICT,
            FOREIGN KEY(caja_externa_id) REFERENCES Cajas_Externas(id) ON DELETE RESTRICT,
            FOREIGN KEY(producto_codigo) REFERENCES Productos(codigo) ON DELETE RESTRICT
        )
    """)
    
    conn.commit()

