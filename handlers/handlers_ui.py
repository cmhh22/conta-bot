# from telegram import Update
# from telegram.ext import ContextTypes
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup


# async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     """Muestra el menú principal con botones para los módulos."""
    
#     # 1. Definir la estructura del teclado
#     keyboard = [
#         [
#             InlineKeyboardButton("💰 Ingreso/Gasto", callback_data='menu_contabilidad'),
#             InlineKeyboardButton("📦 Inventario", callback_data='menu_inventario'),
#         ],
#         [
#             InlineKeyboardButton("📈 Reportes", callback_data='menu_reportes'),
#             InlineKeyboardButton("⚖️ Deudas", callback_data='menu_deudas'),
#         ],
#         [
#             InlineKeyboardButton("❓ Ayuda", callback_data='ayuda'),
#         ]
#     ]

#     reply_markup = InlineKeyboardMarkup(keyboard)

#     await update.message.reply_text(
#         "👋 **Bienvenido al Sistema de Gestión Contable!**\n\n"
#         "Selecciona una opción para acceder a los comandos:",
#         reply_markup=reply_markup,
#         parse_mode='Markdown'
#     )