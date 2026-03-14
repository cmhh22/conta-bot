"""
Utilities for working with Telegram updates.
"""
from telegram import Update
from telegram.ext import ContextTypes


async def reply_or_edit(update: Update, text: str, parse_mode: str = None, reply_markup=None) -> None:
    """
    Reply to a message or edit a callback_query message.
    
    Args:
        update: Telegram update
        text: Text to send
        parse_mode: Parse mode (HTML, Markdown, etc.)
        reply_markup: Optional inline keyboard
    """
    if update.message:
        if parse_mode:
            await update.message.reply_html(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        # If there is a callback_query, answer it first
        await update.callback_query.answer()
        try:
            if parse_mode:
                await update.callback_query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
            else:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        except Exception:
            # If edit fails (message too long or unchanged), send a new message
            if update.callback_query.message:
                if parse_mode:
                    await update.callback_query.message.reply_html(text, reply_markup=reply_markup)
                else:
                    await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def reply_text(update: Update, text: str, reply_markup=None) -> None:
    """Send a plain text message."""
    await reply_or_edit(update, text, parse_mode=None, reply_markup=reply_markup)


async def reply_html(update: Update, text: str, reply_markup=None) -> None:
    """Send an HTML message."""
    await reply_or_edit(update, text, parse_mode="HTML", reply_markup=reply_markup)

