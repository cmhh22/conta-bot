"""
Currency conversion utilities.
"""
import core.config as config


def get_tasa() -> float:
    """Get the current exchange rate."""
    return config.TASA_USD_CUP


def convert_to_usd(monto: float, moneda: str) -> float:
    """
    Convert an amount to USD.
    
    Args:
        monto: Amount to convert
        moneda: Source currency ('usd', 'cup', 'cup-t', 'eur')
    
    Returns:
        Amount in USD
    """
    if moneda == 'usd':
        return monto
    elif moneda in ('cup', 'cup-t'):
        return monto / get_tasa()
    elif moneda == 'eur':
        # 1 EUR = 1/TASA_USD_EUR USD
        return monto / config.TASA_USD_EUR
    else:
        raise ValueError(f"Unsupported currency: {moneda}")


def convert_from_usd(monto_usd: float, moneda_destino: str) -> float:
    """
    Convert an amount from USD to another currency.
    
    Args:
        monto_usd: Amount in USD
        moneda_destino: Destination currency ('usd', 'cup', 'cup-t', 'eur')
    
    Returns:
        Amount in the destination currency
    """
    if moneda_destino == 'usd':
        return monto_usd
    elif moneda_destino in ('cup', 'cup-t'):
        return monto_usd * get_tasa()
    elif moneda_destino == 'eur':
        # 1 USD = TASA_USD_EUR EUR
        return monto_usd * config.TASA_USD_EUR
    else:
        raise ValueError(f"Unsupported currency: {moneda_destino}")


def convert_currency(monto: float, moneda_origen: str, moneda_destino: str) -> float:
    """
    Convert an amount between two currencies.
    
    Args:
        monto: Amount to convert
        moneda_origen: Source currency
        moneda_destino: Destination currency
    
    Returns:
        Converted amount
    """
    if moneda_origen == moneda_destino:
        return monto
    
    # Convert to USD first
    monto_usd = convert_to_usd(monto, moneda_origen)
    # Convert from USD to destination
    return convert_from_usd(monto_usd, moneda_destino)

