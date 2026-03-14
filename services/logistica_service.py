"""
Logistics service - Business logic for inventory movements.
"""
import logging
from typing import List, Dict, Any, Optional
from database.connection import get_db_connection
from database.repositories import (
    ContenedorProductoRepository,
    InventarioAlmacenRepository,
    MovimientoInventarioRepository,
    ProductoRepository,
    ContenedorRepository,
    AlmacenRepository,
    ConsignacionRepository,
    DeudaRepository,
    MovimientoRepository
)
from services.vendedores_service import VendedorService
from utils.currency import convert_to_usd, convert_currency
from core.config import TASA_USD_CUP

logger = logging.getLogger(__name__)


def agregar_producto_a_contenedor(contenedor_id: int, producto_codigo: str, cantidad: float) -> Dict[str, Any]:
    """
    Add a product to a container.
    
    Args:
        contenedor_id: Container ID
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
        contenedor = ContenedorRepository.obtener_por_id(conn, contenedor_id)
        if not contenedor:
            raise ValueError(f"No container exists with ID {contenedor_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        ContenedorProductoRepository.agregar_producto(conn, contenedor_id, producto_codigo, cantidad)
        producto_en_contenedor = ContenedorProductoRepository.obtener_producto_en_contenedor(
            conn, contenedor_id, producto_codigo
        )
        
        return {
            "contenedor_id": producto_en_contenedor["contenedor_id"],
            "producto_codigo": producto_en_contenedor["producto_codigo"],
            "cantidad": producto_en_contenedor["cantidad"],
            "fecha_ingreso": producto_en_contenedor["fecha_ingreso"]
        }


def obtener_productos_de_contenedor(contenedor_id: int) -> List[Dict[str, Any]]:
    """
    Get all products from a container.
    
    Args:
        contenedor_id: Container ID
    
    Returns:
        List of dictionaries with container products
    """
    with get_db_connection() as conn:
        productos = ContenedorProductoRepository.obtener_productos_por_contenedor(conn, contenedor_id)
        return [
            {
                "id": prod["id"],
                "contenedor_id": prod["contenedor_id"],
                "producto_codigo": prod["producto_codigo"],
                "producto_nombre": prod["producto_nombre"],
                "cantidad": prod["cantidad"],
                "fecha_ingreso": prod["fecha_ingreso"]
            }
            for prod in productos
        ]


def mover_producto_contenedor_a_almacen(contenedor_id: int, almacen_id: int, producto_codigo: str,
                                       cantidad: float, user_id: int, descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Move a product from a container to a warehouse.
    
    Args:
        contenedor_id: Source container ID
        almacen_id: Destination warehouse ID
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
        contenedor = ContenedorRepository.obtener_por_id(conn, contenedor_id)
        if not contenedor:
            raise ValueError(f"No container exists with ID {contenedor_id}")
        
        # Check that warehouse exists
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No warehouse exists with ID {almacen_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check available stock in container
        producto_en_contenedor = ContenedorProductoRepository.obtener_producto_en_contenedor(
            conn, contenedor_id, producto_codigo
        )
        if not producto_en_contenedor:
            raise ValueError(f"Product '{producto_codigo}' is not in container {contenedor_id}")
        
        stock_disponible = producto_en_contenedor["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Perform movement
        # 1. Reduce quantity in container
        ContenedorProductoRepository.reducir_cantidad(conn, contenedor_id, producto_codigo, cantidad)
        
        # 2. Add quantity in warehouse
        InventarioAlmacenRepository.agregar_producto(conn, almacen_id, producto_codigo, cantidad)
        
        # 3. Record movement
        movimiento_id = MovimientoInventarioRepository.create(
            conn,
            tipo="contenedor_a_almacen",
            origen_tipo="contenedor",
            origen_id=contenedor_id,
            destino_tipo="almacen",
            destino_id=almacen_id,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=descripcion
        )
        
        return {
            "movimiento_id": movimiento_id,
            "tipo": "contenedor_a_almacen",
            "contenedor_id": contenedor_id,
            "almacen_id": almacen_id,
            "producto_codigo": producto_codigo,
            "cantidad": cantidad,
            "descripcion": descripcion
        }


def obtener_inventario_almacen(almacen_id: int) -> List[Dict[str, Any]]:
    """
    Get full inventory for a warehouse.
    
    Args:
        almacen_id: Warehouse ID
    
    Returns:
        List of dictionaries with warehouse inventory
    """
    with get_db_connection() as conn:
        inventario = InventarioAlmacenRepository.obtener_inventario_por_almacen(conn, almacen_id)
        return [
            {
                "id": item["id"],
                "almacen_id": item["almacen_id"],
                "producto_codigo": item["producto_codigo"],
                "producto_nombre": item["producto_nombre"],
                "cantidad": item["cantidad"],
                "fecha_actualizacion": item["fecha_actualizacion"]
            }
            for item in inventario
        ]


def obtener_movimientos_almacen(almacen_id: int, limite: int = 50) -> List[Dict[str, Any]]:
    """
    Get movement history for a warehouse.
    
    Args:
        almacen_id: Warehouse ID
        limite: Maximum number of movements to return
    
    Returns:
        List of dictionaries with movements
    """
    with get_db_connection() as conn:
        movimientos = MovimientoInventarioRepository.obtener_por_almacen(conn, almacen_id, limite)
        return [
            {
                "id": mov["id"],
                "fecha": mov["fecha"],
                "tipo": mov["tipo"],
                "origen_tipo": mov["origen_tipo"],
                "origen_id": mov["origen_id"],
                "destino_tipo": mov["destino_tipo"],
                "destino_id": mov["destino_id"],
                "producto_codigo": mov["producto_codigo"],
                "producto_nombre": mov["producto_nombre"],
                "cantidad": mov["cantidad"],
                "user_id": mov["user_id"],
                "descripcion": mov["descripcion"]
            }
            for mov in movimientos
        ]


def obtener_movimientos_contenedor(contenedor_id: int, limite: int = 50) -> List[Dict[str, Any]]:
    """
    Get movement history for a container.
    
    Args:
        contenedor_id: Container ID
        limite: Maximum number of movements to return
    
    Returns:
        List of dictionaries with movements
    """
    with get_db_connection() as conn:
        movimientos = MovimientoInventarioRepository.obtener_por_contenedor(conn, contenedor_id, limite)
        return [
            {
                "id": mov["id"],
                "fecha": mov["fecha"],
                "tipo": mov["tipo"],
                "origen_tipo": mov["origen_tipo"],
                "origen_id": mov["origen_id"],
                "destino_tipo": mov["destino_tipo"],
                "destino_id": mov["destino_id"],
                "producto_codigo": mov["producto_codigo"],
                "producto_nombre": mov["producto_nombre"],
                "cantidad": mov["cantidad"],
                "user_id": mov["user_id"],
                "descripcion": mov["descripcion"]
            }
            for mov in movimientos
        ]


def mover_producto_almacen_a_almacen(almacen_origen_id: int, almacen_destino_id: int,
                                     producto_codigo: str, cantidad: float, user_id: int,
                                     descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Move a product from one warehouse to another.
    
    Args:
        almacen_origen_id: Source warehouse ID
        almacen_destino_id: Destination warehouse ID
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
        almacen_origen = AlmacenRepository.obtener_por_id(conn, almacen_origen_id)
        if not almacen_origen:
            raise ValueError(f"No warehouse exists with ID {almacen_origen_id}")
        
        almacen_destino = AlmacenRepository.obtener_por_id(conn, almacen_destino_id)
        if not almacen_destino:
            raise ValueError(f"No warehouse exists with ID {almacen_destino_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check available stock in source warehouse
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_origen_id, producto_codigo
        )
        if not producto_en_almacen:
            raise ValueError(f"Product '{producto_codigo}' is not in warehouse {almacen_origen_id}")
        
        stock_disponible = producto_en_almacen["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Perform movement
        # 1. Reduce quantity in source warehouse
        InventarioAlmacenRepository.reducir_cantidad(conn, almacen_origen_id, producto_codigo, cantidad)
        
        # 2. Add quantity in destination warehouse
        InventarioAlmacenRepository.agregar_producto(conn, almacen_destino_id, producto_codigo, cantidad)
        
        # 3. Record movement
        movimiento_id = MovimientoInventarioRepository.create(
            conn,
            tipo="almacen_a_almacen",
            origen_tipo="almacen",
            origen_id=almacen_origen_id,
            destino_tipo="almacen",
            destino_id=almacen_destino_id,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=descripcion
        )
        
        return {
            "movimiento_id": movimiento_id,
            "tipo": "almacen_a_almacen",
            "almacen_origen_id": almacen_origen_id,
            "almacen_destino_id": almacen_destino_id,
            "producto_codigo": producto_codigo,
            "cantidad": cantidad,
            "descripcion": descripcion
        }


def ajustar_inventario_almacen(almacen_id: int, producto_codigo: str, nueva_cantidad: float,
                               user_id: int, descripcion: Optional[str] = None) -> Dict[str, Any]:
    """
    Adjust warehouse inventory (inventory correction).
    
    Args:
        almacen_id: Warehouse ID
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
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No warehouse exists with ID {almacen_id}")
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Get current quantity
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_id, producto_codigo
        )
        cantidad_anterior = producto_en_almacen["cantidad"] if producto_en_almacen else 0
        
        # Calculate difference
        diferencia = nueva_cantidad - cantidad_anterior
        
        # Update inventory
        if producto_en_almacen:
            if nueva_cantidad == 0:
                InventarioAlmacenRepository.delete_producto(conn, almacen_id, producto_codigo)
            else:
                InventarioAlmacenRepository.update_cantidad(conn, almacen_id, producto_codigo, nueva_cantidad)
        else:
            if nueva_cantidad > 0:
                InventarioAlmacenRepository.agregar_producto(conn, almacen_id, producto_codigo, nueva_cantidad)
        
        # Record adjustment
        if diferencia != 0:
            MovimientoInventarioRepository.create(
                conn,
                tipo="ajuste",
                origen_tipo="almacen",
                origen_id=almacen_id,
                destino_tipo=None,
                destino_id=None,
                producto_codigo=producto_codigo,
                cantidad=abs(diferencia),
                user_id=user_id,
                descripcion=descripcion or f"Ajuste: {cantidad_anterior} → {nueva_cantidad}"
            )
        
        return {
            "almacen_id": almacen_id,
            "producto_codigo": producto_codigo,
            "cantidad_anterior": cantidad_anterior,
            "nueva_cantidad": nueva_cantidad,
            "diferencia": diferencia,
            "descripcion": descripcion
        }


