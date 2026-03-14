"""
Module to generate reports in PDF and Excel format.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try importing required libraries
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab is not installed. PDF exports will not be available.")

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger.warning("openpyxl is not installed. Excel exports will not be available.")


def _ensure_export_dir() -> Path:
    """Ensure the export directory exists."""
    export_dir = Path("exports")
    export_dir.mkdir(exist_ok=True)
    return export_dir


def export_movimientos_pdf(movimientos: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """
    Export transactions to a PDF file.
    
    Args:
        movimientos: List of dictionaries containing transactions
        filename: File name (optional)
    
    Returns:
        Generated PDF file path
    
    Raises:
        ImportError: If reportlab is not installed
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with: pip install reportlab")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimientos_{timestamp}.pdf"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    # Create PDF document
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph("TRANSACTIONS REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Report information
    fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    info_text = f"<b>Generated on:</b> {fecha_reporte}<br/>"
    info_text += f"<b>Total transactions:</b> {len(movimientos)}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    if not movimientos:
        story.append(Paragraph("There are no transactions to display.", styles['Normal']))
    else:
        # Prepare table data
        data = []
        
        # Headers
        headers = ['Date', 'Type', 'Amount', 'Currency', 'Box', 'Description']
        data.append(headers)
        
        # Data
        for mov in movimientos:
            fecha = mov.get('fecha', 'N/A')
            if isinstance(fecha, str) and ' ' in fecha:
                fecha = fecha.split()[0]  # Date only
            
            tipo = mov.get('tipo', 'N/A').upper()
            monto = mov.get('monto', 0)
            moneda = mov.get('moneda', 'N/A').upper()
            caja_nombre = mov.get('caja_nombre', mov.get('caja', 'N/A'))
            descripcion = mov.get('descripcion', '')[:50]  # Limit length
            
            row = [
                fecha,
                tipo,
                f"{monto:,.2f}",
                moneda,
                caja_nombre,
                descripcion
            ]
            data.append(row)
        
        # Create table
        table = Table(data, colWidths=[1*inch, 0.8*inch, 1*inch, 0.6*inch, 1*inch, 2*inch])
        
        # Table style
        table.setStyle(TableStyle([
            # Headers
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(table)
    
    # Build PDF
    doc.build(story)
    logger.info(f"PDF generated: {filepath}")
    return str(filepath)


def export_movimientos_excel(movimientos: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """
    Export transactions to an Excel file.
    
    Args:
        movimientos: List of dictionaries containing transactions
        filename: File name (optional)
    
    Returns:
        Generated Excel file path
    
    Raises:
        ImportError: If openpyxl is not installed
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is not installed. Install with: pip install openpyxl")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"movimientos_{timestamp}.xlsx"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    # Create workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    
    # Styles
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_align = Alignment(horizontal='center', vertical='center')
    
    # Headers
    headers = ['ID', 'Date', 'Type', 'Amount', 'Currency', 'Box', 'User ID', 'Description']
    ws.append(headers)
    
    # Apply header styling
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = border
    
    # Data
    for mov in movimientos:
        fecha = mov.get('fecha', 'N/A')
        if isinstance(fecha, str) and ' ' in fecha:
            fecha = fecha.split()[0]  # Date only
        
        row = [
            mov.get('id', ''),
            fecha,
            mov.get('tipo', 'N/A').upper(),
            mov.get('monto', 0),
            mov.get('moneda', 'N/A').upper(),
            mov.get('caja_nombre', mov.get('caja', 'N/A')),
            mov.get('user_id', ''),
            mov.get('descripcion', '')
        ]
        ws.append(row)
        
        # Apply row borders
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col_num)
            cell.border = border
    
    # Adjust column widths
    column_widths = {
        'A': 8,   # ID
        'B': 12,  # Date
        'C': 12,  # Tipo
        'D': 12,  # Amount
        'E': 10,  # Currency
        'F': 15,  # Box
        'G': 12,  # Usuario ID
        'H': 40,  # Description
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    # Freeze first row
    ws.freeze_panes = 'A2'
    
    # Save file
    wb.save(str(filepath))
    logger.info(f"Excel generated: {filepath}")
    return str(filepath)


def export_inventario_pdf(productos: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """
    Export product inventory to a PDF file.
    
    Args:
        productos: List of dictionaries containing products
        filename: File name (optional)
    
    Returns:
        Generated PDF file path
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with: pip install reportlab")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inventario_{timestamp}.pdf"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    story.append(Paragraph("INVENTORY REPORT", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    info_text = f"<b>Generated on:</b> {fecha_reporte}<br/>"
    info_text += f"<b>Total products:</b> {len(productos)}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    if not productos:
        story.append(Paragraph("There are no products in inventory.", styles['Normal']))
    else:
        data = []
        headers = ['Code', 'Name', 'Stock', 'Unit Cost', 'Currency', 'Sale Price']
        data.append(headers)
        
        for prod in productos:
            row = [
                prod.get('codigo', 'N/A'),
                prod.get('nombre', 'N/A')[:30],
                f"{prod.get('stock', 0):.2f}",
                f"{prod.get('costo_unitario', 0):,.2f}",
                prod.get('moneda_costo', 'N/A').upper(),
                f"{prod.get('precio_venta', 0):,.2f}" if prod.get('precio_venta') else 'N/A'
            ]
            data.append(row)
        
        table = Table(data, colWidths=[1*inch, 2.5*inch, 0.8*inch, 1*inch, 0.7*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
    
    doc.build(story)
    logger.info(f"Inventory PDF generated: {filepath}")
    return str(filepath)


def export_inventario_excel(productos: List[Dict[str, Any]], filename: Optional[str] = None) -> str:
    """
    Exporta inventario de productos a un archivo Excel.
    
    Args:
        productos: Lista de diccionarios con los productos
        filename: Nombre del archivo (opcional)
    
    Returns:
        Ruta del archivo Excel generado
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is not installed. Install with: pip install openpyxl")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inventario_{timestamp}.xlsx"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario"
    
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Code', 'Name', 'Stock', 'Unit Cost', 'Cost Currency', 'Sale Price']
    ws.append(headers)
    
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
    
    for prod in productos:
        row = [
            prod.get('codigo', ''),
            prod.get('nombre', ''),
            prod.get('stock', 0),
            prod.get('costo_unitario', 0),
            prod.get('moneda_costo', ''),
            prod.get('precio_venta', '') if prod.get('precio_venta') else None
        ]
        ws.append(row)
        
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col_num)
            cell.border = border
    
    column_widths = {'A': 15, 'B': 30, 'C': 12, 'D': 15, 'E': 12, 'F': 15}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    ws.freeze_panes = 'A2'
    wb.save(str(filepath))
    logger.info(f"Excel de inventario generado: {filepath}")
    return str(filepath)


def export_deudas_pdf(deudas: Dict[str, List[Dict[str, Any]]], filename: Optional[str] = None) -> str:
    """
    Exporta deudas a un archivo PDF.
    
    Args:
        deudas: Diccionario con 'por_pagar' y 'por_cobrar'
        filename: Nombre del archivo (opcional)
    
    Returns:
        Ruta del archivo PDF generado
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with: pip install reportlab")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deudas_{timestamp}.pdf"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph("REPORTE DE DEUDAS", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    fecha_reporte = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    story.append(Paragraph(f"<b>Generated on:</b> {fecha_reporte}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Cuentas por pagar
    story.append(Paragraph("<b>CUENTAS POR PAGAR (Supplieres)</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    if deudas.get('por_pagar'):
        data = [['Supplier', 'Amount', 'Currency']]
        for deuda in deudas['por_pagar']:
            data.append([
                deuda.get('actor_id', 'N/A'),
                f"{deuda.get('monto', 0):,.2f}",
                deuda.get('moneda', 'N/A').upper()
            ])
        
        table = Table(data, colWidths=[3*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC3545')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFE5E5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("<i>No deudas por pagar.</i>", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Cuentas por cobrar
    story.append(Paragraph("<b>CUENTAS POR COBRAR (Selleres)</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    if deudas.get('por_cobrar'):
        data = [['Seller', 'Amount', 'Currency']]
        for deuda in deudas['por_cobrar']:
            data.append([
                deuda.get('actor_id', 'N/A'),
                f"{deuda.get('monto', 0):,.2f}",
                deuda.get('moneda', 'N/A').upper()
            ])
        
        table = Table(data, colWidths=[3*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#E5FFE5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("<i>No deudas por cobrar.</i>", styles['Normal']))
    
    doc.build(story)
    logger.info(f"PDF de deudas generado: {filepath}")
    return str(filepath)


def export_deudas_excel(deudas: Dict[str, List[Dict[str, Any]]], filename: Optional[str] = None) -> str:
    """
    Exporta deudas a un archivo Excel.
    
    Args:
        deudas: Diccionario con 'por_pagar' y 'por_cobrar'
        filename: Nombre del archivo (opcional)
    
    Returns:
        Ruta del archivo Excel generado
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is not installed. Install with: pip install openpyxl")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"deudas_{timestamp}.xlsx"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    wb = Workbook()
    
    # Hoja de cuentas por pagar
    ws_pagar = wb.active
    ws_pagar.title = "Por Pagar"
    
    header_fill_red = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = ['Supplier', 'Amount', 'Currency']
    ws_pagar.append(headers)
    
    for col_num in range(1, len(headers) + 1):
        cell = ws_pagar.cell(row=1, column=col_num)
        cell.fill = header_fill_red
        cell.font = header_font
        cell.border = border
    
    if deudas.get('por_pagar'):
        for deuda in deudas['por_pagar']:
            row = [
                deuda.get('actor_id', ''),
                deuda.get('monto', 0),
                deuda.get('moneda', '').upper()
            ]
            ws_pagar.append(row)
            for col_num in range(1, len(headers) + 1):
                ws_pagar.cell(row=ws_pagar.max_row, column=col_num).border = border
    
    # Ajustar columnas
    ws_pagar.column_dimensions['A'].width = 30
    ws_pagar.column_dimensions['B'].width = 15
    ws_pagar.column_dimensions['C'].width = 10
    
    # Hoja de cuentas por cobrar
    ws_cobrar = wb.create_sheet("Por Cobrar")
    
    header_fill_green = PatternFill(start_color="28A745", end_color="28A745", fill_type="solid")
    ws_cobrar.append(headers)
    
    for col_num in range(1, len(headers) + 1):
        cell = ws_cobrar.cell(row=1, column=col_num)
        cell.fill = header_fill_green
        cell.font = header_font
        cell.border = border
    
    if deudas.get('por_cobrar'):
        for deuda in deudas['por_cobrar']:
            row = [
                deuda.get('actor_id', ''),
                deuda.get('monto', 0),
                deuda.get('moneda', '').upper()
            ]
            ws_cobrar.append(row)
            for col_num in range(1, len(headers) + 1):
                ws_cobrar.cell(row=ws_cobrar.max_row, column=col_num).border = border
    
    ws_cobrar.column_dimensions['A'].width = 30
    ws_cobrar.column_dimensions['B'].width = 15
    ws_cobrar.column_dimensions['C'].width = 10
    
    wb.save(str(filepath))
    logger.info(f"Excel de deudas generado: {filepath}")
    return str(filepath)


def export_cajas_externas_pdf(transferencias: List[Dict[str, Any]], caja_externa: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Export transfers from an external cash box to PDF.
    
    Args:
        transferencias: Lista de transferencias
        caja_externa: External cash box information
        filename: Nombre del archivo (opcional)
    
    Returns:
        Ruta del archivo PDF generado
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlab is not installed. Install with: pip install reportlab")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"caja_externa_{caja_externa.get('nombre', 'unknown')}_{timestamp}.pdf"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    story.append(Paragraph(f"EXTERNAL CASH BOX REPORT: {caja_externa.get('nombre', 'N/A')}", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    info_text = f"<b>Location:</b> {caja_externa.get('ubicacion', 'N/A')}<br/>"
    info_text += f"<b>Shipping Percentage:</b> {caja_externa.get('porcentaje_envio', 0):.2f}%<br/>"
    info_text += f"<b>Total Transfers:</b> {len(transferencias)}<br/>"
    info_text += f"<b>Generated on:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    if transferencias:
        data = [['Date', 'Product', 'Amount', 'Currency', 'Shipping', 'Received', 'Source Box']]
        
        for transf in transferencias:
            fecha = transf.get('fecha', 'N/A')
            if isinstance(fecha, str) and ' ' in fecha:
                fecha = fecha.split()[0]
            
            data.append([
                fecha,
                f"{transf.get('producto_codigo', 'N/A')} - {transf.get('producto_nombre', 'N/A')[:20]}",
                f"{transf.get('monto', 0):,.2f}",
                transf.get('moneda', 'N/A').upper(),
                f"{transf.get('monto_envio', 0):,.2f}",
                f"{transf.get('monto_recibido', 0):,.2f}",
                transf.get('caja_source_nombre', 'N/A')
            ])
        
        table = Table(data, colWidths=[0.9*inch, 1.8*inch, 0.9*inch, 0.7*inch, 0.9*inch, 0.9*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        
        # Resumen por moneda
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>SUMMARY BY CURRENCY</b>", styles['Heading3']))
        
        totales_por_moneda = {}
        for transf in transferencias:
            moneda = transf.get('moneda', 'N/A')
            if moneda not in totales_por_moneda:
                totales_por_moneda[moneda] = {'total': 0, 'envio': 0, 'recibido': 0}
            totales_por_moneda[moneda]['total'] += transf.get('monto', 0)
            totales_por_moneda[moneda]['envio'] += transf.get('monto_envio', 0)
            totales_por_moneda[moneda]['recibido'] += transf.get('monto_recibido', 0)
        
        resumen_data = [['Currency', 'Total Transferred', 'Total Shipping', 'Total Received']]
        for moneda, totales in totales_por_moneda.items():
            resumen_data.append([
                moneda.upper(),
                f"{totales['total']:,.2f}",
                f"{totales['envio']:,.2f}",
                f"{totales['recibido']:,.2f}"
            ])
        
        resumen_table = Table(resumen_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28A745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(resumen_table)
    else:
        story.append(Paragraph("<i>No transferencias recordeds.</i>", styles['Normal']))
    
    doc.build(story)
    logger.info(f"External cash box PDF generated: {filepath}")
    return str(filepath)


def export_cajas_externas_excel(transferencias: List[Dict[str, Any]], caja_externa: Dict[str, Any], filename: Optional[str] = None) -> str:
    """
    Export transfers from an external cash box to Excel.
    
    Args:
        transferencias: Lista de transferencias
        caja_externa: External cash box information
        filename: Nombre del archivo (opcional)
    
    Returns:
        Ruta del archivo Excel generado
    """
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is not installed. Install with: pip install openpyxl")
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"caja_externa_{caja_externa.get('nombre', 'unknown')}_{timestamp}.xlsx"
    
    export_dir = _ensure_export_dir()
    filepath = export_dir / filename
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Transferencias"
    
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # External cash box information
    ws.append(['External Cash Box:', caja_externa.get('nombre', 'N/A')])
    ws.append(['Location:', caja_externa.get('ubicacion', 'N/A')])
    ws.append(['Shipping Percentage:', f"{caja_externa.get('porcentaje_envio', 0):.2f}%"])
    ws.append(['Generated on:', datetime.now().strftime('%d/%m/%Y %H:%M:%S')])
    ws.append([])
    
    headers = ['Date', 'Product Code', 'Product Name', 'Amount', 'Currency', 'Shipping', 'Received', 'Source Box']
    ws.append(headers)
    
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=6, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
    
    for transf in transferencias:
        fecha = transf.get('fecha', 'N/A')
        if isinstance(fecha, str) and ' ' in fecha:
            fecha = fecha.split()[0]
        
        row = [
            fecha,
            transf.get('producto_codigo', ''),
            transf.get('producto_nombre', ''),
            transf.get('monto', 0),
            transf.get('moneda', '').upper(),
            transf.get('monto_envio', 0),
            transf.get('monto_recibido', 0),
            transf.get('caja_source_nombre', '')
        ]
        ws.append(row)
        
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col_num)
            cell.border = border
    
    column_widths = {'A': 12, 'B': 15, 'C': 25, 'D': 12, 'E': 10, 'F': 12, 'G': 12, 'H': 20}
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width
    
    ws.freeze_panes = 'A7'
    wb.save(str(filepath))
    logger.info(f"External cash box Excel generated: {filepath}")
    return str(filepath)

