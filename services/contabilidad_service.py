"""
Servicio de contabilidad - Lógica de negocio para movimientos financieros.
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
    """Servicio para operaciones contables."""
    
    @staticmethod
    def registrar_ingreso(monto: float, moneda: str, caja_id: int, user_id: int, 
                         descripcion: str = "Ingreso") -> Dict[str, Any]:
        """Registra un ingreso."""
        with get_db_connection() as conn:
            movimiento_id = MovimientoRepository.crear(
                conn, 'ingreso', monto, moneda, caja_id, user_id, descripcion
            )
        return {"movimiento_id": movimiento_id, "monto": monto, "moneda": moneda, "caja_id": caja_id}
    
    @staticmethod
    def registrar_gasto(monto: float, moneda: str, caja_id: int, user_id: int, 
                       descripcion: str) -> Dict[str, Any]:
        """Registra un gasto, validando saldo suficiente."""
        with get_db_connection() as conn:
            saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
            
            # Obtener nombre de la caja para el mensaje de error
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            if saldo_actual < monto:
                raise ValueError(
                    f"Saldo insuficiente en caja {caja_nombre.upper()} ({moneda.upper()}). "
                    f"Disponible: {saldo_actual:.2f} {moneda.upper()}."
                )
            
            movimiento_id = MovimientoRepository.crear(
                conn, 'gasto', monto, moneda, caja_id, user_id, descripcion
            )
        
        return {"movimiento_id": movimiento_id, "monto": monto, "moneda": moneda, "caja_id": caja_id}
    
    @staticmethod
    def obtener_balance() -> Dict[str, Dict[str, float]]:
        """Obtiene el balance agrupado por caja y moneda."""
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
        """Obtiene el saldo actual de una caja."""
        with get_db_connection() as conn:
            return MovimientoRepository.get_saldo_caja(conn, caja_id, moneda)
    
    @staticmethod
    def registrar_traspaso(monto: float, moneda_origen: str, caja_origen_id: int,
                          moneda_destino: str, caja_destino_id: int, user_id: int,
                          motivo: str) -> Dict[str, Any]:
        """Registra un traspaso entre cajas con conversión de moneda."""
        if caja_origen_id == caja_destino_id and moneda_origen == moneda_destino:
            raise ValueError("Las cajas y monedas de origen y destino no pueden ser iguales.")
        
        with get_db_connection() as conn:
            # Validar saldo suficiente
            saldo_actual = MovimientoRepository.get_saldo_caja(conn, caja_origen_id, moneda_origen)
            if saldo_actual < monto:
                from services.cajas_service import CajaService
                caja_origen = CajaService.obtener_por_id(caja_origen_id)
                caja_nombre = caja_origen['nombre'] if caja_origen else str(caja_origen_id)
                raise ValueError(
                    f"Saldo insuficiente en caja de origen {caja_nombre.upper()} "
                    f"({moneda_origen.upper()}). Disponible: {saldo_actual:.2f} {moneda_origen.upper()}."
                )
            
            # Calcular monto destino
            if moneda_origen == moneda_destino:
                monto_destino = monto
            else:
                monto_destino = convert_currency(monto, moneda_origen, moneda_destino)
            
            # Obtener nombres de cajas para descripción
            from services.cajas_service import CajaService
            caja_origen_obj = CajaService.obtener_por_id(caja_origen_id)
            caja_destino_obj = CajaService.obtener_por_id(caja_destino_id)
            caja_origen_nombre = caja_origen_obj['nombre'] if caja_origen_obj else str(caja_origen_id)
            caja_destino_nombre = caja_destino_obj['nombre'] if caja_destino_obj else str(caja_destino_id)
            
            # Registrar egreso en caja origen (tipo 'traspaso' se resta)
            MovimientoRepository.crear(
                conn, 'traspaso', monto, moneda_origen, caja_origen_id, user_id,
                f"TRASPASO (Egreso): A {caja_destino_nombre.upper()}/{moneda_destino.upper()} - Motivo: {motivo}"
            )
            
            # Registrar ingreso en caja destino (tipo 'ingreso' se suma)
            MovimientoRepository.crear(
                conn, 'ingreso', monto_destino, moneda_destino, caja_destino_id, user_id,
                f"TRASPASO (Ingreso): Desde {caja_origen_nombre.upper()}/{moneda_origen.upper()} - Motivo: {motivo}"
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
        """Obtiene el historial de movimientos de los últimos N días."""
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
        """Exporta todos los movimientos."""
        with get_db_connection() as conn:
            movimientos = MovimientoRepository.obtener_todos(conn)
        
        return [dict(row) for row in movimientos]


class DeudaService:
    """Servicio para gestión de deudas."""
    
    @staticmethod
    def actualizar_deuda(actor_id: str, monto: float, moneda: str, tipo: str,
                        es_incremento: bool = True) -> float:
        """Actualiza o crea una deuda."""
        with get_db_connection() as conn:
            deuda = DeudaRepository.obtener_por_actor(conn, actor_id, moneda, tipo)
            
            if deuda:
                monto_actual = deuda['monto_pendiente']
                if es_incremento:
                    nuevo_monto = monto_actual + monto
                else:
                    nuevo_monto = max(0, monto_actual - monto)
                
                DeudaRepository.actualizar_monto(conn, actor_id, moneda, tipo, nuevo_monto)
                return nuevo_monto
            else:
                if not es_incremento:
                    raise ValueError(f"No existe deuda {tipo} para {actor_id} en {moneda}")
                
                DeudaRepository.crear(conn, actor_id, monto, moneda, tipo)
                return monto
    
    @staticmethod
    def liquidar_deuda_vendedor(actor_id: str, monto_pagado: float, 
                               moneda_pago: str) -> float:
        """Liquida una deuda POR_COBRAR con un pago."""
        # Convertir pago a USD (moneda base de deudas)
        monto_liquidado_usd = convert_to_usd(monto_pagado, moneda_pago)
        
        with get_db_connection() as conn:
            deuda = DeudaRepository.obtener_por_actor(conn, actor_id, 'usd', 'POR_COBRAR')
            
            if not deuda:
                logger.warning(f"No se encontró deuda POR_COBRAR para {actor_id}")
                return 0.0
            
            nuevo_monto = max(0, deuda['monto_pendiente'] - monto_liquidado_usd)
            DeudaRepository.actualizar_monto(conn, actor_id, 'usd', 'POR_COBRAR', nuevo_monto)
        
        return monto_liquidado_usd
    
    @staticmethod
    def obtener_deudas_pendientes() -> Dict[str, List[Dict[str, Any]]]:
        """Obtiene todas las deudas pendientes agrupadas por tipo."""
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

