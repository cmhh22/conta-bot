"""
Sellers service - Business logic for seller management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import VendedorRepository

logger = logging.getLogger(__name__)


class VendedorService:
    """Service for seller operations."""
    
    @staticmethod
    def create(name: str) -> Dict[str, Any]:
        """Create a new seller."""
        with get_db_connection() as conn:
            vendedor_id = VendedorRepository.create(conn, name)
        
        return {"id": vendedor_id, "name": name}
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all sellers."""
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
        """Get a seller by ID."""
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
        """Get a seller by name."""
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
    def update(vendedor_id: int, nuevo_name: str) -> None:
        """Update a seller name."""
        with get_db_connection() as conn:
            rows_updated = VendedorRepository.update(conn, vendedor_id, nuevo_name)
            if rows_updated == 0:
                raise ValueError("Seller not found")
    
    @staticmethod
    def delete(vendedor_id: int) -> None:
        """Delete a seller."""
        with get_db_connection() as conn:
            rows_updated = VendedorRepository.delete(conn, vendedor_id)
            if rows_updated == 0:
                raise ValueError("Seller not found")

