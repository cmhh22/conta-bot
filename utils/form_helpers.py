"""
Utilities to create interactive button-based forms.
"""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from core.config import VALID_MONEDAS
from services.cajas_service import CajaService


def create_keyboard(buttons: List[List[str]], callback_prefix: str = "") -> InlineKeyboardMarkup:
    """
    Create an inline keyboard from a list of buttons.
    
    Args:
        buttons: List of lists containing button text
        callback_prefix: Prefix for callback_data
    
    Returns:
        InlineKeyboardMarkup
    """
    keyboard = []
    for row in buttons:
        keyboard_row = []
        for button_text in row:
            # Normalize text for callback
            callback_value = button_text.lower().replace(' ', '_').replace('-', '_')
            callback_data = f"{callback_prefix}:{callback_value}" if callback_prefix else callback_value
            keyboard_row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(keyboard_row)
    return InlineKeyboardMarkup(keyboard)


def create_moneda_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Create a keyboard to select currency."""
    buttons = [
        [moneda.upper() for moneda in VALID_MONEDAS],
        ["↩️ Cancel"]
    ]
    return create_keyboard(buttons, callback_prefix)


def create_caja_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Create a keyboard to select a cash box."""
    cajas = CajaService.listar()
    if cajas:
        # Use IDs in callback_data to identify boxes
        keyboard = []
        for caja in cajas:
            keyboard.append([
                InlineKeyboardButton(
                    caja['nombre'].upper(),
                    callback_data=f"{callback_prefix}:{caja['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("↩️ Cancel", callback_data=f"{callback_prefix}:cancelar")])
        return InlineKeyboardMarkup(keyboard)
    else:
        # Fallback if there are no boxes
        keyboard = [[InlineKeyboardButton("↩️ Cancel", callback_data=f"{callback_prefix}:cancelar")]]
        return InlineKeyboardMarkup(keyboard)


def create_yes_no_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Create a Yes/No confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton("❌ No", callback_data=f"{callback_prefix}:no")
        ],
        [InlineKeyboardButton("↩️ Cancel", callback_data=f"{callback_prefix}:cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_back_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    """Create a keyboard with a back button."""
    keyboard = [[InlineKeyboardButton("↩️ Back", callback_data=f"{callback_prefix}:back")]]
    return InlineKeyboardMarkup(keyboard)


def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the bot main menu."""
    keyboard = [
        [
            InlineKeyboardButton("💰 Accounting", callback_data="menu:contabilidad"),
            InlineKeyboardButton("📦 Inventory", callback_data="menu:inventario")
        ],
        [
            InlineKeyboardButton("📊 Reports", callback_data="menu:reportes"),
            InlineKeyboardButton("⚖️ Debts", callback_data="menu:deudas")
        ],
        [
            InlineKeyboardButton("🧰 Containers", callback_data="menu:contenedores"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu:config")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_contabilidad_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the accounting menu."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Income", callback_data="cont:ingreso"),
            InlineKeyboardButton("➖ Expense", callback_data="cont:gasto")
        ],
        [
            InlineKeyboardButton("🔄 Transfer", callback_data="cont:traspaso"),
            InlineKeyboardButton("📊 Balance", callback_data="cont:balance")
        ],
        [
            InlineKeyboardButton("💳 Supplier Payment", callback_data="cont:pago_proveedor"),
            InlineKeyboardButton("💵 Seller Payment", callback_data="cont:pago_vendedor")
        ],
        [InlineKeyboardButton("↩️ Main Menu", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_inventario_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the inventory menu."""
    keyboard = [
        [
            InlineKeyboardButton("📥 Inbound", callback_data="inv:entrada"),
            InlineKeyboardButton("📤 Sale", callback_data="inv:venta")
        ],
        [
            InlineKeyboardButton("📋 Stock", callback_data="inv:stock"),
            InlineKeyboardButton("📦 Consign", callback_data="inv:consignar")
        ],
        [
            InlineKeyboardButton("📊 Profit", callback_data="inv:ganancia"),
            InlineKeyboardButton("👤 Consigned Stock", callback_data="inv:stock_consignado")
        ],
        [InlineKeyboardButton("↩️ Main Menu", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_reportes_menu_keyboard() -> InlineKeyboardMarkup:
    """Create the reports menu."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Balance", callback_data="rep:balance"),
            InlineKeyboardButton("📜 History", callback_data="rep:historial")
        ],
        [
            InlineKeyboardButton("📈 Profit", callback_data="rep:ganancia"),
            InlineKeyboardButton("💾 Export", callback_data="rep:exportar")
        ],
        [InlineKeyboardButton("↩️ Main Menu", callback_data="menu:main")]
    ]
    return InlineKeyboardMarkup(keyboard)

