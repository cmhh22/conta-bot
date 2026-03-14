"""
Utilidades para trabajar con updates de Telegram.
"""
from telegram import Update
from telegram.ext import ContextTypes


async def reply_or_edit(update: Update, text: str, parse_mode: str = None, reply_markup=None) -> None:
    """
    Responde a un mensaje o edita un mensaje de callback_query.
    
    Args:
        update: Update de Telegram
        text: Texto a enviar
        parse_mode: Modo de parseo (HTML, Markdown, etc.)
        reply_markup: Teclado inline opcional
    """
    if update.message:
        if parse_mode:
            await update.message.reply_html(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        # Si hay un callback_query, primero responder al callback
        await update.callback_query.answer()
        try:
            if parse_mode:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            # Si falla editar (mensaje muy largo o igual), enviar nuevo mensaje
            if update.callback_query.message:
                if parse_mode:
                    await update.callback_query.message.reply_html(text, reply_markup=reply_markup)
                else:
                    await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def reply_text(update: Update, text: str, reply_markup=None) -> None:
    """Envía un mensaje de texto."""
    await reply_or_edit(update, text, parse_mode=None, reply_markup=reply_markup)


async def reply_html(update: Update, text: str, reply_markup=None) -> None:
    """Envía un mensaje HTML."""
    await reply_or_edit(update, text, parse_mode="HTML", reply_markup=reply_markup)

