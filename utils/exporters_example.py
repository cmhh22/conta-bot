"""
Ejemplo de uso del módulo de exportación.
Este archivo muestra cómo usar las funciones de exportación.
"""
from utils.exporters import (
    export_movimientos_pdf,
    export_movimientos_excel,
    export_inventario_pdf,
    export_inventario_excel,
    export_deudas_pdf,
    export_deudas_excel,
    export_cajas_externas_pdf,
    export_cajas_externas_excel
)
from services.contabilidad_service import ContabilidadService, DeudaService
from services.inventario_service import InventarioService
from database.repositories import ProductoRepository, TransferenciaExternaRepository
from database.connection import get_db_connection

# Ejemplo 1: Exportar movimientos a PDF
def ejemplo_exportar_movimientos_pdf():
    """Ejemplo de cómo exportar movimientos a PDF."""
    movimientos = ContabilidadService.exportar_movimientos()
    filepath = export_movimientos_pdf(movimientos)
    print(f"PDF generado en: {filepath}")
    return filepath

# Ejemplo 2: Exportar movimientos a Excel
def ejemplo_exportar_movimientos_excel():
    """Ejemplo de cómo exportar movimientos a Excel."""
    movimientos = ContabilidadService.exportar_movimientos()
    filepath = export_movimientos_excel(movimientos)
    print(f"Excel generado en: {filepath}")
    return filepath

# Ejemplo 3: Exportar inventario a PDF
def ejemplo_exportar_inventario_pdf():
    """Ejemplo de cómo exportar inventario a PDF."""
    with get_db_connection() as conn:
        productos = ProductoRepository.obtener_todos(conn)
    productos_dict = [dict(prod) for prod in productos]
    filepath = export_inventario_pdf(productos_dict)
    print(f"PDF de inventario generado en: {filepath}")
    return filepath

# Ejemplo 4: Exportar inventario a Excel
def ejemplo_exportar_inventario_excel():
    """Ejemplo de cómo exportar inventario a Excel."""
    with get_db_connection() as conn:
        productos = ProductoRepository.obtener_todos(conn)
    productos_dict = [dict(prod) for prod in productos]
    filepath = export_inventario_excel(productos_dict)
    print(f"Excel de inventario generado en: {filepath}")
    return filepath

# Ejemplo 5: Exportar deudas a PDF
def ejemplo_exportar_deudas_pdf():
    """Ejemplo de cómo exportar deudas a PDF."""
    deudas = DeudaService.obtener_deudas_pendientes()
    filepath = export_deudas_pdf(deudas)
    print(f"PDF de deudas generado en: {filepath}")
    return filepath

# Ejemplo 6: Exportar deudas a Excel
def ejemplo_exportar_deudas_excel():
    """Ejemplo de cómo exportar deudas a Excel."""
    deudas = DeudaService.obtener_deudas_pendientes()
    filepath = export_deudas_excel(deudas)
    print(f"Excel de deudas generado en: {filepath}")
    return filepath

# Ejemplo 7: Exportar caja externa a PDF
def ejemplo_exportar_caja_externa_pdf(caja_externa_id: int):
    """Ejemplo de cómo exportar transferencias de caja externa a PDF."""
    from services.cajas_externas_service import CajaExternaService
    
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    if not caja_externa:
        print("Caja externa no encontrada")
        return None
    
    with get_db_connection() as conn:
        transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
    
    transferencias_dict = [dict(transf) for transf in transferencias]
    filepath = export_cajas_externas_pdf(transferencias_dict, caja_externa)
    print(f"PDF de caja externa generado en: {filepath}")
    return filepath

# Ejemplo 8: Exportar caja externa a Excel
def ejemplo_exportar_caja_externa_excel(caja_externa_id: int):
    """Ejemplo de cómo exportar transferencias de caja externa a Excel."""
    from services.cajas_externas_service import CajaExternaService
    
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    if not caja_externa:
        print("Caja externa no encontrada")
        return None
    
    with get_db_connection() as conn:
        transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
    
    transferencias_dict = [dict(transf) for transf in transferencias]
    filepath = export_cajas_externas_excel(transferencias_dict, caja_externa)
    print(f"Excel de caja externa generado en: {filepath}")
    return filepath

