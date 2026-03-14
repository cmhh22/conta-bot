"""
Servicio de contenedores - Lógica de negocio para gestión de contenedores.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import ContenedorRepository

logger = logging.getLogger(__name__)


class ContenedorService:
    """Servicio para operaciones con contenedores."""
    
    @staticmethod
    def crear(nombre: str, numero_contenedor: Optional[str] = None, proveedor_id: Optional[int] = None) -> Dict[str, Any]:
        """Crea un nuevo contenedor."""
        with get_db_connection() as conn:
            cont_id = ContenedorRepository.crear(conn, nombre, numero_contenedor, proveedor_id)
        
        return {
            "id": cont_id, 
            "nombre": nombre,
            "numero_contenedor": numero_contenedor,
            "proveedor_id": proveedor_id
        }
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Obtiene todos los contenedores con información del proveedor."""
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
        """Obtiene un contenedor por su ID con información del proveedor."""
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
    def actualizar(cont_id: int, nuevo_nombre: Optional[str] = None, 
                   numero_contenedor: Optional[str] = None, 
                   proveedor_id: Optional[int] = None,
                   quitar_proveedor: bool = False) -> None:
        """Actualiza un contenedor.
        
        Args:
            quitar_proveedor: Si es True, quita el proveedor del contenedor (establece proveedor_id a NULL)
        """
        with get_db_connection() as conn:
            rows_updated = ContenedorRepository.actualizar(
                conn, cont_id, nuevo_nombre, numero_contenedor, proveedor_id, quitar_proveedor
            )
            if rows_updated == 0:
                raise ValueError("Contenedor no encontrado")
    
    @staticmethod
    def eliminar(cont_id: int) -> None:
        """Elimina un contenedor."""
        with get_db_connection() as conn:
            rows_updated = ContenedorRepository.eliminar(conn, cont_id)
            if rows_updated == 0:
                raise ValueError("Contenedor no encontrado")
    
    @staticmethod
    def obtener_por_proveedor(proveedor_id: int) -> List[Dict[str, Any]]:
        """Obtiene todos los contenedores asociados a un proveedor (relación muchos a uno)."""
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

