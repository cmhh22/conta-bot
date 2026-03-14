"""
Warehouses service - Business logic for warehouse management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import WarehouseRepository

logger = logging.getLogger(__name__)


def create(nombre: str, ubicacion: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new warehouse.
    
    Args:
        nombre: Warehouse name (unique)
        ubicacion: Optional warehouse location
    
    Returns:
        Dict with created warehouse data
    
    Raises:
        ValueError: If the name already exists or is invalid
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("Warehouse name cannot be empty")
    
    with get_db_connection() as conn:
        # Check if it already exists
        existente = WarehouseRepository.obtener_por_nombre(conn, nombre)
        if existente:
            raise ValueError(f"A warehouse named '{nombre}' already exists")
        
        warehouse_id = WarehouseRepository.create(conn, nombre, ubicacion)
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        
        return {
            "id": warehouse["id"],
            "nombre": warehouse["nombre"],
            "ubicacion": warehouse["ubicacion"],
            "fecha_creacion": warehouse["fecha_creacion"]
        }


def listar() -> List[Dict[str, Any]]:
    """
    List all warehouses.
    
    Returns:
        List of dictionaries with warehouse data
    """
    with get_db_connection() as conn:
        warehousees = WarehouseRepository.obtener_todos(conn)
        return [
            {
                "id": warehouse["id"],
                "nombre": warehouse["nombre"],
                "ubicacion": warehouse["ubicacion"],
                "fecha_creacion": warehouse["fecha_creacion"]
            }
            for warehouse in warehousees
        ]


def obtener_por_id(warehouse_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a warehouse by ID.
    
    Args:
        warehouse_id: Warehouse ID
    
    Returns:
        Dict with warehouse data or None if it does not exist
    """
    with get_db_connection() as conn:
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            return None
        
        return {
            "id": warehouse["id"],
            "nombre": warehouse["nombre"],
            "ubicacion": warehouse["ubicacion"],
            "fecha_creacion": warehouse["fecha_creacion"]
        }


def obtener_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
    """
    Get a warehouse by name.
    
    Args:
        nombre: Warehouse name
    
    Returns:
        Dict with warehouse data or None if it does not exist
    """
    with get_db_connection() as conn:
        warehouse = WarehouseRepository.obtener_por_nombre(conn, nombre)
        if not warehouse:
            return None
        
        return {
            "id": warehouse["id"],
            "nombre": warehouse["nombre"],
            "ubicacion": warehouse["ubicacion"],
            "fecha_creacion": warehouse["fecha_creacion"]
        }


def update(warehouse_id: int, nuevo_nombre: Optional[str] = None,
               nueva_ubicacion: Optional[str] = None) -> Dict[str, Any]:
    """
    Update a warehouse.
    
    Args:
        warehouse_id: ID of warehouse to update
        nuevo_nombre: New name (optional)
        nueva_ubicacion: New location (optional)
    
    Returns:
        Dict with updated warehouse data
    
    Raises:
        ValueError: If the warehouse does not exist or the new name is already in use
    """
    with get_db_connection() as conn:
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            raise ValueError(f"No warehouse exists with ID {warehouse_id}")
        
        # Check if the new name already exists (if being changed)
        if nuevo_nombre:
            nuevo_nombre = nuevo_nombre.strip()
            if not nuevo_nombre:
                raise ValueError("Warehouse name cannot be empty")
            
            existente = WarehouseRepository.obtener_por_nombre(conn, nuevo_nombre)
            if existente and existente["id"] != warehouse_id:
                raise ValueError(f"A warehouse named '{nuevo_nombre}' already exists")
        
        WarehouseRepository.update(conn, warehouse_id, nuevo_nombre, nueva_ubicacion)
        warehouse_updated = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        
        return {
            "id": warehouse_updated["id"],
            "nombre": warehouse_updated["nombre"],
            "ubicacion": warehouse_updated["ubicacion"],
            "fecha_creacion": warehouse_updated["fecha_creacion"]
        }


def delete(warehouse_id: int) -> bool:
    """
    Delete a warehouse.
    
    Args:
        warehouse_id: ID of warehouse to delete
    
    Returns:
        True if deletion was successful
    
    Raises:
        ValueError: If the warehouse does not exist
    """
    with get_db_connection() as conn:
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            raise ValueError(f"No warehouse exists with ID {warehouse_id}")
        
        WarehouseRepository.delete(conn, warehouse_id)
        return True

