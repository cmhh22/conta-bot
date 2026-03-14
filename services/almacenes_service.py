"""
Servicio de almacenes - Lógica de negocio para gestión de almacenes.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import AlmacenRepository

logger = logging.getLogger(__name__)


def crear(nombre: str, ubicacion: Optional[str] = None) -> Dict[str, Any]:
    """
    Crea un nuevo almacén.
    
    Args:
        nombre: Nombre del almacén (único)
        ubicacion: Ubicación opcional del almacén
    
    Returns:
        Dict con los datos del almacén creado
    
    Raises:
        ValueError: Si el nombre ya existe o es inválido
    """
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del almacén no puede estar vacío")
    
    with get_db_connection() as conn:
        # Verificar si ya existe
        existente = AlmacenRepository.obtener_por_nombre(conn, nombre)
        if existente:
            raise ValueError(f"Ya existe un almacén con el nombre '{nombre}'")
        
        almacen_id = AlmacenRepository.crear(conn, nombre, ubicacion)
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        
        return {
            "id": almacen["id"],
            "nombre": almacen["nombre"],
            "ubicacion": almacen["ubicacion"],
            "fecha_creacion": almacen["fecha_creacion"]
        }


def listar() -> List[Dict[str, Any]]:
    """
    Lista todos los almacenes.
    
    Returns:
        Lista de diccionarios con los datos de los almacenes
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
    Obtiene un almacén por su ID.
    
    Args:
        almacen_id: ID del almacén
    
    Returns:
        Dict con los datos del almacén o None si no existe
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
    Obtiene un almacén por su nombre.
    
    Args:
        nombre: Nombre del almacén
    
    Returns:
        Dict con los datos del almacén o None si no existe
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


def actualizar(almacen_id: int, nuevo_nombre: Optional[str] = None,
               nueva_ubicacion: Optional[str] = None) -> Dict[str, Any]:
    """
    Actualiza un almacén.
    
    Args:
        almacen_id: ID del almacén a actualizar
        nuevo_nombre: Nuevo nombre (opcional)
        nueva_ubicacion: Nueva ubicación (opcional)
    
    Returns:
        Dict con los datos actualizados del almacén
    
    Raises:
        ValueError: Si el almacén no existe o el nuevo nombre ya está en uso
    """
    with get_db_connection() as conn:
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No existe un almacén con ID {almacen_id}")
        
        # Verificar si el nuevo nombre ya existe (si se está cambiando)
        if nuevo_nombre:
            nuevo_nombre = nuevo_nombre.strip()
            if not nuevo_nombre:
                raise ValueError("El nombre del almacén no puede estar vacío")
            
            existente = AlmacenRepository.obtener_por_nombre(conn, nuevo_nombre)
            if existente and existente["id"] != almacen_id:
                raise ValueError(f"Ya existe un almacén con el nombre '{nuevo_nombre}'")
        
        AlmacenRepository.actualizar(conn, almacen_id, nuevo_nombre, nueva_ubicacion)
        almacen_actualizado = AlmacenRepository.obtener_por_id(conn, almacen_id)
        
        return {
            "id": almacen_actualizado["id"],
            "nombre": almacen_actualizado["nombre"],
            "ubicacion": almacen_actualizado["ubicacion"],
            "fecha_creacion": almacen_actualizado["fecha_creacion"]
        }


def eliminar(almacen_id: int) -> bool:
    """
    Elimina un almacén.
    
    Args:
        almacen_id: ID del almacén a eliminar
    
    Returns:
        True si se eliminó correctamente
    
    Raises:
        ValueError: Si el almacén no existe
    """
    with get_db_connection() as conn:
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No existe un almacén con ID {almacen_id}")
        
        AlmacenRepository.eliminar(conn, almacen_id)
        return True

