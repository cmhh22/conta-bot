"""
Utilidades para crear formularios interactivos con botones.
"""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService


def create_keyboard(buttons: List[List[str]], callback_prefix: str = "") -> InlineKeyboardMarkup:
    """
    Crea un teclado inline desde una lista de botones.
    
    Args:
        buttons: Lista de listas con texto de botones
        callback_prefix: Prefijo para los callback_data
    
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button_text in row:
            # Normalizar el texto para callback
            callback_value = button_text.lower().replace(' ', '_').replace('-', '_')
            callback_data = f"{callback_prefix}:{callback_value}" if callback_prefix else callback_value
            keyboard_row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)


def create_moneda_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Crea un teclado para seleccionar moneda."""
    buttons = [
        [moneda.upper() for moneda in VALID_MONEDAS],
        ["↩️ Cancelar"]
    ]
    return create_keyboard(buttons, callback_prefix)


def create_caja_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Crea un teclado para seleccionar caja."""
    cajas = CajaService.listar()
    if cajas:
        # Usar IDs en callback_data para identificar cajas
        keyboard = []
        for caja in cajas:
            keyboard.append([
                InlineKeyboardButton(
                    caja['nombre'].upper(),
                    callback_data=f"{callback_prefix}:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Cancelar", callback_data=f"{callback_prefix}:cancelar")])
        return InlineKeyboardMarkup(keyboard)
    else:
        # Fallback si no hay cajas
        keyboard = [[InlineKeyboardButton("↩️ Cancelar", callback_data=f"{callback_prefix}:cancelar")]]
        return InlineKeyboardMarkup(keyboard)


def create_yes_no_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Crea un teclado de confirmación Sí/No."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton("❌ No", callback_data=f"{callback_prefix}:no")
        ],
        [InlineKeyboardButton("↩️ Cancelar", callback_data=f"{callback_prefix}:cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_back_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Crea un teclado con botón de volver."""
    keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data=f"{callback_prefix}:back")]]
    return InlineKeyboardMarkup(keyboard)


def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Crea el menú principal del bot."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Contabilidad", callback_data="menu:contabilidad"),
            InlineKeyboardButton("📦 Inventario", callback_data="menu:inventario")
        ],
        [
            InlineKeyboardButton("📊 Reportes", callback_data="menu:reportes"),
            InlineKeyboardButton("⚖️ Deudas", callback_data="menu:deudas")
        ],
        [
            InlineKeyboardButton("🧰 Contenedores", callback_data="menu:contenedores"),
            InlineKeyboardButton("⚙️ Configuración", callback_data="menu:config")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_contabilidad_menu_keyboard() -> InlineKeyboardMarkup:
    """Crea el menú de contabilidad."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Ingreso", callback_data="cont:ingreso"),
            InlineKeyboardButton("➖ Gasto", callback_data="cont:gasto")
        ],
        [
            InlineKeyboardButton("🔄 Traspaso", callback_data="cont:traspaso"),
            InlineKeyboardButton("📊 Balance", callback_data="cont:balance")
        ],
        [
            InlineKeyboardButton("💳 Pago Proveedor", callback_data="cont:pago_proveedor"),
            InlineKeyboardButton("💵 Pago Vendedor", callback_data="cont:pago_vendedor")
        ],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_inventario_menu_keyboard() -> InlineKeyboardMarkup:
    """Crea el menú de inventario."""
    keyboard = [
        [
            InlineKeyboardButton("📥 Entrada", callback_data="inv:entrada"),
            InlineKeyboardButton("📤 Venta", callback_data="inv:venta")
        ],
        [
            InlineKeyboardButton("📋 Stock", callback_data="inv:stock"),
            InlineKeyboardButton("📦 Consignar", callback_data="inv:consignar")
        ],
        [
            InlineKeyboardButton("📊 Ganancia", callback_data="inv:ganancia"),
            InlineKeyboardButton("👤 Stock Consignado", callback_data="inv:stock_consignado")
        ],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_reportes_menu_keyboard() -> InlineKeyboardMarkup:
    """Crea el menú de reportes."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Balance", callback_data="rep:balance"),
            InlineKeyboardButton("📜 Historial", callback_data="rep:historial")
        ],
        [
            InlineKeyboardButton("📈 Ganancia", callback_data="rep:ganancia"),
            InlineKeyboardButton("💾 Exportar", callback_data="rep:exportar")
        ],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)

