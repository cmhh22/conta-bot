"""
Inventory service - Business logic for products and stock.
"""
import logging
from typing import Dict, Any, List, Optional
from database.connection import get_db_connection
from database.repositories import (
    ProductoRepository, ConsignmentRepository, MovimientoRepository, DeudaRepository
)
from utils.currency import convert_to_usd

logger = logging.getLogger(__name__)


class InventarioService:
    """Service for inventory operations."""
    
    @staticmethod
    def registrar_entrada(codigo: str, cantidad: float, costo_unitario: float,
                         moneda_costo: str, proveedor: str) -> Dict[str, Any]:
        """Record inbound stock and generate supplier debt."""
        costo_total = cantidad * costo_unitario
        
        with get_db_connection() as conn:
            # Get or create product
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            
            if producto:
                # Update with weighted average cost
                stock_anterior = producto['stock']
                costo_anterior = producto['costo_unitario']
                
                nuevo_stock = stock_anterior + cantidad
                costo_total_anterior = stock_anterior * costo_anterior
                nuevo_costo_total = costo_total_anterior + costo_total
                nuevo_costo_unitario = nuevo_costo_total / nuevo_stock if nuevo_stock > 0 else 0
                
                ProductoRepository.update_stock(conn, codigo, nuevo_stock)
                ProductoRepository.update_costo(conn, codigo, nuevo_costo_unitario, moneda_costo)
            else:
                # Create new product
                ProductoRepository.create(conn, codigo, codigo, costo_unitario, moneda_costo, cantidad)
            
            # Generate supplier debt
            deuda = DeudaRepository.obtener_por_actor(conn, proveedor, moneda_costo, 'POR_PAGAR')
            if deuda:
                nuevo_monto = deuda['monto_pendiente'] + costo_total
                DeudaRepository.update_monto(conn, proveedor, moneda_costo, 'POR_PAGAR', nuevo_monto)
            else:
                DeudaRepository.create(conn, proveedor, costo_total, moneda_costo, 'POR_PAGAR')
        
        return {
            "codigo": codigo,
            "cantidad": cantidad,
            "costo_total": costo_total,
            "moneda": moneda_costo,
            "proveedor": proveedor
        }
    
    @staticmethod
    def obtener_stock() -> List[Dict[str, Any]]:
        """Get all products with stock."""
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
        """Record a standard sale (non-consigned)."""
        with get_db_connection() as conn:
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            
            if not producto:
                raise ValueError(f"Product {codigo} does not exist in inventory.")
            
            stock_actual = producto['stock']
            if stock_actual < unidades:
                raise ValueError(
                    f"Insufficient stock. Available: {stock_actual}, Requested: {unidades}"
                )
            
            costo_unitario = producto['costo_unitario']
            moneda_costo = producto['moneda_costo']
            
            # Update stock
            nuevo_stock = stock_actual - unidades
            ProductoRepository.update_stock(conn, codigo, nuevo_stock)
            
            # Calculate COGS
            costo_total = unidades * costo_unitario
            
            # Get box name for description
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            # Record movement
            descripcion = (
                f"VENTA: {unidades} x {codigo} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"CMV: {costo_total:.2f} {moneda_costo.upper()} | "
                f"CAJA: {caja_nombre} | NOTA: {nota}"
            )
            
            MovimientoRepository.create(
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
        """Record a consigned sale."""
        with get_db_connection() as conn:
            consignment = ConsignmentRepository.obtener_por_vendedor_codigo(conn, vendedor, codigo)
            
            if not consignment or consignment['stock'] < unidades:
                stock_disponible = consignment['stock'] if consignment else 0
                raise ValueError(
                    f"Insufficient consigned stock for {vendedor}. "
                    f"Available: {stock_disponible}, Requested: {unidades}"
                )
            
            precio_unitario = consignment['precio_unitario']
            moneda_consignment = consignment['moneda']
            
            # Update consigned stock
            nuevo_stock = consignment['stock'] - unidades
            ConsignmentRepository.update_stock(conn, codigo, vendedor, nuevo_stock)
            
            # Settle debt
            monto_a_liquidar = unidades * precio_unitario
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor, moneda_consignment, 'POR_COBRAR')
            if deuda:
                nuevo_monto = max(0, deuda['monto_pendiente'] - monto_a_liquidar)
                DeudaRepository.update_monto(conn, vendedor, moneda_consignment, 'POR_COBRAR', nuevo_monto)
            
            # Get box name for description
            from services.cajas_service import CajaService
            caja = CajaService.obtener_por_id(caja_id)
            caja_nombre = caja['nombre'] if caja else str(caja_id)
            
            # Record movement
            descripcion = (
                f"VENTA_CONSIGNADA: {unidades} x {codigo} | "
                f"Seller: {vendedor} | "
                f"REVENUE: {monto_total:.2f} {moneda.upper()} | "
                f"DEUDA_LIQUIDADA: {monto_a_liquidar:.2f} {moneda_consignment.upper()} | "
                f"CAJA: {caja_nombre} | NOTA: {nota}"
            )
            
            MovimientoRepository.create(
                conn, 'venta', monto_total, moneda, caja_id, user_id, descripcion
            )
        
        return {
            "codigo": codigo,
            "unidades": unidades,
            "monto_total": monto_total,
            "vendedor": vendedor,
            "monto_liquidado": monto_a_liquidar,
            "moneda_liquidacion": moneda_consignment
        }
    
    @staticmethod
    def calcular_ganancias() -> Dict[str, float]:
        """Calculate accumulated gross profit."""
        with get_db_connection() as conn:
            movimientos = MovimientoRepository.obtener_todos(conn)
        
        total_ingreso_usd = 0.0
        total_costo_usd = 0.0
        
        for mov in movimientos:
            if mov['tipo'] != 'venta':
                continue
            
            # Convert revenue to USD
            ingreso_usd = convert_to_usd(mov['monto'], mov['moneda'])
            total_ingreso_usd += ingreso_usd
            
            # Extract COGS from description (standard sales only)
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
                logger.warning(f"Error parsing COGS from description: {e}")
        
        margen_bruto = total_ingreso_usd - total_costo_usd
        
        return {
            "ingresos_total_usd": total_ingreso_usd,
            "costos_total_usd": total_costo_usd,
            "margen_bruto_usd": margen_bruto
        }
    
    @staticmethod
    def consignar_producto(codigo: str, cantidad: float, vendedor: str,
                          precio_venta: float, moneda: str) -> Dict[str, Any]:
        """Consign products to a seller."""
        with get_db_connection() as conn:
            # Check available stock
            producto = ProductoRepository.obtener_por_codigo(conn, codigo)
            if not producto or producto['stock'] < cantidad:
                stock_actual = producto['stock'] if producto else 0
                raise ValueError(
                    f"Insufficient stock to consign. Available: {stock_actual}, Requested: {cantidad}"
                )
            
            # Subtract from general stock
            nuevo_stock = producto['stock'] - cantidad
            ProductoRepository.update_stock(conn, codigo, nuevo_stock)
            
            # Create or update consignment
            consignment = ConsignmentRepository.obtener_por_vendedor_codigo(conn, vendedor, codigo)
            if consignment:
                nuevo_stock_consignado = consignment['stock'] + cantidad
                ConsignmentRepository.update_stock(conn, codigo, vendedor, nuevo_stock_consignado)
            else:
                ConsignmentRepository.create(conn, codigo, vendedor, cantidad, precio_venta, moneda)
            
            # Generate POR_COBRAR debt
            monto_total_deuda = cantidad * precio_venta
            deuda = DeudaRepository.obtener_por_actor(conn, vendedor, moneda, 'POR_COBRAR')
            if deuda:
                nuevo_monto = deuda['monto_pendiente'] + monto_total_deuda
                DeudaRepository.update_monto(conn, vendedor, moneda, 'POR_COBRAR', nuevo_monto)
            else:
                DeudaRepository.create(conn, vendedor, monto_total_deuda, moneda, 'POR_COBRAR')
        
        return {
            "codigo": codigo,
            "cantidad": cantidad,
            "vendedor": vendedor,
            "monto_deuda": monto_total_deuda,
            "moneda": moneda
        }
    
    @staticmethod
    def obtener_stock_consignado(vendedor: str) -> List[Dict[str, Any]]:
        """Get consigned stock for a seller."""
        with get_db_connection() as conn:
            consignaciones = ConsignmentRepository.obtener_por_vendedor(conn, vendedor)
        
        return [
            {
                "codigo": row['codigo'],
                "stock": row['stock']
            }
            for row in consignaciones
        ]

