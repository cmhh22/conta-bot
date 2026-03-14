"""
Suppliers service - Business logic for supplier management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import ProveedorRepository

logger = logging.getLogger(__name__)


class ProveedorService:
    """Service for supplier operations."""
    
    @staticmethod
    def create(name: str) -> Dict[str, Any]:
        """Create a new supplier."""
        with get_db_connection() as conn:
            proveedor_id = ProveedorRepository.create(conn, name)
        
        return {"id": proveedor_id, "name": name}
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all suppliers."""
        with get_db_connection() as conn:
            proveedores = ProveedorRepository.obtener_todos(conn)
        
        return [
            {
                "id": row['id'],
                "name": row['name'],
                "fecha_creacion": row['fecha_creacion']
            }
            for row in proveedores
        ]
    
    @staticmethod
    def obtener_por_id(proveedor_id: int) -> Optional[Dict[str, Any]]:
        """Get a supplier by ID."""
        with get_db_connection() as conn:
            proveedor = ProveedorRepository.obtener_por_id(conn, proveedor_id)
        
        if not proveedor:
            return None
        
        return {
            "id": proveedor['id'],
            "name": proveedor['name'],
            "fecha_creacion": proveedor['fecha_creacion']
        }
    
    @staticmethod
    def obtener_por_nombre(name: str) -> Optional[Dict[str, Any]]:
        """Get a supplier by name."""
        with get_db_connection() as conn:
            proveedor = ProveedorRepository.obtener_por_nombre(conn, name)
        
        if not proveedor:
            return None
        
        return {
            "id": proveedor['id'],
            "name": proveedor['name'],
            "fecha_creacion": proveedor['fecha_creacion']
        }
    
    @staticmethod
    def update(proveedor_id: int, nuevo_name: str) -> None:
        """Update a supplier name."""
        with get_db_connection() as conn:
            rows_updated = ProveedorRepository.update(conn, proveedor_id, nuevo_name)
            if rows_updated == 0:
                raise ValueError("Supplier not found")
    
    @staticmethod
    def delete(proveedor_id: int) -> None:
        """Delete a supplier."""
        with get_db_connection() as conn:
            rows_updated = ProveedorRepository.delete(conn, proveedor_id)
            if rows_updated == 0:
                raise ValueError("Supplier not found")

