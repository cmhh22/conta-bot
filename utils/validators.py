"""
Centralized validators for the system.
"""
from typing import Optional
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_moneda(moneda: str) -> str:
    """Validate that the currency is valid."""
    moneda_lower = moneda.lower()
    if moneda_lower not in VALID_MONEDAS:
        raise ValidationError(f"Invalid currency '{moneda}'. Use: {', '.join(VALID_MONEDAS)}")
    return moneda_lower


def validate_caja(caja: str) -> int:
    """Validate that the cash box is valid and return its ID."""
    caja_lower = caja.lower().strip()
    caja_obj = CajaService.obtener_por_nombre(caja_lower)
    if not caja_obj:
        # Get available cash box list for the error message
        cajas = CajaService.listar()
        nombres_cajas = [c['nombre'] for c in cajas]
        raise ValidationError(
            f"Invalid cash box '{caja}'. Available boxes: {', '.join(nombres_cajas) if nombres_cajas else 'None'}"
        )
    return caja_obj['id']


def validate_monto(monto_str: str) -> float:
    """Validate and convert an amount to float."""
    try:
        monto = float(monto_str)
        if monto <= 0:
            raise ValidationError("Amount must be a positive number.")
        return monto
    except ValueError:
        raise ValidationError(f"'{monto_str}' is not a valid number.")


def validate_cantidad(cantidad_str: str) -> float:
    """Validate and convert a quantity to float."""
    try:
        cantidad = float(cantidad_str)
        if cantidad <= 0:
            raise ValidationError("Quantity must be a positive number.")
        return cantidad
    except ValueError:
        raise ValidationError(f"'{cantidad_str}' is not a valid number.")


def validate_days(days_str: Optional[str], default: int = 7) -> int:
    """Validate and convert days to integer."""
    if days_str is None:
        return default
    try:
        days = int(days_str)
        if days <= 0:
            raise ValidationError("Number of days must be a positive integer.")
        return days
    except ValueError:
        raise ValidationError(f"'{days_str}' is not a valid number of days.")

