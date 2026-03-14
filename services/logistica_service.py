"""
Servicio de logística - Lógica de negocio para movimientos de inventario.
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
    Agrega un producto a un contenedor.
    
    Args:
        contenedor_id: ID del contenedor
        producto_codigo: Código del producto
        cantidad: Cantidad a agregar
    
    Returns:
        Dict con los datos del producto agregado
    
    Raises:
        ValueError: Si el contenedor o producto no existen, o la cantidad es inválida
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    with get_db_connection() as conn:
        # Verificar que el contenedor existe
        contenedor = ContenedorRepository.obtener_por_id(conn, contenedor_id)
        if not contenedor:
            raise ValueError(f"No existe un contenedor con ID {contenedor_id}")
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
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
    Obtiene todos los productos de un contenedor.
    
    Args:
        contenedor_id: ID del contenedor
    
    Returns:
        Lista de diccionarios con los productos del contenedor
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
    Mueve un producto de un contenedor a un almacén.
    
    Args:
        contenedor_id: ID del contenedor origen
        almacen_id: ID del almacén destino
        producto_codigo: Código del producto a mover
        cantidad: Cantidad a mover
        user_id: ID del usuario que realiza el movimiento
        descripcion: Descripción opcional del movimiento
    
    Returns:
        Dict con los datos del movimiento realizado
    
    Raises:
        ValueError: Si no hay suficiente stock en el contenedor o los IDs no existen
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    with get_db_connection() as conn:
        # Verificar que el contenedor existe
        contenedor = ContenedorRepository.obtener_por_id(conn, contenedor_id)
        if not contenedor:
            raise ValueError(f"No existe un contenedor con ID {contenedor_id}")
        
        # Verificar que el almacén existe
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No existe un almacén con ID {almacen_id}")
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
        # Verificar stock disponible en el contenedor
        producto_en_contenedor = ContenedorProductoRepository.obtener_producto_en_contenedor(
            conn, contenedor_id, producto_codigo
        )
        if not producto_en_contenedor:
            raise ValueError(f"El producto '{producto_codigo}' no está en el contenedor {contenedor_id}")
        
        stock_disponible = producto_en_contenedor["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente. Disponible: {stock_disponible}, Solicitado: {cantidad}"
            )
        
        # Realizar el movimiento
        # 1. Reducir cantidad en contenedor
        ContenedorProductoRepository.reducir_cantidad(conn, contenedor_id, producto_codigo, cantidad)
        
        # 2. Agregar cantidad en almacén
        InventarioAlmacenRepository.agregar_producto(conn, almacen_id, producto_codigo, cantidad)
        
        # 3. Registrar el movimiento
        movimiento_id = MovimientoInventarioRepository.crear(
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
    Obtiene el inventario completo de un almacén.
    
    Args:
        almacen_id: ID del almacén
    
    Returns:
        Lista de diccionarios con el inventario del almacén
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
    Obtiene el historial de movimientos de un almacén.
    
    Args:
        almacen_id: ID del almacén
        limite: Límite de movimientos a retornar
    
    Returns:
        Lista de diccionarios con los movimientos
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
    Obtiene el historial de movimientos de un contenedor.
    
    Args:
        contenedor_id: ID del contenedor
        limite: Límite de movimientos a retornar
    
    Returns:
        Lista de diccionarios con los movimientos
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
    Mueve un producto de un almacén a otro.
    
    Args:
        almacen_origen_id: ID del almacén origen
        almacen_destino_id: ID del almacén destino
        producto_codigo: Código del producto a mover
        cantidad: Cantidad a mover
        user_id: ID del usuario que realiza el movimiento
        descripcion: Descripción opcional del movimiento
    
    Returns:
        Dict con los datos del movimiento realizado
    
    Raises:
        ValueError: Si no hay suficiente stock en el almacén origen o los IDs no existen
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    with get_db_connection() as conn:
        # Verificar que los almacenes existen
        almacen_origen = AlmacenRepository.obtener_por_id(conn, almacen_origen_id)
        if not almacen_origen:
            raise ValueError(f"No existe un almacén con ID {almacen_origen_id}")
        
        almacen_destino = AlmacenRepository.obtener_por_id(conn, almacen_destino_id)
        if not almacen_destino:
            raise ValueError(f"No existe un almacén con ID {almacen_destino_id}")
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
        # Verificar stock disponible en el almacén origen
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_origen_id, producto_codigo
        )
        if not producto_en_almacen:
            raise ValueError(f"El producto '{producto_codigo}' no está en el almacén {almacen_origen_id}")
        
        stock_disponible = producto_en_almacen["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente. Disponible: {stock_disponible}, Solicitado: {cantidad}"
            )
        
        # Realizar el movimiento
        # 1. Reducir cantidad en almacén origen
        InventarioAlmacenRepository.reducir_cantidad(conn, almacen_origen_id, producto_codigo, cantidad)
        
        # 2. Agregar cantidad en almacén destino
        InventarioAlmacenRepository.agregar_producto(conn, almacen_destino_id, producto_codigo, cantidad)
        
        # 3. Registrar el movimiento
        movimiento_id = MovimientoInventarioRepository.crear(
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
    Ajusta el inventario de un almacén (corrección de inventario).
    
    Args:
        almacen_id: ID del almacén
        producto_codigo: Código del producto
        nueva_cantidad: Nueva cantidad (debe ser >= 0)
        user_id: ID del usuario que realiza el ajuste
        descripcion: Descripción opcional del ajuste
    
    Returns:
        Dict con los datos del ajuste realizado
    
    Raises:
        ValueError: Si el almacén o producto no existen, o la cantidad es inválida
    """
    if nueva_cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa")
    
    with get_db_connection() as conn:
        # Verificar que el almacén existe
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No existe un almacén con ID {almacen_id}")
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
        # Obtener cantidad actual
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_id, producto_codigo
        )
        cantidad_anterior = producto_en_almacen["cantidad"] if producto_en_almacen else 0
        
        # Calcular diferencia
        diferencia = nueva_cantidad - cantidad_anterior
        
        # Actualizar inventario
        if producto_en_almacen:
            if nueva_cantidad == 0:
                InventarioAlmacenRepository.eliminar_producto(conn, almacen_id, producto_codigo)
            else:
                InventarioAlmacenRepository.actualizar_cantidad(conn, almacen_id, producto_codigo, nueva_cantidad)
        else:
            if nueva_cantidad > 0:
                InventarioAlmacenRepository.agregar_producto(conn, almacen_id, producto_codigo, nueva_cantidad)
        
        # Registrar el ajuste
        if diferencia != 0:
            MovimientoInventarioRepository.crear(
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
    Obtiene un resumen general de la logística.
    
    Returns:
        Dict con estadísticas de logística
    """
    with get_db_connection() as conn:
        # Contar contenedores
        contenedores = ContenedorRepository.obtener_todos(conn)
        total_contenedores = len(contenedores)
        
        # Contar productos en contenedores
        total_productos_contenedores = 0
        for cont in contenedores:
            productos = ContenedorProductoRepository.obtener_productos_por_contenedor(conn, cont["id"])
            total_productos_contenedores += len(productos)
        
        # Contar almacenes
        almacenes = AlmacenRepository.obtener_todos(conn)
        total_almacenes = len(almacenes)
        
        # Contar productos en almacenes
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
    Consigna un producto desde un almacén a un vendedor.
    
    Args:
        almacen_id: ID del almacén origen
        producto_codigo: Código del producto a consignar
        cantidad: Cantidad a consignar
        vendedor_id: ID del vendedor
        precio_venta: Precio unitario de venta
        moneda: Moneda del precio ('usd', 'cup', 'cup-t', 'eur')
        user_id: ID del usuario que realiza la consignación
    
    Returns:
        Dict con los datos de la consignación realizada
    
    Raises:
        ValueError: Si no hay suficiente stock en el almacén o los IDs no existen
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    if precio_venta <= 0:
        raise ValueError("El precio debe ser mayor a 0")
    
    from services.vendedores_service import VendedorService
    
    with get_db_connection() as conn:
        # Verificar que el almacén existe
        almacen = AlmacenRepository.obtener_por_id(conn, almacen_id)
        if not almacen:
            raise ValueError(f"No existe un almacén con ID {almacen_id}")
        
        # Verificar que el vendedor existe
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        if not vendedor:
            raise ValueError(f"No existe un vendedor con ID {vendedor_id}")
        
        vendedor_name = vendedor['name']
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
        # Verificar stock disponible en el almacén
        producto_en_almacen = InventarioAlmacenRepository.obtener_producto_en_almacen(
            conn, almacen_id, producto_codigo
        )
        if not producto_en_almacen:
            raise ValueError(f"El producto '{producto_codigo}' no está en el almacén {almacen_id}")
        
        stock_disponible = producto_en_almacen["cantidad"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente en el almacén. Disponible: {stock_disponible}, Solicitado: {cantidad}"
            )
        
        # Reducir inventario del almacén
        nueva_cantidad = stock_disponible - cantidad
        InventarioAlmacenRepository.actualizar_cantidad(
            conn, almacen_id, producto_codigo, nueva_cantidad
        )
        
        # Crear o actualizar consignación
        consignacion = ConsignacionRepository.obtener_por_vendedor_codigo(conn, vendedor_name, producto_codigo)
        if consignacion:
            nuevo_stock_consignado = consignacion['stock'] + cantidad
            ConsignacionRepository.actualizar_stock(conn, producto_codigo, vendedor_name, nuevo_stock_consignado)
        else:
            ConsignacionRepository.crear(conn, producto_codigo, vendedor_name, cantidad, precio_venta, moneda)
        
        # Generar deuda POR_COBRAR
        monto_total_deuda = cantidad * precio_venta
        deuda = DeudaRepository.obtener_por_actor(conn, vendedor_name, moneda, 'POR_COBRAR')
        if deuda:
            nuevo_monto = deuda['monto_pendiente'] + monto_total_deuda
            DeudaRepository.actualizar_monto(conn, vendedor_name, moneda, 'POR_COBRAR', nuevo_monto)
        else:
            DeudaRepository.crear(conn, vendedor_name, monto_total_deuda, moneda, 'POR_COBRAR')
        
        # Registrar movimiento de inventario
        MovimientoInventarioRepository.crear(
            conn,
            tipo='venta_almacen',
            origen_tipo='almacen',
            origen_id=almacen_id,
            destino_tipo=None,
            destino_id=None,
            producto_codigo=producto_codigo,
            cantidad=cantidad,
            user_id=user_id,
            descripcion=f"Consignación a vendedor {vendedor_name}"
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
    Mueve una consignación de un vendedor a otro.
    
    Args:
        vendedor_origen_id: ID del vendedor origen
        vendedor_destino_id: ID del vendedor destino
        producto_codigo: Código del producto a mover
        cantidad: Cantidad a mover
        user_id: ID del usuario que realiza el movimiento
    
    Returns:
        Dict con los datos del movimiento realizado
    
    Raises:
        ValueError: Si no hay suficiente stock consignado o los IDs no existen
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    with get_db_connection() as conn:
        # Verificar que los vendedores existen
        vendedor_origen = VendedorService.obtener_por_id(vendedor_origen_id)
        if not vendedor_origen:
            raise ValueError(f"No existe un vendedor con ID {vendedor_origen_id}")
        
        vendedor_destino = VendedorService.obtener_por_id(vendedor_destino_id)
        if not vendedor_destino:
            raise ValueError(f"No existe un vendedor con ID {vendedor_destino_id}")
        
        vendedor_origen_name = vendedor_origen['name']
        vendedor_destino_name = vendedor_destino['name']
        
        # Verificar que el producto existe
        producto = ProductoRepository.obtener_por_codigo(conn, producto_codigo)
        if not producto:
            raise ValueError(f"No existe un producto con código '{producto_codigo}'")
        
        # Verificar consignación en el vendedor origen
        consignacion_origen = ConsignacionRepository.obtener_por_vendedor_codigo(
            conn, vendedor_origen_name, producto_codigo
        )
        if not consignacion_origen:
            raise ValueError(
                f"El vendedor {vendedor_origen_name} no tiene consignación del producto '{producto_codigo}'"
            )
        
        stock_disponible = consignacion_origen["stock"]
        if stock_disponible < cantidad:
            raise ValueError(
                f"Stock consignado insuficiente. Disponible: {stock_disponible}, Solicitado: {cantidad}"
            )
        
        precio_unitario = consignacion_origen["precio_unitario"]
        moneda = consignacion_origen["moneda"]
        
        # Reducir consignación del vendedor origen
        nuevo_stock_origen = stock_disponible - cantidad
        if nuevo_stock_origen > 0:
            ConsignacionRepository.actualizar_stock(
                conn, producto_codigo, vendedor_origen_name, nuevo_stock_origen
            )
        else:
            # Si queda en 0, eliminar la consignación
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Consignaciones WHERE codigo = ? AND vendedor = ?",
                (producto_codigo, vendedor_origen_name)
            )
        
        # Crear o actualizar consignación del vendedor destino
        consignacion_destino = ConsignacionRepository.obtener_por_vendedor_codigo(
            conn, vendedor_destino_name, producto_codigo
        )
        if consignacion_destino:
            nuevo_stock_destino = consignacion_destino["stock"] + cantidad
            ConsignacionRepository.actualizar_stock(
                conn, producto_codigo, vendedor_destino_name, nuevo_stock_destino
            )
        else:
            ConsignacionRepository.crear(
                conn, producto_codigo, vendedor_destino_name, cantidad, precio_unitario, moneda
            )
        
        # Actualizar deudas
        monto_movimiento = cantidad * precio_unitario
        
        # Reducir deuda del vendedor origen
        deuda_origen = DeudaRepository.obtener_por_actor(conn, vendedor_origen_name, moneda, 'POR_COBRAR')
        if deuda_origen:
            nuevo_monto_origen = max(0, deuda_origen['monto_pendiente'] - monto_movimiento)
            if nuevo_monto_origen > 0:
                DeudaRepository.actualizar_monto(conn, vendedor_origen_name, moneda, 'POR_COBRAR', nuevo_monto_origen)
            else:
                # Si la deuda queda en 0, eliminarla
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM Deudas WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'",
                    (vendedor_origen_name, moneda)
                )
        
        # Aumentar deuda del vendedor destino
        deuda_destino = DeudaRepository.obtener_por_actor(conn, vendedor_destino_name, moneda, 'POR_COBRAR')
        if deuda_destino:
            nuevo_monto_destino = deuda_destino['monto_pendiente'] + monto_movimiento
            DeudaRepository.actualizar_monto(conn, vendedor_destino_name, moneda, 'POR_COBRAR', nuevo_monto_destino)
        else:
            DeudaRepository.crear(conn, vendedor_destino_name, monto_movimiento, moneda, 'POR_COBRAR')
    
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
    Registra el pago de una consignación (reduce la deuda POR_COBRAR).
    
    Args:
        vendedor_id: ID del vendedor que paga
        moneda_deuda: Moneda de la deuda a pagar ('usd', 'cup', 'cup-t', 'eur')
        monto_pago: Monto a pagar
        moneda_pago: Moneda del pago ('usd', 'cup', 'cup-t', 'eur')
        caja_id: ID de la caja donde se recibe el pago
        user_id: ID del usuario que registra el pago
        nota: Nota opcional del pago
    
    Returns:
        Dict con los datos del pago registrado
    
    Raises:
        ValueError: Si el vendedor no existe, no tiene deuda, o el monto es inválido
    """
    if monto_pago <= 0:
        raise ValueError("El monto a pagar debe ser mayor a 0")
    
    with get_db_connection() as conn:
        # Verificar que el vendedor existe
        vendedor = VendedorService.obtener_por_id(vendedor_id)
        if not vendedor:
            raise ValueError(f"No existe un vendedor con ID {vendedor_id}")
        
        vendedor_name = vendedor['name']
        
        # Verificar que existe la deuda
        deuda = DeudaRepository.obtener_por_actor(conn, vendedor_name, moneda_deuda, 'POR_COBRAR')
        if not deuda:
            raise ValueError(
                f"El vendedor {vendedor_name} no tiene deuda POR_COBRAR en {moneda_deuda.upper()}"
            )
        
        deuda_actual = deuda['monto_pendiente']
        
        # Convertir el pago a la moneda de la deuda si es necesario
        if moneda_pago != moneda_deuda:
            # Usar la función de conversión de moneda que ya maneja todas las monedas (usd, cup, cup-t, eur)
            monto_a_descontar = convert_currency(monto_pago, moneda_pago, moneda_deuda)
        else:
            monto_a_descontar = monto_pago
        
        # Verificar que el monto a descontar no exceda la deuda
        if monto_a_descontar > deuda_actual:
            raise ValueError(
                f"El monto a pagar ({monto_a_descontar:.2f} {moneda_deuda.upper()}) "
                f"excede la deuda actual ({deuda_actual:.2f} {moneda_deuda.upper()})"
            )
        
        # Reducir la deuda
        nuevo_monto = max(0, deuda_actual - monto_a_descontar)
        if nuevo_monto > 0:
            DeudaRepository.actualizar_monto(conn, vendedor_name, moneda_deuda, 'POR_COBRAR', nuevo_monto)
        else:
            # Si la deuda queda en 0, eliminarla
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM Deudas WHERE actor_id = ? AND moneda = ? AND tipo = 'POR_COBRAR'",
                (vendedor_name, moneda_deuda)
            )
        
        # Registrar el ingreso en la caja
        descripcion = f"PAGO CONSIGNACIÓN: {vendedor_name}. Deuda reducida en {monto_a_descontar:.2f} {moneda_deuda.upper()}"
        if nota:
            descripcion += f". Nota: {nota}"
        
        MovimientoRepository.crear(
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

