"""
Cash box service - Business logic for cash box management.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import CajaRepository, MovimientoRepository
from core.config import VALID_MONEDAS

logger = logging.getLogger(__name__)


class CajaService:
    """Service for cash box operations."""
    
    @staticmethod
    def create(nombre: str, descripcion: Optional[str] = None) -> Dict[str, Any]:
        """Create a new cash box."""
        with get_db_connection() as conn:
            # Check if a box with that name already exists
            caja_existente = CajaRepository.obtener_por_nombre(conn, nombre)
            if caja_existente:
                raise ValueError(f"A cash box named '{nombre}' already exists")
            
            caja_id = CajaRepository.create(conn, nombre, descripcion)
        
        return {"id": caja_id, "nombre": nombre, "descripcion": descripcion}
    
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        """Get all cash boxes with their balances by currency."""
        with get_db_connection() as conn:
            cajas = CajaRepository.obtener_todos(conn)
            
            resultado = []
            for row in cajas:
                caja_id = row['id']
                # Get balances by currency
                saldos = {}
                for moneda in VALID_MONEDAS:
                    saldo = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
                    if saldo != 0:  # Include only non-zero balances
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
        """Get a cash box by ID with its balances by currency."""
        with get_db_connection() as conn:
            caja = CajaRepository.obtener_por_id(conn, caja_id)
            
            if not caja:
                return None
            
            # Get balances by currency
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
        """Get a cash box by name."""
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
    def update(caja_id: int, nuevo_nombre: str, nueva_descripcion: Optional[str] = None) -> None:
        """Update a cash box."""
        with get_db_connection() as conn:
            # Check if the new name already exists on another box
            caja_existente = CajaRepository.obtener_por_nombre(conn, nuevo_nombre)
            if caja_existente and caja_existente['id'] != caja_id:
                raise ValueError(f"A cash box named '{nuevo_nombre}' already exists")
            
            rows_updated = CajaRepository.update(conn, caja_id, nuevo_nombre, nueva_descripcion)
            if rows_updated == 0:
                raise ValueError("Cash box not found")
    
    @staticmethod
    def delete(caja_id: int) -> None:
        """Delete a cash box."""
        with get_db_connection() as conn:
            # Check whether the box has associated transactions
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Movimientos WHERE caja_id = ?", (caja_id,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                raise ValueError(
                    f"No se puede delete la caja porque tiene {count} movimiento(s) asociado(s). "
                    "Delete or move the transactions first."
                )
            
            rows_updated = CajaRepository.delete(conn, caja_id)
            if rows_updated == 0:
                raise ValueError("Cash box not found")

