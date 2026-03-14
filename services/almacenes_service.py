"""
Warehouses service - Business logic for warehouse management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import AlmacenRepository

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
        existente = AlmacenRepository.obtener_por_nombre(conn, nombre)
        if existente:
            raise ValueError(f"A warehouse named '{nombre}' already exists")
        
        almacen_id = AlmacenRepository.create(conn, nombre, ubicacion)
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        
        return {
            "id": almacen["id"],
            "nombre": almacen["nombre"],
            "ubicacion": almacen["ubicacion"],
            "fecha_creacion": almacen["fecha_creacion"]
        }


def listar() -> List[Dict[str, Any]]:
    """
    List all warehouses.
    
    Returns:
        List of dictionaries with warehouse data
    """
    with get_db_connection() as conn:
        almacenes = AlmacenRepository.obtener_todos(conn)
        return [
            {
                "id": almacen["id"],
                "nombre": almacen["nombre"],
                "ubicacion": almacen["ubicacion"],
                "fecha_creacion": almacen["fecha_creacion"]
            }
            for almacen in almacenes
        ]


def obtener_por_id(almacen_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a warehouse by ID.
    
    Args:
        almacen_id: Warehouse ID
    
    Returns:
        Dict with warehouse data or None if it does not exist
    """
    with get_db_connection() as conn:
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            return None
        
        return {
            "id": almacen["id"],
            "nombre": almacen["nombre"],
            "ubicacion": almacen["ubicacion"],
            "fecha_creacion": almacen["fecha_creacion"]
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
        almacen = AlmacenRepository.obtener_por_nombre(conn, nombre)
        if not almacen:
            return None
        
        return {
            "id": almacen["id"],
            "nombre": almacen["nombre"],
            "ubicacion": almacen["ubicacion"],
            "fecha_creacion": almacen["fecha_creacion"]
        }


def update(almacen_id: int, nuevo_nombre: Optional[str] = None,
               nueva_ubicacion: Optional[str] = None) -> Dict[str, Any]:
    """
    Update a warehouse.
    
    Args:
        almacen_id: ID of warehouse to update
        nuevo_nombre: New name (optional)
        nueva_ubicacion: New location (optional)
    
    Returns:
        Dict with updated warehouse data
    
    Raises:
        ValueError: If the warehouse does not exist or the new name is already in use
    """
    with get_db_connection() as conn:
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No warehouse exists with ID {almacen_id}")
        
        # Check if the new name already exists (if being changed)
        if nuevo_nombre:
            nuevo_nombre = nuevo_nombre.strip()
            if not nuevo_nombre:
                raise ValueError("Warehouse name cannot be empty")
            
            existente = AlmacenRepository.obtener_por_nombre(conn, nuevo_nombre)
            if existente and existente["id"] != almacen_id:
                raise ValueError(f"A warehouse named '{nuevo_nombre}' already exists")
        
        AlmacenRepository.update(conn, almacen_id, nuevo_nombre, nueva_ubicacion)
        almacen_updated = AlmacenRepository.obtener_por_id(conn, almacen_id)
        
        return {
            "id": almacen_updated["id"],
            "nombre": almacen_updated["nombre"],
            "ubicacion": almacen_updated["ubicacion"],
            "fecha_creacion": almacen_updated["fecha_creacion"]
        }


def delete(almacen_id: int) -> bool:
    """
    Delete a warehouse.
    
    Args:
        almacen_id: ID of warehouse to delete
    
    Returns:
        True if deletion was successful
    
    Raises:
        ValueError: If the warehouse does not exist
    """
    with get_db_connection() as conn:
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No warehouse exists with ID {almacen_id}")
        
        AlmacenRepository.delete(conn, almacen_id)
        return True

