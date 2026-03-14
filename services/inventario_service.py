"""
Servicio de inventario - Lógica de negocio para productos y stock.
"""
import logging
from typing import Dict, Any, List, Optional
from database.connection import get_db_connection
from database.repositories import (
    ProductoRepository, ConsignacionRepository, MovimientoRepository, DeudaRepository
)
from utils.currency import convert_to_usd

logger = logging.getLogger(__name__)


class InventarioService:
    """Servicio para operaciones de inventario."""
    
    @staticmethod
    def registrar_entrada(codigo: str, cantidad: float, costo_unitario: float,
                         moneda_costo: str, proveedor: str) -> Dict[str, Any]:
        """Registra una entrada de mercancía y genera deuda con proveedor."""
        costo_total = cantidad * costo_unitario
        
        with get_db_connection() as conn:
            # Obtener o crear producto
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            
            if producto:
                # Actualizar con costo promedio ponderado
                stock_anterior = producto['stock']
                costo_anterior = producto['costo_unitario']
                
                nuevo_stock = stock_anterior + cantidad
                costo_total_anterior = stock_anterior * costo_anterior
                nuevo_costo_total = costo_total_anterior + costo_total
                nuevo_costo_unitario = nuevo_costo_total / nuevo_stock if nuevo_stock > 0 else 0
                
                ProductoRepository.actualizar_stock(conn, codigo, nuevo_stock)
                ProductoRepository.actualizar_costo(conn, codigo, nuevo_costo_unitario, moneda_costo)
            else:
                # Crear nuevo producto
                ProductoRepository.crear(conn, codigo, codigo, costo_unitario, moneda_costo, cantidad)
            
            # Generar deuda con proveedor
            deuda = DeudaRepository.obtener_por_actor(conn, proveedor, moneda_costo, 'POR_PAGAR')
            if deuda:
                nuevo_monto = deuda['monto_pendiente'] + costo_total
                DeudaRepository.actualizar_monto(conn, proveedor, moneda_costo, 'POR_PAGAR', nuevo_monto)
            else:
                DeudaRepository.crear(conn, proveedor, costo_total, moneda_costo, 'POR_PAGAR')
        
        return {
            "codigo": codigo,
            "cantidad": cantidad,
            "costo_total": costo_total,
            "moneda": moneda_costo,
            "proveedor": proveedor
        }
    
    @staticmethod
    def obtener_stock() -> List[Dict[str, Any]]:
        """Obtiene todos los productos con stock."""
        with get_db_connection() as conn:
            productos = ProductoRepository.obtener_con_stock(conn)
        
        return [
            {
                "codigo": row['codigo'],
                "nombre": row['nombre'],
                "stock": row['stock'],
                "costo_unitario": row['costo_unitario'],
                "moneda_costo": row['moneda_costo']
            }
            for row in productos
        ]
    
    @staticmethod
    def registrar_venta_estandar(codigo: str, unidades: float, monto_total: float,
                                 moneda: str, caja_id: int, user_id: int,
                                 nota: str) -> Dict[str, Any]:
        """Registra una venta estándar (no consignada)."""
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            
            if not producto:
                raise ValueError(f"El producto {codigo} no existe en el inventario.")
            
            stock_actual = producto['stock']
            if stock_actual < unidades:
                raise ValueError(
                    f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {unidades}"
                )
            
            costo_unitario = producto['costo_unitario']
            moneda_costo = producto['moneda_costo']
            
            # Actualizar stock
            nuevo_stock = stock_actual - unidades
            ProductoRepository.actualizar_stock(conn, codigo, nuevo_stock)
            
            # Calcular CMV
            costo_total = unidades * costo_unitario
            
            # Obtener nombre de caja para descripción
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            # Registrar movimiento
            descripcion = (
                f"VENTA: {unidades} x {codigo} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"CMV: {costo_total:.2f} {moneda_costo.upper()} | "
                f"CAJA: {caja_nombre} | NOTA: {nota}"
            )
            
            MovimientoRepository.crear(
                conn, 'venta', monto_total, moneda, caja_id, user_id, descripcion
            )
        
        return {
            "codigo": codigo,
            "unidades": unidades,
            "monto_total": monto_total,
            "moneda": moneda,
            "costo_total": costo_total,
            "moneda_costo": moneda_costo
        }
    
    @staticmethod
    def registrar_venta_consignada(codigo: str, unidades: float, monto_total: float,
                                   moneda: str, caja_id: int, vendedor: str,
                                   user_id: int, nota: str) -> Dict[str, Any]:
        """Registra una venta consignada."""
        with get_db_connection() as conn:
            consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(conn, vendedor, codigo)
            
            if not consignacion or consignacion['stock'] < unidades:
                stock_disponible = consignacion['stock'] if consignacion else 0
                raise ValueError(
                    f"Stock consignado insuficiente para {vendedor}. "
                    f"Disponible: {stock_disponible}, Solicitado: {unidades}"
                )
            
            precio_unitario = consignacion['precio_unitario']
            moneda_consignacion = consignacion['moneda']
            
            # Actualizar stock consignado
            nuevo_stock = consignacion['stock'] - unidades
            ConsignacionRepository.actualizar_stock(conn, codigo, vendedor, nuevo_stock)
            
            # Liquidar deuda
            monto_a_liquidar = unidades * precio_unitario
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor, moneda_consignacion, 'POR_COBRAR')
            if deuda:
                nuevo_monto = max(0, deuda['monto_pendiente'] - monto_a_liquidar)
                DeudaRepository.actualizar_monto(conn, vendedor, moneda_consignacion, 'POR_COBRAR', nuevo_monto)
            
            # Obtener nombre de caja para descripción
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            # Registrar movimiento
            descripcion = (
                f"VENTA_CONSIGNADA: {unidades} x {codigo} | "
                f"Vendedor: {vendedor} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"DEUDA_LIQUIDADA: {monto_a_liquidar:.2f} {moneda_consignacion.upper()} | "
                f"CAJA: {caja_nombre} | NOTA: {nota}"
            )
            
            MovimientoRepository.crear(
                conn, 'venta', monto_total, moneda, caja_id, user_id, descripcion
            )
        
        return {
            "codigo": codigo,
            "unidades": unidades,
            "monto_total": monto_total,
            "vendedor": vendedor,
            "monto_liquidado": monto_a_liquidar,
            "moneda_liquidacion": moneda_consignacion
        }
    
    @staticmethod
    def calcular_ganancias() -> Dict[str, float]:
        """Calcula las ganancias brutas acumuladas."""
        with get_db_connection() as conn:
            movimientos = MovimientoRepository.obtener_todos(conn)
        
        total_ingreso_usd = 0.0
        total_costo_usd = 0.0
        
        for mov in movimientos:
            if mov['tipo'] != 'venta':
                continue
            
            # Convertir ingreso a USD
            ingreso_usd = convert_to_usd(mov['monto'], mov['moneda'])
            total_ingreso_usd += ingreso_usd
            
            # Extraer CMV de la descripción (solo ventas estándar)
            descripcion = mov['descripcion']
            if 'VENTA_CONSIGNADA' in descripcion:
                continue
            
            try:
                if 'CMV:' in descripcion:
                    cmv_part = descripcion.split('CMV:')[1].split('|')[0].strip()
                    costo_valor = float(cmv_part.split()[0].replace(',', ''))
                    costo_moneda = cmv_part.split()[1].lower()
                    costo_usd = convert_to_usd(costo_valor, costo_moneda)
                    total_costo_usd += costo_usd
            except Exception as e:
                logger.warning(f"Error al parsear CMV en descripción: {e}")
        
        margen_bruto = total_ingreso_usd - total_costo_usd
        
        return {
            "ingresos_total_usd": total_ingreso_usd,
            "costos_total_usd": total_costo_usd,
            "margen_bruto_usd": margen_bruto
        }
    
    @staticmethod
    def consignar_producto(codigo: str, cantidad: float, vendedor: str,
                          precio_venta: float, moneda: str) -> Dict[str, Any]:
        """Consigna productos a un vendedor."""
        with get_db_connection() as conn:
            # Verificar stock disponible
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            if not producto or producto['stock'] < cantidad:
                stock_actual = producto['stock'] if producto else 0
                raise ValueError(
                    f"Stock insuficiente para consignar. Disponible: {stock_actual}, Solicitado: {cantidad}"
                )
            
            # Descontar del stock general
            nuevo_stock = producto['stock'] - cantidad
            ProductoRepository.actualizar_stock(conn, codigo, nuevo_stock)
            
            # Crear o actualizar consignación
            consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(conn, vendedor, codigo)
            if consignacion:
                nuevo_stock_consignado = consignacion['stock'] + cantidad
                ConsignacionRepository.actualizar_stock(conn, codigo, vendedor, nuevo_stock_consignado)
            else:
                ConsignacionRepository.crear(conn, codigo, vendedor, cantidad, precio_venta, moneda)
            
            # Generar deuda POR_COBRAR
            monto_total_deuda = cantidad * precio_venta
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor, moneda, 'POR_COBRAR')
            if deuda:
                nuevo_monto = deuda['monto_pendiente'] + monto_total_deuda
                DeudaRepository.actualizar_monto(conn, vendedor, moneda, 'POR_COBRAR', nuevo_monto)
            else:
                DeudaRepository.crear(conn, vendedor, monto_total_deuda, moneda, 'POR_COBRAR')
        
        return {
            "codigo": codigo,
            "cantidad": cantidad,
            "vendedor": vendedor,
            "monto_deuda": monto_total_deuda,
            "moneda": moneda
        }
    
    @staticmethod
    def obtener_stock_consignado(vendedor: str) -> List[Dict[str, Any]]:
        """Obtiene el stock consignado de un vendedor."""
        with get_db_connection() as conn:
            consignaciones = ConsignacionRepository.obtener_por_vendedor(conn, vendedor)
        
        return [
            {
                "codigo": row['codigo'],
                "stock": row['stock']
            }
            for row in consignaciones
        ]

