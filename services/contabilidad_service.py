"""
Accounting service - Business logic for financial transactions.
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from database.connection import get_db_connection
from database.repositories import (
    MovimientoRepository, DeudaRepository
)
from utils.currency import convert_to_usd, convert_currency

logger = logging.getLogger(__name__)


class ContabilidadService:
    """Service for accounting operations."""
    
    @staticmethod
    def registrar_ingreso(monto: float, moneda: str, caja_id: int, user_id: int, 
                         descripcion: str = "Ingreso") -> Dict[str, Any]:
        """Record an income transaction."""
        with get_db_connection() as conn:
            movimiento_id = MovimientoRepository.create(
                conn, 'ingreso', monto, moneda, caja_id, user_id, descripcion
            )
        return {"movimiento_id": movimiento_id, "monto": monto, "moneda": moneda, "caja_id": caja_id}
    
    @staticmethod
    def registrar_gasto(monto: float, moneda: str, caja_id: int, user_id: int, 
                       descripcion: str) -> Dict[str, Any]:
        """Record an expense, validating sufficient balance."""
        with get_db_connection() as conn:
            saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
            
            # Get box name for error message
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            if saldo_actual < monto:
                raise ValueError(
                    f"Insufficient balance in box {caja_nombre.upper()} ({moneda.upper()}). "
                    f"Available: {saldo_actual:.2f} {moneda.upper()}."
                )
            
            movimiento_id = MovimientoRepository.create(
                conn, 'gasto', monto, moneda, caja_id, user_id, descripcion
            )
        
        return {"movimiento_id": movimiento_id, "monto": monto, "moneda": moneda, "caja_id": caja_id}
    
    @staticmethod
    def obtener_balance() -> Dict[str, Dict[str, float]]:
        """Get balance grouped by box and currency."""
        with get_db_connection() as conn:
            resultados = MovimientoRepository.obtener_balance_por_caja(conn)
        
        balances = {}
        for row in resultados:
            caja = row['caja']
            moneda = row['moneda']
            total = row['total']
            
            if caja not in balances:
                balances[caja] = {}
            balances[caja][moneda] = float(total)
        
        return balances
    
    @staticmethod
    def obtener_saldo_caja(caja_id: int, moneda: str) -> float:
        """Get current balance for a box."""
        with get_db_connection() as conn:
            return MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
    
    @staticmethod
    def registrar_traspaso(monto: float, moneda_origen: str, caja_origen_id: int,
                          moneda_destino: str, caja_destino_id: int, user_id: int,
                          motivo: str) -> Dict[str, Any]:
        """Record a transfer between boxes with currency conversion."""
        if caja_origen_id == caja_destino_id and moneda_origen == moneda_destino:
            raise ValueError("Source and destination boxes/currencies cannot be the same.")
        
        with get_db_connection() as conn:
            # Validate sufficient balance
            saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_origen_id, moneda_origen)
            if saldo_actual < monto:
                from services.cajas_service import CajaService
                caja_origen = CajaService.obtener_por_id(caja_origen_id)
                caja_nombre = caja_origen['nombre'] if caja_origen else str(caja_origen_id)
                raise ValueError(
                    f"Insufficient balance in source box {caja_nombre.upper()} "
                    f"({moneda_origen.upper()}). Available: {saldo_actual:.2f} {moneda_origen.upper()}."
                )
            
            # Calculate destination amount
            if moneda_origen == moneda_destino:
                monto_destino = monto
            else:
                monto_destino = convert_currency(monto, moneda_origen, moneda_destino)
            
            # Get box names for description
            from services.cajas_service import CajaService
            caja_origen_obj = CajaService.obtener_por_id(caja_origen_id)
            caja_destino_obj = CajaService.obtener_por_id(caja_destino_id)
            caja_origen_nombre = caja_origen_obj['nombre'] if caja_origen_obj else str(caja_origen_id)
            caja_destino_nombre = caja_destino_obj['nombre'] if caja_destino_obj else str(caja_destino_id)
            
            # Record outgoing movement in source box (type 'traspaso' is subtracted)
            MovimientoRepository.create(
                conn, 'traspaso', monto, moneda_origen, caja_origen_id, user_id,
                f"TRANSFER (Outgoing): To {caja_destino_nombre.upper()}/{moneda_destino.upper()} - Reason: {motivo}"
            )
            
            # Record income in destination box (type 'ingreso' is added)
            MovimientoRepository.create(
                conn, 'ingreso', monto_destino, moneda_destino, caja_destino_id, user_id,
                f"TRANSFER (Incoming): From {caja_origen_nombre.upper()}/{moneda_origen.upper()} - Reason: {motivo}"
            )
        
        return {
            "monto_origen": monto,
            "moneda_origen": moneda_origen,
            "caja_origen_id": caja_origen_id,
            "monto_destino": monto_destino,
            "moneda_destino": moneda_destino,
            "caja_destino_id": caja_destino_id
        }
    
    @staticmethod
    def obtener_historial(dias: int = 7) -> List[Dict[str, Any]]:
        """Get transaction history from the last N days."""
        fecha_desde = datetime.now() - timedelta(days=dias)
        
        with get_db_connection() as conn:
            movimientos = MovimientoRepository.obtener_por_fecha(conn, fecha_desde)
        
        return [
            {
                "fecha": row['fecha'],
                "tipo": row['tipo'],
                "monto": row['monto'],
                "moneda": row['moneda'],
                "caja": row['caja'],
                "descripcion": row['descripcion']
            }
            for row in movimientos
        ]
    
    @staticmethod
    def exportar_movimientos() -> List[Dict[str, Any]]:
        """Export all transactions."""
        with get_db_connection() as conn:
            movimientos = MovimientoRepository.obtener_todos(conn)
        
        return [dict(row) for row in movimientos]


class DeudaService:
    """Service for debt management."""
    
    @staticmethod
    def update_deuda(actor_id: str, monto: float, moneda: str, tipo: str,
                        es_incremento: bool = True) -> float:
        """Update or create a debt."""
        with get_db_connection() as conn:
            deuda = DeudaRepository.obtener_por_actor(conn, actor_id, moneda, tipo)
            
            if deuda:
                monto_actual = deuda['monto_pendiente']
                if es_incremento:
                    nuevo_monto = monto_actual + monto
                else:
                    nuevo_monto = max(0, monto_actual - monto)
                
                DeudaRepository.update_monto(conn, actor_id, moneda, tipo, nuevo_monto)
                return nuevo_monto
            else:
                if not es_incremento:
                    raise ValueError(f"Debt {tipo} for {actor_id} in {moneda} does not exist")
                
                DeudaRepository.create(conn, actor_id, monto, moneda, tipo)
                return monto
    
    @staticmethod
    def liquidar_deuda_vendedor(actor_id: str, monto_pagado: float, 
                               moneda_pago: str) -> float:
        """Settle a POR_COBRAR debt with a payment."""
        # Convert payment to USD (debt base currency)
        monto_liquidado_usd = convert_to_usd(monto_pagado, moneda_pago)
        
        with get_db_connection() as conn:
            deuda = DeudaRepository.obtener_por_actor(conn, actor_id, 'usd', 'POR_COBRAR')
            
            if not deuda:
                logger.warning(f"No POR_COBRAR debt found for {actor_id}")
                return 0.0
            
            nuevo_monto = max(0, deuda['monto_pendiente'] - monto_liquidado_usd)
            DeudaRepository.update_monto(conn, actor_id, 'usd', 'POR_COBRAR', nuevo_monto)
        
        return monto_liquidado_usd
    
    @staticmethod
    def obtener_deudas_pendientes() -> Dict[str, List[Dict[str, Any]]]:
        """Get all pending debts grouped by type."""
        with get_db_connection() as conn:
            deudas = DeudaRepository.obtener_pendientes(conn)
        
        por_pagar = []
        por_cobrar = []
        
        for row in deudas:
            deuda_dict = {
                "actor_id": row['actor_id'],
                "monto": row['monto_pendiente'],
                "moneda": row['moneda']
            }
            
            if row['tipo'] == 'POR_PAGAR':
                por_pagar.append(deuda_dict)
            else:
                por_cobrar.append(deuda_dict)
        
        return {
            "por_pagar": por_pagar,
            "por_cobrar": por_cobrar
        }

