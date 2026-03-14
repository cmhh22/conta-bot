"""
Validadores centralizados para el sistema.
"""
from typing import Optional
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService


class ValidationError(Exception):
    """Excepción personalizada para errores de validación."""
    pass


def validate_moneda(moneda: str) -> str:
    """Valida que la moneda sea válida."""
    moneda_lower = moneda.lower()
    if moneda_lower not in VALID_MONEDAS:
        raise ValidationError(f"Moneda '{moneda}' no válida. Usa: {', '.join(VALID_MONEDAS)}")
    return moneda_lower


def validate_caja(caja: str) -> int:
    """Valida que la caja sea válida y retorna su ID."""
    caja_lower = caja.lower().strip()
    caja_obj = CajaService.obtener_por_nombre(caja_lower)
    if not caja_obj:
        # Obtener lista de cajas disponibles para el mensaje de error
        cajas = CajaService.listar()
        nombres_cajas = [c['nombre'] for c in cajas]
        raise ValidationError(
            f"Caja '{caja}' no válida. Cajas disponibles: {', '.join(nombres_cajas) if nombres_cajas else 'Ninguna'}"
        )
    return caja_obj['id']


def validate_monto(monto_str: str) -> float:
    """Valida y convierte un monto a float."""
    try:
        monto = float(monto_str)
        if monto <= 0:
            raise ValidationError("El monto debe ser un número positivo.")
        return monto
    except ValueError:
        raise ValidationError(f"'{monto_str}' no es un número válido.")


def validate_cantidad(cantidad_str: str) -> float:
    """Valida y convierte una cantidad a float."""
    try:
        cantidad = float(cantidad_str)
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser un número positivo.")
        return cantidad
    except ValueError:
        raise ValidationError(f"'{cantidad_str}' no es un número válido.")


def validate_dias(dias_str: Optional[str], default: int = 7) -> int:
    """Valida y convierte días a entero."""
    if dias_str is None:
        return default
    try:
        dias = int(dias_str)
        if dias <= 0:
            raise ValidationError("El número de días debe ser un entero positivo.")
        return dias
    except ValueError:
        raise ValidationError(f"'{dias_str}' no es un número válido de días.")

