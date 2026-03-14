"""
Example usage of the export module.
This file shows how to use export functions.
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

# Example 1: Export transactions to PDF
def ejemplo_exportar_movimientos_pdf():
    """Example of how to export transactions to PDF."""
    movimientos = ContabilidadService.exportar_movimientos()
    filepath = export_movimientos_pdf(movimientos)
    print(f"PDF generated at: {filepath}")
    return filepath

# Example 2: Export transactions to Excel
def ejemplo_exportar_movimientos_excel():
    """Example of how to export transactions to Excel."""
    movimientos = ContabilidadService.exportar_movimientos()
    filepath = export_movimientos_excel(movimientos)
    print(f"Excel generated at: {filepath}")
    return filepath

# Example 3: Export inventory to PDF
def ejemplo_exportar_inventario_pdf():
    """Example of how to export inventory to PDF."""
    with get_db_connection() as conn:
        productos = ProductoRepository.obtener_todos(conn)
    productos_dict = [dict(prod) for prod in productos]
    filepath = export_inventario_pdf(productos_dict)
    print(f"Inventory PDF generated at: {filepath}")
    return filepath

# Example 4: Export inventory to Excel
def ejemplo_exportar_inventario_excel():
    """Example of how to export inventory to Excel."""
    with get_db_connection() as conn:
        productos = ProductoRepository.obtener_todos(conn)
    productos_dict = [dict(prod) for prod in productos]
    filepath = export_inventario_excel(productos_dict)
    print(f"Inventory Excel generated at: {filepath}")
    return filepath

# Example 5: Export debts to PDF
def ejemplo_exportar_deudas_pdf():
    """Example of how to export debts to PDF."""
    deudas = DeudaService.obtener_deudas_pendientes()
    filepath = export_deudas_pdf(deudas)
    print(f"Debts PDF generated at: {filepath}")
    return filepath

# Example 6: Export debts to Excel
def ejemplo_exportar_deudas_excel():
    """Example of how to export debts to Excel."""
    deudas = DeudaService.obtener_deudas_pendientes()
    filepath = export_deudas_excel(deudas)
    print(f"Debts Excel generated at: {filepath}")
    return filepath

# Example 7: Export external box to PDF
def ejemplo_exportar_caja_externa_pdf(caja_externa_id: int):
    """Example of how to export external box transfers to PDF."""
    from services.cajas_externas_service import CajaExternaService
    
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    if not caja_externa:
        print("External box not found")
        return None
    
    with get_db_connection() as conn:
        transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
    
    transferencias_dict = [dict(transf) for transf in transferencias]
    filepath = export_cajas_externas_pdf(transferencias_dict, caja_externa)
    print(f"External box PDF generated at: {filepath}")
    return filepath

# Example 8: Export external box to Excel
def ejemplo_exportar_caja_externa_excel(caja_externa_id: int):
    """Example of how to export external box transfers to Excel."""
    from services.cajas_externas_service import CajaExternaService
    
    caja_externa = CajaExternaService.obtener_por_id(caja_externa_id)
    if not caja_externa:
        print("External box not found")
        return None
    
    with get_db_connection() as conn:
        transferencias = TransferenciaExternaRepository.obtener_por_caja_externa(conn, caja_externa_id)
    
    transferencias_dict = [dict(transf) for transf in transferencias]
    filepath = export_cajas_externas_excel(transferencias_dict, caja_externa)
    print(f"External box Excel generated at: {filepath}")
    return filepath

