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
            
            # Verificar si la tabla Proveedores existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Proveedores'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Proveedores...")
                cursor.execute("""
                    CREATE TABLE Proveedores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Proveedores created.")
            else:
                logger.info("Tabla Proveedores ya existe.")
            
            # Verificar si la columna numero_contenedor existe en Contenedores
            cursor.execute("PRAGMA table_info(Contenedores)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'numero_contenedor' not in columns:
                logger.info("Agregando columna numero_contenedor a Contenedores...")
                cursor.execute("""
                    ALTER TABLE Contenedores 
                    ADD COLUMN numero_contenedor TEXT
                """)
                logger.info("Columna numero_contenedor agregada.")
            else:
                logger.info("Columna numero_contenedor ya existe.")
            
            if 'proveedor_id' not in columns:
                logger.info("Agregando columna proveedor_id a Contenedores...")
                # SQLite no soporta ADD COLUMN con FOREIGN KEY directamente
                # Necesitamos recreate la tabla
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Contenedores_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        numero_contenedor TEXT,
                        proveedor_id INTEGER,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(proveedor_id) REFERENCES Proveedores(id) ON DELETE SET NULL
                    )
                """)
                
                # Copiar datos existentes
                cursor.execute("""
                    INSERT INTO Contenedores_new (id, nombre, fecha_creacion)
                    SELECT id, nombre, fecha_creacion FROM Contenedores
                """)
                
                # Delete tabla antigua
                cursor.execute("DROP TABLE Contenedores")
                
                # Renombrar tabla nueva
                cursor.execute("ALTER TABLE Contenedores_new RENAME TO Contenedores")
                
                logger.info("Columna proveedor_id agregada con relacion FOREIGN KEY.")
            else:
                logger.info("Columna proveedor_id ya existe.")
                # Verificar si tiene restriccion UNIQUE y deletela si existe
                # SQLite no permite delete UNIQUE directamente, necesitamos recreate la tabla
                cursor.execute("""
                    SELECT sql FROM sqlite_master 
                    WHERE type='table' AND name='Contenedores'
                """)
                table_sql = cursor.fetchone()
                if table_sql and 'proveedor_id INTEGER UNIQUE' in table_sql[0]:
                    logger.info("Eliminando restriccion UNIQUE de proveedor_id para permitir relacion muchos-a-uno...")
                    # Recreate tabla sin UNIQUE
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS Contenedores_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nombre TEXT UNIQUE NOT NULL,
                            numero_contenedor TEXT,
                            proveedor_id INTEGER,
                            fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(proveedor_id) REFERENCES Proveedores(id) ON DELETE SET NULL
                        )
                    """)
                    
                    # Copiar todos los datos
                    cursor.execute("""
                        INSERT INTO Contenedores_new (id, nombre, numero_contenedor, proveedor_id, fecha_creacion)
                        SELECT id, nombre, numero_contenedor, proveedor_id, fecha_creacion FROM Contenedores
                    """)
                    
                    # Delete tabla antigua
                    cursor.execute("DROP TABLE Contenedores")
                    
                    # Renombrar tabla nueva
                    cursor.execute("ALTER TABLE Contenedores_new RENAME TO Contenedores")
                    
                    logger.info("Restriccion UNIQUE deleted. Ahora un proveedor puede tener multiples contenedores.")
            
            # Verificar si la tabla Almacenes existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Almacenes'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Almacenes...")
                cursor.execute("""
                    CREATE TABLE Almacenes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre TEXT UNIQUE NOT NULL,
                        ubicacion TEXT,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Almacenes created.")
            else:
                logger.info("Tabla Almacenes ya existe.")
            
            # Verificar si la tabla Contenedor_Productos existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Contenedor_Productos'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Contenedor_Productos...")
                cursor.execute("""
                    CREATE TABLE Contenedor_Productos (
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
                logger.info("Tabla Contenedor_Productos created.")
            else:
                logger.info("Tabla Contenedor_Productos ya existe.")
            
            # Verificar si la tabla Inventario_Almacen existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Inventario_Almacen'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Inventario_Almacen...")
                cursor.execute("""
                    CREATE TABLE Inventario_Almacen (
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
                logger.info("Tabla Inventario_Almacen created.")
            else:
                logger.info("Tabla Inventario_Almacen ya existe.")
            
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
                logger.info("Tabla Movimientos_Inventario created.")
            else:
                logger.info("Tabla Movimientos_Inventario ya existe.")
            
            # Verificar si la tabla Vendedores existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='Vendedores'
            """)
            if not cursor.fetchone():
                logger.info("Creando tabla Vendedores...")
                cursor.execute("""
                    CREATE TABLE Vendedores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                logger.info("Tabla Vendedores created.")
            else:
                logger.info("Tabla Vendedores ya existe.")
            
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
                        tipo TEXT NOT NULL CHECK (tipo IN ('ingreso', 'gasto', 'traspaso', 'venta', 'consignacion_finalizada')),
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
            
            # Corregir traspasos mal registrados (los de destino deben ser 'ingreso', no 'traspaso')
            logger.info("Corrigiendo traspasos mal registrados...")
            cursor.execute("""
                SELECT id, descripcion, caja_id, monto, moneda
                FROM Movimientos
                WHERE tipo = 'traspaso' 
                AND descripcion LIKE '%TRASPASO (Ingreso)%'
            """)
            traspasos_destino = cursor.fetchall()
            
            if traspasos_destino:
                logger.info(f"Encontrados {len(traspasos_destino)} traspasos de destino a corregir.")
                for mov in traspasos_destino:
                    mov_id = mov[0]
                    cursor.execute("""
                        UPDATE Movimientos
                        SET tipo = 'ingreso'
                        WHERE id = ?
                    """, (mov_id,))
                    logger.info(f"Movimiento {mov_id} corregido: 'traspaso' -> 'ingreso' (Caja {mov[2]}, {mov[4].upper()} {mov[3]:.2f})")
                logger.info("Traspasos de destino corregidos exitosamente.")
            else:
                logger.info("No se encontraron traspasos de destino a corregir.")
            
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

