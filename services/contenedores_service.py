"""
Containers service - Business logic for container management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import ContenedorRepository

logger = logging.getLogger(__name__)


class ContenedorService:
    """Service for container operations."""
    
    @staticmethod
    def create(nombre: str, numero_contenedor: Optional[str] = None, proveedor_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new container."""
        with get_db_connection() as conn:
            cont_id = ContenedorRepository.create(conn, nombre, numero_contenedor, proveedor_id)
        
        return {
            "id": cont_id, 
            "nombre": nombre,
            "numero_contenedor": numero_contenedor,
            "proveedor_id": proveedor_id
        }
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all containers with supplier information."""
        with get_db_connection() as conn:
            contenedores = ContenedorRepository.obtener_todos(conn)
        
        return [
            {
                "id": row['id'],
                "nombre": row['nombre'],
                "numero_contenedor": row['numero_contenedor'],
                "proveedor_id": row['proveedor_id'],
                "proveedor_name": row['proveedor_name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in contenedores
        ]
    
    @staticmethod
    def obtener_por_id(cont_id: int) -> Optional[Dict[str, Any]]:
        """Get a container by ID with supplier information."""
        with get_db_connection() as conn:
            contenedor = ContenedorRepository.obtener_por_id(conn, cont_id)
        
        if not contenedor:
            return None
        
        return {
            "id": contenedor['id'],
            "nombre": contenedor['nombre'],
            "numero_contenedor": contenedor['numero_contenedor'],
            "proveedor_id": contenedor['proveedor_id'],
            "proveedor_name": contenedor['proveedor_name'],
            "fecha_creacion": contenedor['fecha_creacion']
        }
    
    @staticmethod
    def update(cont_id: int, nuevo_nombre: Optional[str] = None, 
                   numero_contenedor: Optional[str] = None, 
                   proveedor_id: Optional[int] = None,
                   quitar_proveedor: bool = False) -> None:
        """Update a container.
        
        Args:
            quitar_proveedor: If True, remove the supplier from the container (set proveedor_id to NULL)
        """
        with get_db_connection() as conn:
            rows_updated = ContenedorRepository.update(
                conn, cont_id, nuevo_nombre, numero_contenedor, proveedor_id, quitar_proveedor
            )
            if rows_updated == 0:
                raise ValueError("Container not found")
    
    @staticmethod
    def delete(cont_id: int) -> None:
        """Delete a container."""
        with get_db_connection() as conn:
            rows_updated = ContenedorRepository.delete(conn, cont_id)
            if rows_updated == 0:
                raise ValueError("Container not found")
    
    @staticmethod
    def obtener_por_proveedor(proveedor_id: int) -> List[Dict[str, Any]]:
        """Get all containers associated with one supplier (many-to-one relationship)."""
        with get_db_connection() as conn:
            contenedores = ContenedorRepository.obtener_por_proveedor(conn, proveedor_id)
        
        return [
            {
                "id": row['id'],
                "nombre": row['nombre'],
                "numero_contenedor": row['numero_contenedor'],
                "proveedor_id": row['proveedor_id'],
                "proveedor_name": row['proveedor_name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in contenedores
        ]

