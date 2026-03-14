"""
Servicio para operaciones con cajas externas.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import CajaExternaRepository

logger = logging.getLogger(__name__)


class CajaExternaService:
    """Servicio para operaciones con cajas externas."""
    
    @staticmethod
    def crear(nombre: str, ubicacion: str, descripcion: Optional[str] = None,
              porcentaje_envio: float = 0) -> Dict[str, Any]:
        """Crea una nueva caja externa."""
        with get_db_connection() as conn:
            caja_id = CajaExternaRepository.crear(conn, nombre, ubicacion, descripcion, porcentaje_envio)
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
        """Obtiene todas las cajas externas."""
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
        """Obtiene una caja externa por su ID."""
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
        """Obtiene una caja externa por su nombre."""
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
    def actualizar(caja_externa_id: int, nuevo_nombre: str, nueva_ubicacion: str,
                   nueva_descripcion: Optional[str] = None,
                   nuevo_porcentaje_envio: Optional[float] = None) -> int:
        """Actualiza una caja externa."""
        with get_db_connection() as conn:
            return CajaExternaRepository.actualizar(
                conn, caja_externa_id, nuevo_nombre, nueva_ubicacion,
                nueva_descripcion, nuevo_porcentaje_envio
            )
    
    @staticmethod
    def eliminar(caja_externa_id: int) -> int:
        """Elimina una caja externa."""
        with get_db_connection() as conn:
            return CajaExternaRepository.eliminar(conn, caja_externa_id)

