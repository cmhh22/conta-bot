"""
Configuración centralizada del proyecto.
Lee desde: 1) variables de entorno  2) archivo .env  3) config_secret.py (desarrollo local)
"""
from __future__ import annotations
import os
from typing import List

# Cargar .env si existe (para desarrollo local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv es opcional

# ==================== CONSTANTES ====================
VALID_MONEDAS = ['usd', 'cup', 'cup-t', 'eur']
VALID_CAJAS = ['cfg', 'sc', 'trd']

# Tasa de cambio USD a CUP (puede ser actualizada dinámicamente)
# Nota: Para persistencia, considerar guardar en BD
TASA_USD_CUP = 410.0
# Tasa de cambio USD a EUR (puede ser actualizada dinámicamente)
TASA_USD_EUR = 0.92  # Aproximadamente 1 USD = 0.92 EUR

# Nombre de la base de datos
DB_NAME = "contabilidad.db"

# Configuración de IA (opcional)
# Lee desde variable de entorno
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Override opcional desde archivo local (para desarrollo)
try:
    from config_secret import OPENAI_API_KEY as _OPENAI_API_KEY_LOCAL  # type: ignore
    OPENAI_API_KEY: str = _OPENAI_API_KEY_LOCAL or _OPENAI_API_KEY
except Exception:
    OPENAI_API_KEY = _OPENAI_API_KEY

USE_OPENAI = bool(OPENAI_API_KEY and OPENAI_API_KEY.strip())

# ==================== CONFIGURACIÓN DE TELEGRAM ====================
# Lee desde variables de entorno
_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_admin_ids_env = os.getenv("ADMIN_USER_IDS", "")

_ADMIN_USER_IDS: List[int] = []
if _admin_ids_env.strip():
    try:
        _ADMIN_USER_IDS = [int(x.strip()) for x in _admin_ids_env.split(",") if x.strip()]
    except ValueError:
        _ADMIN_USER_IDS = []

# Override opcional desde archivo local (para desarrollo)
try:
    from config_secret import TOKEN as _TOKEN_LOCAL, ADMIN_USER_IDS as _ADMIN_USER_IDS_LOCAL  # type: ignore
    # Usar el token local solo si existe y no está vacío, sino usar el de entorno
    TOKEN: str = _TOKEN_LOCAL if (_TOKEN_LOCAL and _TOKEN_LOCAL.strip()) else _TOKEN
    ADMIN_USER_IDS: List[int] = _ADMIN_USER_IDS_LOCAL if _ADMIN_USER_IDS_LOCAL else _ADMIN_USER_IDS
except (ImportError, AttributeError, Exception):
    # Si no existe config_secret.py o hay algún error, usar solo variables de entorno
    TOKEN = _TOKEN
    ADMIN_USER_IDS = _ADMIN_USER_IDS

# Validación final
if not isinstance(ADMIN_USER_IDS, list):
    ADMIN_USER_IDS = []

