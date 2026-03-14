"""
Logistics service - Business logic for inventory movements.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import (
    ContainerProductoRepository,
    InventarioWarehouseRepository,
    MovimientoInventarioRepository,
    ProductoRepository,
    ContainerRepository,
    WarehouseRepository,
    ConsignmentRepository,
    DeudaRepository,
    MovimientoRepository
)
from services.vendedores_service import VendedorService
from utils.currency import convert_to_usd, convert_currency
from core.config import TASA_USD_CUP

logger = logging.getLogger(__name__)


def agregar_producto_a_container(container_id: int, producto_codigo: str, cantidad: float) -> Dict[str, Any]:
    """
    Add a product to a container.
    
    Args:
        container_id: Container ID
        producto_codigo: Product code
        cantidad: Quantity to add
    
    Returns:
        Dict with added product data
    
    Raises:
        ValueError: If container or product does not exist, or quantity is invalid
    """
    if cantidad <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    with get_db_connection() as conn:
        # Check that container exists
        container = ContainerRepository.obtener_por_id(conn, container_id)
        if not container:
            raise ValueError(f"No container exists with ID {container_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        ContainerProductoRepository.agregar_producto(conn, container_id, producto_codigo, cantidad)
        producto_en_container = ContainerProductoRepository.obtener_producto_en_container(
            conn, container_id, producto_codigo
        )
        
        return {
            "container_id": producto_en_container["container_id"],
            "producto_codigo": producto_en_container["producto_codigo"],
            "cantidad": producto_en_container["cantidad"],
            "fecha_ingreso": producto_en_container["fecha_ingreso"]
        }


def obtener_productos_de_container(container_id: int) -> List[Dict[str, Any]]:
    """
    Get all products from a container.
    
    Args:
        container_id: Container ID
    
    Returns:
        List of dictionaries with container products
    """
    with get_db_connection() as conn:
        productos = ContainerProductoRepository.obtener_productos_por_container(conn, container_id)
        return [
            {
                "id": prod["id"],
                "container_id": prod["container_id"],
                "producto_codigo": prod["producto_codigo"],
                "producto_nombre": prod["producto_nombre"],
                "cantidad": prod["cantidad"],
                "fecha_ingreso": prod["fecha_ingreso"]
            }
            for prod in productos
        ]


def mover_producto_container_a_warehouse(container_id: int, warehouse_id: int, producto_codigo: str,
                                       cantidad: float, user_id: int, descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Move a product from a container to a warehouse.
    
    Args:
        container_id: Source container ID
        warehouse_id: Destination warehouse ID
        producto_codigo: Product code to move
        cantidad: Quantity to move
        user_id: ID of the user performing the movement
        descripcion: Optional movement description
    
    Returns:
        Dict with movement data
    
    Raises:
        ValueError: If there is not enough stock in the container or IDs do not exist
    """
    if cantidad <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    with get_db_connection() as conn:
        # Check that container exists
        container = ContainerRepository.obtener_por_id(conn, container_id)
        if not container:
            raise ValueError(f"No container exists with ID {container_id}")
        
        # Check that warehouse exists
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            raise ValueError(f"No warehouse exists with ID {warehouse_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check available stock in container
        producto_en_container = ContainerProductoRepository.obtener_producto_en_container(
            conn, container_id, producto_codigo
        )
        if not producto_en_container:
            raise ValueError(f"Product '{producto_codigo}' is not in container {container_id}")
        
        stock_disponible = producto_en_container["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Perform movement
        # 1. Reduce quantity in container
        ContainerProductoRepository.reducir_cantidad(conn, container_id, producto_codigo, cantidad)
        
        # 2. Add quantity in warehouse
        InventarioWarehouseRepository.agregar_producto(conn, warehouse_id, producto_codigo, cantidad)
        
        # 3. Record movement
        movimiento_id = MovimientoInventarioRepository.create(
            conn,
            tipo="container_a_warehouse",
            source_tipo="container",
            source_id=container_id,
            destination_tipo="warehouse",
            destination_id=warehouse_id,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=descripcion
        )
        
        return {
            "movimiento_id": movimiento_id,
            "tipo": "container_a_warehouse",
            "container_id": container_id,
            "warehouse_id": warehouse_id,
            "producto_codigo": producto_codigo,
            "cantidad": cantidad,
            "descripcion": descripcion
        }


def obtener_inventario_warehouse(warehouse_id: int) -> List[Dict[str, Any]]:
    """
    Get full inventory for a warehouse.
    
    Args:
        warehouse_id: Warehouse ID
    
    Returns:
        List of dictionaries with warehouse inventory
    """
    with get_db_connection() as conn:
        inventario = InventarioWarehouseRepository.obtener_inventario_por_warehouse(conn, warehouse_id)
        return [
            {
                "id": item["id"],
                "warehouse_id": item["warehouse_id"],
                "producto_codigo": item["producto_codigo"],
                "producto_nombre": item["producto_nombre"],
                "cantidad": item["cantidad"],
                "fecha_actualizacion": item["fecha_actualizacion"]
            }
            for item in inventario
        ]


def obtener_movimientos_warehouse(warehouse_id: int, limite: int = 50) -> List[Dict[str, Any]]:
    """
    Get movement history for a warehouse.
    
    Args:
        warehouse_id: Warehouse ID
        limite: Maximum number of movements to return
    
    Returns:
        List of dictionaries with movements
    """
    with get_db_connection() as conn:
        movimientos = MovimientoInventarioRepository.obtener_por_warehouse(conn, warehouse_id, limite)
        return [
            {
                "id": mov["id"],
                "fecha": mov["fecha"],
                "tipo": mov["tipo"],
                "source_tipo": mov["source_tipo"],
                "source_id": mov["source_id"],
                "destination_tipo": mov["destination_tipo"],
                "destination_id": mov["destination_id"],
                "producto_codigo": mov["producto_codigo"],
                "producto_nombre": mov["producto_nombre"],
                "cantidad": mov["cantidad"],
                "user_id": mov["user_id"],
                "descripcion": mov["descripcion"]
            }
            for mov in movimientos
        ]


def obtener_movimientos_container(container_id: int, limite: int = 50) -> List[Dict[str, Any]]:
    """
    Get movement history for a container.
    
    Args:
        container_id: Container ID
        limite: Maximum number of movements to return
    
    Returns:
        List of dictionaries with movements
    """
    with get_db_connection() as conn:
        movimientos = MovimientoInventarioRepository.obtener_por_container(conn, container_id, limite)
        return [
            {
                "id": mov["id"],
                "fecha": mov["fecha"],
                "tipo": mov["tipo"],
                "source_tipo": mov["source_tipo"],
                "source_id": mov["source_id"],
                "destination_tipo": mov["destination_tipo"],
                "destination_id": mov["destination_id"],
                "producto_codigo": mov["producto_codigo"],
                "producto_nombre": mov["producto_nombre"],
                "cantidad": mov["cantidad"],
                "user_id": mov["user_id"],
                "descripcion": mov["descripcion"]
            }
            for mov in movimientos
        ]


def mover_producto_warehouse_a_warehouse(warehouse_source_id: int, warehouse_destination_id: int,
                                     producto_codigo: str, cantidad: float, user_id: int,
                                     descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Move a product from one warehouse to another.
    
    Args:
        warehouse_source_id: Source warehouse ID
        warehouse_destination_id: Destination warehouse ID
        producto_codigo: Product code to move
        cantidad: Quantity to move
        user_id: ID of the user performing the movement
        descripcion: Optional movement description
    
    Returns:
        Dict with movement data
    
    Raises:
        ValueError: If source warehouse lacks stock or IDs do not exist
    """
    if cantidad <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    with get_db_connection() as conn:
        # Check that warehouses exist
        warehouse_source = WarehouseRepository.obtener_por_id(conn, warehouse_source_id)
        if not warehouse_source:
            raise ValueError(f"No warehouse exists with ID {warehouse_source_id}")
        
        warehouse_destination = WarehouseRepository.obtener_por_id(conn, warehouse_destination_id)
        if not warehouse_destination:
            raise ValueError(f"No warehouse exists with ID {warehouse_destination_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check available stock in source warehouse
        producto_en_warehouse = InventarioWarehouseRepository.obtener_producto_en_warehouse(
            conn, warehouse_source_id, producto_codigo
        )
        if not producto_en_warehouse:
            raise ValueError(f"Product '{producto_codigo}' is not in warehouse {warehouse_source_id}")
        
        stock_disponible = producto_en_warehouse["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Perform movement
        # 1. Reduce quantity in source warehouse
        InventarioWarehouseRepository.reducir_cantidad(conn, warehouse_source_id, producto_codigo, cantidad)
        
        # 2. Add quantity in destination warehouse
        InventarioWarehouseRepository.agregar_producto(conn, warehouse_destination_id, producto_codigo, cantidad)
        
        # 3. Record movement
        movimiento_id = MovimientoInventarioRepository.create(
            conn,
            tipo="warehouse_a_warehouse",
            source_tipo="warehouse",
            source_id=warehouse_source_id,
            destination_tipo="warehouse",
            destination_id=warehouse_destination_id,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=descripcion
        )
        
        return {
            "movimiento_id": movimiento_id,
            "tipo": "warehouse_a_warehouse",
            "warehouse_source_id": warehouse_source_id,
            "warehouse_destination_id": warehouse_destination_id,
            "producto_codigo": producto_codigo,
            "cantidad": cantidad,
            "descripcion": descripcion
        }


def ajustar_inventario_warehouse(warehouse_id: int, producto_codigo: str, nueva_cantidad: float,
                               user_id: int, descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Adjust warehouse inventory (inventory correction).
    
    Args:
        warehouse_id: Warehouse ID
        producto_codigo: Product code
        nueva_cantidad: New quantity (must be >= 0)
        user_id: ID of user performing adjustment
        descripcion: Optional adjustment description
    
    Returns:
        Dict with performed adjustment data
    
    Raises:
        ValueError: If warehouse/product does not exist, or quantity is invalid
    """
    if nueva_cantidad < 0:
        raise ValueError("Quantity cannot be negative")
    
    with get_db_connection() as conn:
        # Check that warehouse exists
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            raise ValueError(f"No warehouse exists with ID {warehouse_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Get current quantity
        producto_en_warehouse = InventarioWarehouseRepository.obtener_producto_en_warehouse(
            conn, warehouse_id, producto_codigo
        )
        cantidad_anterior = producto_en_warehouse["cantidad"] if producto_en_warehouse else 0
        
        # Calculate difference
        diferencia = nueva_cantidad - cantidad_anterior
        
        # Update inventory
        if producto_en_warehouse:
            if nueva_cantidad == 0:
                InventarioWarehouseRepository.delete_producto(conn, warehouse_id, producto_codigo)
            else:
                InventarioWarehouseRepository.update_cantidad(conn, warehouse_id, producto_codigo, nueva_cantidad)
        else:
            if nueva_cantidad > 0:
                InventarioWarehouseRepository.agregar_producto(conn, warehouse_id, producto_codigo, nueva_cantidad)
        
        # Record adjustment
        if diferencia != 0:
            MovimientoInventarioRepository.create(
                conn,
                tipo="ajuste",
                source_tipo="warehouse",
                source_id=warehouse_id,
                destination_tipo=None,
                destination_id=None,
                producto_codigo=producto_codigo,
                cantidad=abs(diferencia),
                user_id=user_id,
                descripcion=descripcion or f"Ajuste: {cantidad_anterior} → {nueva_cantidad}"
            )
        
        return {
            "warehouse_id": warehouse_id,
            "producto_codigo": producto_codigo,
            "cantidad_anterior": cantidad_anterior,
            "nueva_cantidad": nueva_cantidad,
            "diferencia": diferencia,
            "descripcion": descripcion
        }


def obtener_resumen_logistics() -> Dict[str, Any]:
    """
    Get a high-level logistics summary.
    
    Returns:
        Dict with logistics statistics
    """
    with get_db_connection() as conn:
        # Count containers
        containeres = ContainerRepository.obtener_todos(conn)
        total_containeres = len(containeres)
        
        # Count products in containers
        total_productos_containeres = 0
        for cont in containeres:
            productos = ContainerProductoRepository.obtener_productos_por_container(conn, cont["id"])
            total_productos_containeres += len(productos)
        
        # Count warehouses
        warehousees = WarehouseRepository.obtener_todos(conn)
        total_warehousees = len(warehousees)
        
        # Count products in warehouses
        total_productos_warehousees = 0
        for alm in warehousees:
            inventario = InventarioWarehouseRepository.obtener_inventario_por_warehouse(conn, alm["id"])
            total_productos_warehousees += len(inventario)
        
        return {
            "total_containeres": total_containeres,
            "total_productos_containeres": total_productos_containeres,
            "total_warehousees": total_warehousees,
            "total_productos_warehousees": total_productos_warehousees
        }


def consignar_desde_warehouse(warehouse_id: int, producto_codigo: str, cantidad: float,
                            vendedor_id: int, precio_venta: float, moneda: str,
                            user_id: int) -> Dict[str, Any]:
    """
    Consign a product from a warehouse to a seller.
    
    Args:
        warehouse_id: Source warehouse ID
        producto_codigo: Product code to consign
        cantidad: Quantity to consign
        vendedor_id: Seller ID
        precio_venta: Unit sale price
        moneda: Price currency ('usd', 'cup', 'cup-t', 'eur')
        user_id: ID of user recording the consignment
    
    Returns:
        Dict with consignment data
    
    Raises:
        ValueError: If warehouse has insufficient stock or IDs do not exist
    """
    if cantidad <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    if precio_venta <= 0:
        raise ValueError("Price must be greater than 0")
    
    from services.vendedores_service import VendedorService
    
    with get_db_connection() as conn:
        # Check that warehouse exists
        warehouse = WarehouseRepository.obtener_por_id(conn, warehouse_id)
        if not warehouse:
            raise ValueError(f"No warehouse exists with ID {warehouse_id}")
        
        # Check that seller exists
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        if not vendedor:
            raise ValueError(f"No seller exists with ID {vendedor_id}")
        
        vendedor_name = vendedor['name']
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check available stock in warehouse
        producto_en_warehouse = InventarioWarehouseRepository.obtener_producto_en_warehouse(
            conn, warehouse_id, producto_codigo
        )
        if not producto_en_warehouse:
            raise ValueError(f"Product '{producto_codigo}' is not in warehouse {warehouse_id}")
        
        stock_disponible = producto_en_warehouse["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock in warehouse. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Reduce warehouse inventory
        nueva_cantidad = stock_disponible - cantidad
        InventarioWarehouseRepository.update_cantidad(
            conn, warehouse_id, producto_codigo, nueva_cantidad
        )
        
        # Create or update consignment
        consignment = ConsignmentRepository.obtener_por_vendedor_codigo(conn, vendedor_name, producto_codigo)
        if consignment:
            nuevo_stock_consignado = consignment['stock'] + cantidad
            ConsignmentRepository.update_stock(conn, producto_codigo, vendedor_name, nuevo_stock_consignado)
        else:
            ConsignmentRepository.create(conn, producto_codigo, vendedor_name, cantidad, precio_venta, moneda)
        
        # Generate POR_COBRAR debt
        monto_total_deuda = cantidad * precio_venta
        deuda = DeudaRepository.obtener_por_actor(conn, vendedor_name, moneda, 'POR_COBRAR')
        if deuda:
            nuevo_monto = deuda['monto_pendiente'] + monto_total_deuda
            DeudaRepository.update_monto(conn, vendedor_name, moneda, 'POR_COBRAR', nuevo_monto)
        else:
            DeudaRepository.create(conn, vendedor_name, monto_total_deuda, moneda, 'POR_COBRAR')
        
        # Record inventory movement
        MovimientoInventarioRepository.create(
            conn,
            tipo='venta_warehouse',
            source_tipo='warehouse',
            source_id=warehouse_id,
            destination_tipo=None,
            destination_id=None,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=f"Consignment to seller {vendedor_name}"
        )
    
    return {
        "warehouse_id": warehouse_id,
        "producto_codigo": producto_codigo,
        "cantidad": cantidad,
        "vendedor_id": vendedor_id,
        "vendedor_name": vendedor_name,
        "precio_venta": precio_venta,
        "moneda": moneda,
        "monto_deuda": monto_total_deuda
    }


def mover_consignment_vendedor(vendedor_source_id: int, vendedor_destination_id: int,
                                producto_codigo: str, cantidad: float,
                                user_id: int) -> Dict[str, Any]:
    """
    Move a consignment from one seller to another.
    
    Args:
        vendedor_source_id: Source seller ID
        vendedor_destination_id: Destination seller ID
        producto_codigo: Product code to move
        cantidad: Quantity to move
        user_id: ID of user performing the move
    
    Returns:
        Dict with movement data
    
    Raises:
        ValueError: If consigned stock is insufficient or IDs do not exist
    """
    if cantidad <= 0:
        raise ValueError("Quantity must be greater than 0")
    
    with get_db_connection() as conn:
        # Check that sellers exist
        vendedor_source = VendedorService.obtener_por_id(vendedor_source_id)
        if not vendedor_source:
            raise ValueError(f"No seller exists with ID {vendedor_source_id}")
        
        vendedor_destination = VendedorService.obtener_por_id(vendedor_destination_id)
        if not vendedor_destination:
            raise ValueError(f"No seller exists with ID {vendedor_destination_id}")
        
        vendedor_source_name = vendedor_source['name']
        vendedor_destination_name = vendedor_destination['name']
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check source seller consignment
        consignment_source = ConsignmentRepository.obtener_por_vendedor_codigo(
            conn, vendedor_source_name, producto_codigo
        )
        if not consignment_source:
            raise ValueError(
                f"Seller {vendedor_source_name} has no consignment for product '{producto_codigo}'"
            )
        
        stock_disponible = consignment_source["stock"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient consigned stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        precio_unitario = consignment_source["precio_unitario"]
        moneda = consignment_source["moneda"]
        
        # Reduce source seller consignment
        nuevo_stock_source = stock_disponible - cantidad
        if nuevo_stock_source > 0:
            ConsignmentRepository.update_stock(
                conn, producto_codigo, vendedor_source_name, nuevo_stock_source
            )
        else:
            # If it reaches 0, delete the consignment
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Consignaciones WHERE codigo = ? AND vendedor = ?",
                (producto_codigo, vendedor_source_name)
            )
        
        # Create or update destination seller consignment
        consignment_destination = ConsignmentRepository.obtener_por_vendedor_codigo(
            conn, vendedor_destination_name, producto_codigo
        )
        if consignment_destination:
            nuevo_stock_destination = consignment_destination["stock"] + cantidad
            ConsignmentRepository.update_stock(
                conn, producto_codigo, vendedor_destination_name, nuevo_stock_destination
            )
        else:
            ConsignmentRepository.create(
                conn, producto_codigo, vendedor_destination_name, cantidad, precio_unitario, moneda
            )
        
        # Update debts
        monto_movimiento = cantidad * precio_unitario
        
        # Reduce source seller debt
        deuda_source = DeudaRepository.obtener_por_actor(conn, vendedor_source_name, moneda, 'POR_COBRAR')
        if deuda_source:
            nuevo_monto_source = max(0, deuda_source['monto_pendiente'] - monto_movimiento)
            if nuevo_monto_source > 0:
                DeudaRepository.update_monto(conn, vendedor_source_name, moneda, 'POR_COBRAR', nuevo_monto_source)
            else:
                # If debt reaches 0, remove it
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM Deudas WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'",
                    (vendedor_source_name, moneda)
                )
        
        # Increase destination seller debt
        deuda_destination = DeudaRepository.obtener_por_actor(conn, vendedor_destination_name, moneda, 'POR_COBRAR')
        if deuda_destination:
            nuevo_monto_destination = deuda_destination['monto_pendiente'] + monto_movimiento
            DeudaRepository.update_monto(conn, vendedor_destination_name, moneda, 'POR_COBRAR', nuevo_monto_destination)
        else:
            DeudaRepository.create(conn, vendedor_destination_name, monto_movimiento, moneda, 'POR_COBRAR')
    
    return {
        "vendedor_source_id": vendedor_source_id,
        "vendedor_source_name": vendedor_source_name,
        "vendedor_destination_id": vendedor_destination_id,
        "vendedor_destination_name": vendedor_destination_name,
        "producto_codigo": producto_codigo,
        "cantidad": cantidad,
        "precio_unitario": precio_unitario,
        "moneda": moneda,
        "monto_movimiento": monto_movimiento
    }


def pagar_consignment(vendedor_id: int, moneda_deuda: str, monto_pago: float,
                       moneda_pago: str, caja_id: int, user_id: int,
                       nota: Optional[str] = None) -> Dict[str, Any]:
    """
    Record payment of a consignment (reduces POR_COBRAR debt).
    
    Args:
        vendedor_id: ID of the paying seller
        moneda_deuda: Currency of debt to pay ('usd', 'cup', 'cup-t', 'eur')
        monto_pago: Payment amount
        moneda_pago: Payment currency ('usd', 'cup', 'cup-t', 'eur')
        caja_id: ID of box receiving payment
        user_id: ID of user recording payment
        nota: Optional payment note
    
    Returns:
        Dict with recorded payment data
    
    Raises:
        ValueError: If seller does not exist, has no debt, or amount is invalid
    """
    if monto_pago <= 0:
        raise ValueError("Payment amount must be greater than 0")
    
    with get_db_connection() as conn:
        # Check that seller exists
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        if not vendedor:
            raise ValueError(f"No seller exists with ID {vendedor_id}")
        
        vendedor_name = vendedor['name']
        
        # Check debt exists
        deuda = DeudaRepository.obtener_por_actor(conn, vendedor_name, moneda_deuda, 'POR_COBRAR')
        if not deuda:
            raise ValueError(
                f"Seller {vendedor_name} has no POR_COBRAR debt in {moneda_deuda.upper()}"
            )
        
        deuda_actual = deuda['monto_pendiente']
        
        # Convert payment to debt currency if needed
        if moneda_pago != moneda_deuda:
            # Use currency conversion function that already handles all currencies (usd, cup, cup-t, eur)
            monto_a_descontar = convert_currency(monto_pago, moneda_pago, moneda_deuda)
        else:
            monto_a_descontar = monto_pago
        
        # Verify deducted amount does not exceed debt
        if monto_a_descontar > deuda_actual:
            raise ValueError(
                f"Payment amount ({monto_a_descontar:.2f} {moneda_deuda.upper()}) "
                f"exceeds current debt ({deuda_actual:.2f} {moneda_deuda.upper()})"
            )
        
        # Reduce debt
        nuevo_monto = max(0, deuda_actual - monto_a_descontar)
        if nuevo_monto > 0:
            DeudaRepository.update_monto(conn, vendedor_name, moneda_deuda, 'POR_COBRAR', nuevo_monto)
        else:
            # If debt reaches 0, remove it
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Deudas WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'",
                (vendedor_name, moneda_deuda)
            )
        
        # Record income in box
        descripcion = f"CONSIGNMENT PAYMENT: {vendedor_name}. Debt reduced by {monto_a_descontar:.2f} {moneda_deuda.upper()}"
        if nota:
            descripcion += f". Note: {nota}"
        
        MovimientoRepository.create(
            conn, 'ingreso', monto_pago, moneda_pago, caja_id, user_id, descripcion
        )
    
    return {
        "vendedor_id": vendedor_id,
        "vendedor_name": vendedor_name,
        "moneda_deuda": moneda_deuda,
        "deuda_anterior": deuda_actual,
        "monto_pagado": monto_pago,
        "moneda_pago": moneda_pago,
        "monto_descontado": monto_a_descontar,
        "deuda_restante": nuevo_monto,
        "caja_id": caja_id
    }

