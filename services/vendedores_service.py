"""
Servicio de vendedores - Lógica de negocio para gestión de vendedores.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import VendedorRepository

logger = logging.getLogger(__name__)


class VendedorService:
    """Servicio para operaciones con vendedores."""
    
    @staticmethod
    def crear(name: str) -> Dict[str, Any]:
        """Crea un nuevo vendedor."""
        with get_db_connection() as conn:
            vendedor_id = VendedorRepository.crear(conn, name)
        
        return {"id": vendedor_id, "name": name}
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Obtiene todos los vendedores."""
        with get_db_connection() as conn:
            vendedores = VendedorRepository.obtener_todos(conn)
        
        return [
            {
                "id": row['id'],
                "name": row['name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in vendedores
        ]
    
    @staticmethod
    def obtener_por_id(vendedor_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un vendedor por su ID."""
        with get_db_connection() as conn:
            vendedor = VendedorRepository.obtener_por_id(conn, vendedor_id)
        
        if not vendedor:
            return None
        
        return {
            "id": vendedor['id'],
            "name": vendedor['name'],
            "fecha_creacion": vendedor['fecha_creacion']
        }
    
    @staticmethod
    def obtener_por_nombre(name: str) -> Optional[Dict[str, Any]]:
        """Obtiene un vendedor por su nombre."""
        with get_db_connection() as conn:
            vendedor = VendedorRepository.obtener_por_nombre(conn, name)
        
        if not vendedor:
            return None
        
        return {
            "id": vendedor['id'],
            "name": vendedor['name'],
            "fecha_creacion": vendedor['fecha_creacion']
        }
    
    @staticmethod
    def actualizar(vendedor_id: int, nuevo_name: str) -> None:
        """Actualiza el nombre de un vendedor."""
        with get_db_connection() as conn:
            rows_updated = VendedorRepository.actualizar(conn, vendedor_id, nuevo_name)
            if rows_updated == 0:
                raise ValueError("Vendedor no encontrado")
    
    @staticmethod
    def eliminar(vendedor_id: int) -> None:
        """Elimina un vendedor."""
        with get_db_connection() as conn:
            rows_updated = VendedorRepository.eliminar(conn, vendedor_id)
            if rows_updated == 0:
                raise ValueError("Vendedor no encontrado")