def obtener_resumen_logistica() -> Dict[str, Any]:
    """
    Get a high-level logistics summary.
    
    Returns:
        Dict with logistics statistics
    """
    with get_db_connection() as conn:
        # Count containers
        contenedores = ContenedorRepository.obtener_todos(conn)
        total_contenedores = len(contenedores)
        
        # Count products in containers
        total_productos_contenedores = 0
        for cont in contenedores:
            productos = ContenedorProductoRepository.obtener_productos_por_contenedor(conn, cont["id"])
            total_productos_contenedores += len(productos)
        
        # Count warehouses
        almacenes = AlmacenRepository.obtener_todos(conn)
        total_almacenes = len(almacenes)
        
        # Count products in warehouses
        total_productos_almacenes = 0
        for alm in almacenes:
            inventario = InventarioAlmacenRepository.obtener_inventario_por_almacen(conn, alm["id"])
            total_productos_almacenes += len(inventario)
        
        return {
            "total_contenedores": total_contenedores,
            "total_productos_contenedores": total_productos_contenedores,
            "total_almacenes": total_almacenes,
            "total_productos_almacenes": total_productos_almacenes
        }


def consignar_desde_almacen(almacen_id: int, producto_codigo: str, cantidad: float,
                            vendedor_id: int, precio_venta: float, moneda: str,
                            user_id: int) -> Dict[str, Any]:
    """
    Consign a product from a warehouse to a seller.
    
    Args:
        almacen_id: Source warehouse ID
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
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No warehouse exists with ID {almacen_id}")
        
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
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_id, producto_codigo
        )
        if not producto_en_almacen:
            raise ValueError(f"Product '{producto_codigo}' is not in warehouse {almacen_id}")
        
        stock_disponible = producto_en_almacen["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient stock in warehouse. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        # Reduce warehouse inventory
        nueva_cantidad = stock_disponible - cantidad
        InventarioAlmacenRepository.update_cantidad(
            conn, almacen_id, producto_codigo, nueva_cantidad
        )
        
        # Create or update consignment
        consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(conn, vendedor_name, producto_codigo)
        if consignacion:
            nuevo_stock_consignado = consignacion['stock'] + cantidad
            ConsignacionRepository.update_stock(conn, producto_codigo, vendedor_name, nuevo_stock_consignado)
        else:
            ConsignacionRepository.create(conn, producto_codigo, vendedor_name, cantidad, precio_venta, moneda)
        
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
            tipo='venta_almacen',
            origen_tipo='almacen',
            origen_id=almacen_id,
            destino_tipo=None,
            destino_id=None,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=f"Consignment to seller {vendedor_name}"
        )
    
    return {
        "almacen_id": almacen_id,
        "producto_codigo": producto_codigo,
        "cantidad": cantidad,
        "vendedor_id": vendedor_id,
        "vendedor_name": vendedor_name,
        "precio_venta": precio_venta,
        "moneda": moneda,
        "monto_deuda": monto_total_deuda
    }


def mover_consignacion_vendedor(vendedor_origen_id: int, vendedor_destino_id: int,
                                producto_codigo: str, cantidad: float,
                                user_id: int) -> Dict[str, Any]:
    """
    Move a consignment from one seller to another.
    
    Args:
        vendedor_origen_id: Source seller ID
        vendedor_destino_id: Destination seller ID
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
        vendedor_origen = VendedorService.obtener_por_id(vendedor_origen_id)
        if not vendedor_origen:
            raise ValueError(f"No seller exists with ID {vendedor_origen_id}")
        
        vendedor_destino = VendedorService.obtener_por_id(vendedor_destino_id)
        if not vendedor_destino:
            raise ValueError(f"No seller exists with ID {vendedor_destino_id}")
        
        vendedor_origen_name = vendedor_origen['name']
        vendedor_destino_name = vendedor_destino['name']
        
        # Check that product exists
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No product exists with code '{producto_codigo}'")
        
        # Check source seller consignment
        consignacion_origen = ConsignacionRepository.obtener_por_vendedor_codigo(
            conn, vendedor_origen_name, producto_codigo
        )
        if not consignacion_origen:
            raise ValueError(
                f"Seller {vendedor_origen_name} has no consignment for product '{producto_codigo}'"
            )
        
        stock_disponible = consignacion_origen["stock"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Insufficient consigned stock. Available: {stock_disponible}, Requested: {cantidad}"
            )
        
        precio_unitario = consignacion_origen["precio_unitario"]
        moneda = consignacion_origen["moneda"]
        
        # Reduce source seller consignment
        nuevo_stock_origen = stock_disponible - cantidad
        if nuevo_stock_origen > 0:
            ConsignacionRepository.update_stock(
                conn, producto_codigo, vendedor_origen_name, nuevo_stock_origen
            )
        else:
            # If it reaches 0, delete the consignment
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Consignaciones WHERE codigo = ? AND vendedor = ?",
                (producto_codigo, vendedor_origen_name)
            )
        
        # Create or update destination seller consignment
        consignacion_destino = ConsignacionRepository.obtener_por_vendedor_codigo(
            conn, vendedor_destino_name, producto_codigo
        )
        if consignacion_destino:
            nuevo_stock_destino = consignacion_destino["stock"] + cantidad
            ConsignacionRepository.update_stock(
                conn, producto_codigo, vendedor_destino_name, nuevo_stock_destino
            )
        else:
            ConsignacionRepository.create(
                conn, producto_codigo, vendedor_destino_name, cantidad, precio_unitario, moneda
            )
        
        # Update debts
        monto_movimiento = cantidad * precio_unitario
        
        # Reduce source seller debt
        deuda_origen = DeudaRepository.obtener_por_actor(conn, vendedor_origen_name, moneda, 'POR_COBRAR')
        if deuda_origen:
            nuevo_monto_origen = max(0, deuda_origen['monto_pendiente'] - monto_movimiento)
            if nuevo_monto_origen > 0:
                DeudaRepository.update_monto(conn, vendedor_origen_name, moneda, 'POR_COBRAR', nuevo_monto_origen)
            else:
                # If debt reaches 0, remove it
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM Deudas WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'",
                    (vendedor_origen_name, moneda)
                )
        
        # Increase destination seller debt
        deuda_destino = DeudaRepository.obtener_por_actor(conn, vendedor_destino_name, moneda, 'POR_COBRAR')
        if deuda_destino:
            nuevo_monto_destino = deuda_destino['monto_pendiente'] + monto_movimiento
            DeudaRepository.update_monto(conn, vendedor_destino_name, moneda, 'POR_COBRAR', nuevo_monto_destino)
        else:
            DeudaRepository.create(conn, vendedor_destino_name, monto_movimiento, moneda, 'POR_COBRAR')
    
    return {
        "vendedor_origen_id": vendedor_origen_id,
        "vendedor_origen_name": vendedor_origen_name,
        "vendedor_destino_id": vendedor_destino_id,
        "vendedor_destino_name": vendedor_destino_name,
        "producto_codigo": producto_codigo,
        "cantidad": cantidad,
        "precio_unitario": precio_unitario,
        "moneda": moneda,
        "monto_movimiento": monto_movimiento
    }


def pagar_consignacion(vendedor_id: int, moneda_deuda: str, monto_pago: float,
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

