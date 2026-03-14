"""
Servicio de cajas - Lógica de negocio para gestión de cajas.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import CajaRepository, MovimientoRepository
from core.config import VALID_MONEDAS

logger = logging.getLogger(__name__)


class CajaService:
    """Servicio para operaciones con cajas."""
    
    @staticmethod
    def crear(nombre: str, descripcion: Optional[str] = None) -> Dict[str, Any]:
        """Crea una nueva caja."""
        with get_db_connection() as conn:
            # Verificar si ya existe una caja con ese nombre
            caja_existente = CajaRepository.obtener_por_nombre(conn, nombre)
            if caja_existente:
                raise ValueError(f"Ya existe una caja con el nombre '{nombre}'")
            
            caja_id = CajaRepository.crear(conn, nombre, descripcion)
        
        return {"id": caja_id, "nombre": nombre, "descripcion": descripcion}
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Obtiene todas las cajas con sus saldos por moneda."""
        with get_db_connection() as conn:
            cajas = CajaRepository.obtener_todos(conn)
            
            resultado = []
            for row in cajas:
                caja_id = row['id']
                # Obtener saldos por moneda
                saldos = {}
                for moneda in VALID_MONEDAS:
                    saldo = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
                    if saldo != 0:  # Solo incluir monedas con saldo diferente de 0
                        saldos[moneda] = saldo
                
                resultado.append({
                    "id": caja_id,
                    "nombre": row['nombre'],
                    "descripcion": row['descripcion'],
                    "fecha_creacion": row['fecha_creacion'],
                    "saldos": saldos
                })
            
            return resultado
    
    @staticmethod
    def obtener_por_id(caja_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene una caja por su ID con sus saldos por moneda."""
        with get_db_connection() as conn:
            caja = CajaRepository.obtener_por_id(conn, caja_id)
            
            if not caja:
                return None
            
            # Obtener saldos por moneda
            saldos = {}
            for moneda in VALID_MONEDAS:
                saldo = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
                saldos[moneda] = saldo
            
            return {
                "id": caja['id'],
                "nombre": caja['nombre'],
                "descripcion": caja['descripcion'],
                "fecha_creacion": caja['fecha_creacion'],
                "saldos": saldos
            }
    
    @staticmethod
    def obtener_por_nombre(nombre: str) -> Optional[Dict[str, Any]]:
        """Obtiene una caja por su nombre."""
        with get_db_connection() as conn:
            caja = CajaRepository.obtener_por_nombre(conn, nombre)
        
        if not caja:
            return None
        
        return {
            "id": caja['id'],
            "nombre": caja['nombre'],
            "descripcion": caja['descripcion'],
            "fecha_creacion": caja['fecha_creacion']
        }
    
    @staticmethod
    def actualizar(caja_id: int, nuevo_nombre: str, nueva_descripcion: Optional[str] = None) -> None:
        """Actualiza una caja."""
        with get_db_connection() as conn:
            # Verificar si el nuevo nombre ya existe en otra caja
            caja_existente = CajaRepository.obtener_por_nombre(conn, nuevo_nombre)
            if caja_existente and caja_existente['id'] != caja_id:
                raise ValueError(f"Ya existe una caja con el nombre '{nuevo_nombre}'")
            
            rows_updated = CajaRepository.actualizar(conn, caja_id, nuevo_nombre, nueva_descripcion)
            if rows_updated == 0:
                raise ValueError("Caja no encontrada")
    
    @staticmethod
    def eliminar(caja_id: int) -> None:
        """Elimina una caja."""
        with get_db_connection() as conn:
            # Verificar si la caja tiene movimientos asociados
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Movimientos WHERE caja_id = ?", (caja_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                raise ValueError(
                    f"No se puede eliminar la caja porque tiene {count} movimiento(s) asociado(s). "
                    "Primero elimina o mueve los movimientos."
                )
            
            rows_updated = CajaRepository.eliminar(conn, caja_id)
            if rows_updated == 0:
                raise ValueError("Caja no encontrada")

