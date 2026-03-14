"""
Script de migracion para update la base de datos existente.
Ejecuta este script una vez para agregar las nuevas tablas y columnas.
"""
import sqlite3
import logging
from database.connection import get_db_connection
from core.config import DB_NAME

logger = logging.getLogger(__name__)


def migrate_database() -> None:
    """Migra la base de datos agregando nuevas tablas y columnas."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la tabla Supplieres existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Supplieres'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Supplieres...")
                cursor.execute("""
                    CREATE TABLE Supplieres (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Supplieres created.")
            else:
                logger.info("Tabla Supplieres ya existe.")
            
            # Verificar si la columna numero_container existe en Containeres
            cursor.execute("PRAGMA table_info(Containeres)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'numero_container' not in columns:
                logger.info("Agregando columna numero_container a Containeres...")
                cursor.execute("""
                    ALTER TABLE Containeres 
                    ADD COLUMN numero_container TEXT
                """)
                logger.info("Columna numero_container agregada.")
            else:
                logger.info("Columna numero_container ya existe.")
            
            if 'proveedor_id' not in columns:
                logger.info("Agregando columna proveedor_id a Containeres...")
                # SQLite no soporta ADD COLUMN con FOREIGN KEY directamente
                # Necesitamos recreate la tabla
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Containeres_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        numero_container TEXT,
                        proveedor_id INTEGER,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(proveedor_id) REFERENCES Supplieres(id) ON DELETE SET NULL
                    )
                """)
                
                # Copiar datos existentes
                cursor.execute("""
                    INSERT INTO Containeres_new (id, nombre, fecha_creacion)
                    SELECT id, nombre, fecha_creacion FROM Containeres
                """)
                
                # Delete tabla antigua
                cursor.execute("DROP TABLE Containeres")
                
                # Renombrar tabla nueva
                cursor.execute("ALTER TABLE Containeres_new RENAME TO Containeres")
                
                logger.info("Columna proveedor_id agregada con relacion FOREIGN KEY.")
            else:
                logger.info("Columna proveedor_id ya existe.")
                # Verificar si tiene restriccion UNIQUE y deletela si existe
                # SQLite no permite delete UNIQUE directamente, necesitamos recreate la tabla
                cursor.execute("""
                    SELECT sql FROM sqlite_master 
                    WHERE type='table' AND name='Containeres'
                """)
                table_sql = cursor.fetchone()
                if table_sql and 'proveedor_id INTEGER UNIQUE' in table_sql[0]:
                    logger.info("Eliminando restriccion UNIQUE de proveedor_id para permitir relacion muchos-a-uno...")
                    # Recreate tabla sin UNIQUE
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS Containeres_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT UNIQUE NOT NULL,
                            numero_container TEXT,
                            proveedor_id INTEGER,
                            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(proveedor_id) REFERENCES Supplieres(id) ON DELETE SET NULL
                        )
                    """)
                    
                    # Copiar todos los datos
                    cursor.execute("""
                        INSERT INTO Containeres_new (id, nombre, numero_container, proveedor_id, fecha_creacion)
                        SELECT id, nombre, numero_container, proveedor_id, fecha_creacion FROM Containeres
                    """)
                    
                    # Delete tabla antigua
                    cursor.execute("DROP TABLE Containeres")
                    
                    # Renombrar tabla nueva
                    cursor.execute("ALTER TABLE Containeres_new RENAME TO Containeres")
                    
                    logger.info("Restriccion UNIQUE deleted. Ahora un proveedor puede tener multiples containeres.")
            
            # Verificar si la tabla Warehousees existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Warehousees'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Warehousees...")
                cursor.execute("""
                    CREATE TABLE Warehousees (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        ubicacion TEXT,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Warehousees created.")
            else:
                logger.info("Tabla Warehousees ya existe.")
            
            # Verificar si la tabla Container_Productos existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Container_Productos'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Container_Productos...")
                cursor.execute("""
                    CREATE TABLE Container_Productos (
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
                logger.info("Tabla Container_Productos created.")
            else:
                logger.info("Tabla Container_Productos ya existe.")
            
            # Verificar si la tabla Inventario_Warehouse existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Inventario_Warehouse'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Inventario_Warehouse...")
                cursor.execute("""
                    CREATE TABLE Inventario_Warehouse (
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
                logger.info("Tabla Inventario_Warehouse created.")
            else:
                logger.info("Tabla Inventario_Warehouse ya existe.")
            
            # Verificar si la tabla Movimientos_Inventario existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Movimientos_Inventario'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Movimientos_Inventario...")
                cursor.execute("""
                    CREATE TABLE Movimientos_Inventario (
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
                logger.info("Tabla Movimientos_Inventario created.")
            else:
                logger.info("Tabla Movimientos_Inventario ya existe.")
            
            # Verificar si la tabla Selleres existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Selleres'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Selleres...")
                cursor.execute("""
                    CREATE TABLE Selleres (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Selleres created.")
            else:
                logger.info("Tabla Selleres ya existe.")
            
            # Verificar si la tabla Cajas existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Cajas'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Cajas...")
                cursor.execute("""
                    CREATE TABLE Cajas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        descripcion TEXT,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Cajas created.")
                
                # Insertar cajas por defecto
                cajas_por_defecto = [
                    ('cfg', 'Caja Fisica General'),
                    ('sc', 'Caja Secundaria'),
                    ('trd', 'Caja Tercera')
                ]
                for nombre, descripcion in cajas_por_defecto:
                    cursor.execute("""
                        INSERT INTO Cajas (nombre, descripcion)
                        VALUES (?, ?)
                    """, (nombre, descripcion))
                logger.info("Cajas por defecto insertadas.")
            else:
                logger.info("Tabla Cajas ya existe.")
            
            # Verificar si Movimientos tiene caja_id o caja (TEXT)
            cursor.execute("PRAGMA table_info(Movimientos)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            
            if 'caja_id' not in columns and 'caja' in columns:
                logger.info("Migrando Movimientos de caja (TEXT) a caja_id (INTEGER)...")
                
                # Obtener mapeo de nombres de cajas a IDs
                cursor.execute("SELECT id, nombre FROM Cajas")
                cajas_map = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Create tabla temporal con nueva estructura
                cursor.execute("""
                    CREATE TABLE Movimientos_new (
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
                
                # Copiar datos existentes, mapeando caja (TEXT) a caja_id (INTEGER)
                cursor.execute("SELECT id, fecha, tipo, monto, moneda, caja, user_id, descripcion FROM Movimientos")
                movimientos = cursor.fetchall()
                
                for mov in movimientos:
                    mov_id, fecha, tipo, monto, moneda, caja_nombre, user_id, descripcion = mov
                    caja_id = cajas_map.get(caja_nombre)
                    if caja_id:
                        cursor.execute("""
                            INSERT INTO Movimientos_new (id, fecha, tipo, monto, moneda, caja_id, user_id, descripcion)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (mov_id, fecha, tipo, monto, moneda, caja_id, user_id, descripcion))
                    else:
                        logger.warning(f"Movimiento {mov_id} tiene caja '{caja_nombre}' not found. Usando primera caja disponible.")
                        if cajas_map:
                            primera_caja_id = list(cajas_map.values())[0]
                            cursor.execute("""
                                INSERT INTO Movimientos_new (id, fecha, tipo, monto, moneda, caja_id, user_id, descripcion)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (mov_id, fecha, tipo, monto, moneda, primera_caja_id, user_id, descripcion))
                
                # Delete tabla antigua
                cursor.execute("DROP TABLE Movimientos")
                
                # Renombrar tabla nueva
                cursor.execute("ALTER TABLE Movimientos_new RENAME TO Movimientos")
                
                logger.info("Migracion de Movimientos completada. Ahora usa caja_id (INTEGER).")
            elif 'caja_id' in columns:
                logger.info("Tabla Movimientos ya tiene caja_id. No se requiere migracion.")
            else:
                logger.warning("Tabla Movimientos no tiene ni 'caja' ni 'caja_id'. Verificar estructura.")
            
            # Corregir traspasos mal recordeds (los de destination deben ser 'ingreso', no 'traspaso')
            logger.info("Corrigiendo traspasos mal recordeds...")
            cursor.execute("""
                SELECT id, descripcion, caja_id, monto, moneda
                FROM Movimientos
                WHERE tipo = 'traspaso' 
                AND descripcion LIKE '%TRASPASO (Ingreso)%'
            """)
            traspasos_destination = cursor.fetchall()
            
            if traspasos_destination:
                logger.info(f"Encontrados {len(traspasos_destination)} traspasos de destination a corregir.")
                for mov in traspasos_destination:
                    mov_id = mov[0]
                    cursor.execute("""
                        UPDATE Movimientos
                        SET tipo = 'ingreso'
                        WHERE id = ?
                    """, (mov_id,))
                    logger.info(f"Movimiento {mov_id} corregido: 'traspaso' -> 'ingreso' (Caja {mov[2]}, {mov[4].upper()} {mov[3]:.2f})")
                logger.info("Traspasos de destination corregidos exitosamente.")
            else:
                logger.info("No se encontraron traspasos de destination a corregir.")
            
            # Create tabla Deudas_Productos si no existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Deudas_Productos'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Deudas_Productos...")
                cursor.execute("""
                    CREATE TABLE Deudas_Productos (
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
                logger.info("Tabla Deudas_Productos created.")
            else:
                logger.info("Tabla Deudas_Productos ya existe.")
            
            # Migracion: Agregar EUR a las restricciones CHECK de moneda
            # SQLite no permite modificar CHECK constraints directamente,
            # pero las nuevas tablas ya tienen EUR. Para tablas existentes,
            # las restricciones se aplicaran en nuevas inserciones.
            # Nota: Las tablas existentes seguiran funcionando, pero para aplicar
            # la restriccion completa, se necesitaria recreate las tablas.
            logger.info("Nota: EUR agregado a VALID_MONEDAS. Las nuevas inserciones aceptaran 'eur'.")
            
            # Create tabla Cajas_Externas si no existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Cajas_Externas'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Cajas_Externas...")
                cursor.execute("""
                    CREATE TABLE Cajas_Externas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        ubicacion TEXT NOT NULL,
                        descripcion TEXT,
                        porcentaje_envio REAL NOT NULL DEFAULT 0 CHECK (porcentaje_envio >= 0 AND porcentaje_envio <= 100),
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Cajas_Externas created.")
            else:
                logger.info("Tabla Cajas_Externas ya existe.")
            
            # Create tabla Transferencias_Externas si no existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Transferencias_Externas'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Transferencias_Externas...")
                cursor.execute("""
                    CREATE TABLE Transferencias_Externas (
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
                logger.info("Tabla Transferencias_Externas created.")
            else:
                logger.info("Tabla Transferencias_Externas ya existe.")
            
            conn.commit()
            logger.info("Migracion completada exitosamente.")
            
    except Exception as e:
        logger.error(f"Error durante la migracion: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_database()

