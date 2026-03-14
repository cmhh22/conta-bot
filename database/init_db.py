"""
Inicializacion de la base de datos.
"""
import logging
from database.connection import get_db_connection
from database.models import setup_database
from database.migrations import migrate_database

logger = logging.getLogger(__name__)


def initialize_database() -> None:
    """Inicializa la base de datos creando todas las tablas necesarias y ejecutando migraciones."""
    try:
        with get_db_connection() as conn:
            setup_database(conn)
        logger.info("Base de datos inicializada correctamente.")
        
        # Ejecutar migraciones para bases de datos existentes
        try:
            migrate_database()
        except Exception as e:
            logger.warning(f"Error durante migracion (puede ser normal si la BD es nueva): {e}")
            
    except Exception as e:
        logger.error(f"Error while inicializar la base de datos: {e}", exc_info=True)
        raise

