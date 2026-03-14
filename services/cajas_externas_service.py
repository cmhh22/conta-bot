"""
Service for external cash box operations.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import CajaExternaRepository

logger = logging.getLogger(__name__)


class CajaExternaService:
    """Service for external cash box operations."""
    
    @staticmethod
    def create(nombre: str, ubicacion: str, descripcion: Optional[str] = None,
              porcentaje_envio: float = 0) -> Dict[str, Any]:
        """Create a new external cash box."""
        with get_db_connection() as conn:
            caja_id = CajaExternaRepository.create(conn, nombre, ubicacion, descripcion, porcentaje_envio)
            caja = CajaExternaRepository.obtener_por_id(conn, caja_id)
        
        return {
            "id": caja['id'],
            "nombre": caja['nombre'],
            "ubicacion": caja['ubicacion'],
            "descripcion": caja['descripcion'],
            "porcentaje_envio": caja['porcentaje_envio'],
            "fecha_creacion": caja['fecha_creacion']
        }
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all external cash boxes."""
        with get_db_connection() as conn:
            cajas = CajaExternaRepository.obtener_todos(conn)
        
        return [
            {
                "id": row['id'],
                "nombre": row['nombre'],
                "ubicacion": row['ubicacion'],
                "descripcion": row['descripcion'],
                "porcentaje_envio": row['porcentaje_envio'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in cajas
        ]
    
    @staticmethod
    def obtener_por_id(caja_externa_id: int) -> Optional[Dict[str, Any]]:
        """Get an external cash box by ID."""
        with get_db_connection() as conn:
            caja = CajaExternaRepository.obtener_por_id(conn, caja_externa_id)
        
        if not caja:
            return None
        
        return {
            "id": caja['id'],
            "nombre": caja['nombre'],
            "ubicacion": caja['ubicacion'],
            "descripcion": caja['descripcion'],
            "porcentaje_envio": caja['porcentaje_envio'],
            "fecha_creacion": caja['fecha_creacion']
        }
    
    @staticmethod
    def obtener_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
        """Get an external cash box by name."""
        with get_db_connection() as conn:
            caja = CajaExternaRepository.obtener_por_nombre(conn, nombre)
        
        if not caja:
            return None
        
        return {
            "id": caja['id'],
            "nombre": caja['nombre'],
            "ubicacion": caja['ubicacion'],
            "descripcion": caja['descripcion'],
            "porcentaje_envio": caja['porcentaje_envio'],
            "fecha_creacion": caja['fecha_creacion']
        }
    
    @staticmethod
    def update(caja_externa_id: int, nuevo_nombre: str, nueva_ubicacion: str,
                   nueva_descripcion: Optional[str] = None,
                   nuevo_porcentaje_envio: Optional[float] = None) -> int:
        """Update an external cash box."""
        with get_db_connection() as conn:
            return CajaExternaRepository.update(
                conn, caja_externa_id, nuevo_nombre, nueva_ubicacion,
                nueva_descripcion, nuevo_porcentaje_envio
            )
    
    @staticmethod
    def delete(caja_externa_id: int) -> int:
        """Delete an external cash box."""
        with get_db_connection() as conn:
            return CajaExternaRepository.delete(conn, caja_externa_id)

