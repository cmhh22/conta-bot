"""
Containers service - Business logic for container management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import ContainerRepository

logger = logging.getLogger(__name__)


class ContainerService:
    """Service for container operations."""
    
    @staticmethod
    def create(nombre: str, numero_container: Optional[str] = None, proveedor_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new container."""
        with get_db_connection() as conn:
            cont_id = ContainerRepository.create(conn, nombre, numero_container, proveedor_id)
        
        return {
            "id": cont_id, 
            "nombre": nombre,
            "numero_container": numero_container,
            "proveedor_id": proveedor_id
        }
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all containers with supplier information."""
        with get_db_connection() as conn:
            containeres = ContainerRepository.obtener_todos(conn)
        
        return [
            {
                "id": row['id'],
                "nombre": row['nombre'],
                "numero_container": row['numero_container'],
                "proveedor_id": row['proveedor_id'],
                "proveedor_name": row['proveedor_name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in containeres
        ]
    
    @staticmethod
    def obtener_por_id(cont_id: int) -> Optional[Dict[str, Any]]:
        """Get a container by ID with supplier information."""
        with get_db_connection() as conn:
            container = ContainerRepository.obtener_por_id(conn, cont_id)
        
        if not container:
            return None
        
        return {
            "id": container['id'],
            "nombre": container['nombre'],
            "numero_container": container['numero_container'],
            "proveedor_id": container['proveedor_id'],
            "proveedor_name": container['proveedor_name'],
            "fecha_creacion": container['fecha_creacion']
        }
    
    @staticmethod
    def update(cont_id: int, nuevo_nombre: Optional[str] = None, 
                   numero_container: Optional[str] = None, 
                   proveedor_id: Optional[int] = None,
                   quitar_proveedor: bool = False) -> None:
        """Update a container.
        
        Args:
            quitar_proveedor: If True, remove the supplier from the container (set proveedor_id to NULL)
        """
        with get_db_connection() as conn:
            rows_updated = ContainerRepository.update(
                conn, cont_id, nuevo_nombre, numero_container, proveedor_id, quitar_proveedor
            )
            if rows_updated == 0:
                raise ValueError("Container not found")
    
    @staticmethod
    def delete(cont_id: int) -> None:
        """Delete a container."""
        with get_db_connection() as conn:
            rows_updated = ContainerRepository.delete(conn, cont_id)
            if rows_updated == 0:
                raise ValueError("Container not found")
    
    @staticmethod
    def obtener_por_proveedor(proveedor_id: int) -> List[Dict[str, Any]]:
        """Get all containers associated with one supplier (many-to-one relationship)."""
        with get_db_connection() as conn:
            containeres = ContainerRepository.obtener_por_proveedor(conn, proveedor_id)
        
        return [
            {
                "id": row['id'],
                "nombre": row['nombre'],
                "numero_container": row['numero_container'],
                "proveedor_id": row['proveedor_id'],
                "proveedor_name": row['proveedor_name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in containeres
        ]

