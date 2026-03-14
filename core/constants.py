"""
Constantes del sistema.
"""
from typing import List, Literal

# Tipos de moneda válidos
Moneda = Literal['usd', 'cup', 'cup-t', 'eur']
VALID_MONEDAS: List[str] = ['usd', 'cup', 'cup-t', 'eur']

# Tipos de caja válidos
Caja = Literal['cfg', 'sc', 'trd']
VALID_CAJAS: List[str] = ['cfg', 'sc', 'trd']

# Tipos de movimiento
TipoMovimiento = Literal['ingreso', 'gasto', 'traspaso', 'venta', 'consignacion_finalizada']
TIPOS_MOVIMIENTO: List[str] = ['ingreso', 'gasto', 'traspaso', 'venta', 'consignacion_finalizada']

# Tipos de deuda
TipoDeuda = Literal['POR_PAGAR', 'POR_COBRAR']
TIPOS_DEUDA: List[str] = ['POR_PAGAR', 'POR_COBRAR']

