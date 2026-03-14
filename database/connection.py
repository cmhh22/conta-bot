"""
Gestión centralizada de conexiones a la base de datos.
"""
import sqlite3
import logging
from contextlib import contextmanager
from typing import Generator
from core.config import DB_NAME

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager para manejar conexiones a la base de datos de forma segura.
    Garantiza commit en éxito y rollback en error.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        # Habilitar foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Retornar tuplas con nombres de columnas (acceso por nombre)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error en transacción de base de datos: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()

