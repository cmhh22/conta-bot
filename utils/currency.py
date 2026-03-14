"""
Utilidades para conversión de monedas.
"""
import core.config as config


def get_tasa() -> float:
    """Obtiene la tasa de cambio actual."""
    return config.TASA_USD_CUP


def convert_to_usd(monto: float, moneda: str) -> float:
    """
    Convierte un monto a USD.
    
    Args:
        monto: Monto a convertir
        moneda: Moneda origen ('usd', 'cup', 'cup-t', 'eur')
    
    Returns:
        Monto en USD
    """
    if moneda == 'usd':
        return monto
    elif moneda in ('cup', 'cup-t'):
        return monto / get_tasa()
    elif moneda == 'eur':
        # 1 EUR = 1/TASA_USD_EUR USD
        return monto / config.TASA_USD_EUR
    else:
        raise ValueError(f"Moneda no soportada: {moneda}")


def convert_from_usd(monto_usd: float, moneda_destino: str) -> float:
    """
    Convierte un monto desde USD a otra moneda.
    
    Args:
        monto_usd: Monto en USD
        moneda_destino: Moneda destino ('usd', 'cup', 'cup-t', 'eur')
    
    Returns:
        Monto en la moneda destino
    """
    if moneda_destino == 'usd':
        return monto_usd
    elif moneda_destino in ('cup', 'cup-t'):
        return monto_usd * get_tasa()
    elif moneda_destino == 'eur':
        # 1 USD = TASA_USD_EUR EUR
        return monto_usd * config.TASA_USD_EUR
    else:
        raise ValueError(f"Moneda no soportada: {moneda_destino}")


def convert_currency(monto: float, moneda_origen: str, moneda_destino: str) -> float:
    """
    Convierte un monto entre dos monedas.
    
    Args:
        monto: Monto a convertir
        moneda_origen: Moneda origen
        moneda_destino: Moneda destino
    
    Returns:
        Monto convertido
    """
    if moneda_origen == moneda_destino:
        return monto
    
    # Convertir a USD primero
    monto_usd = convert_to_usd(monto, moneda_origen)
    # Convertir desde USD a destino
    return convert_from_usd(monto_usd, moneda_destino)

