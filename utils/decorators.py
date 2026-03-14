"""
Decoradores útiles para el sistema.
"""
from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_IDS


def admin_only(func: Callable) -> Callable:
    """
    Decorador para restringir comandos solo a administradores.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any):
        user_id = update.effective_user.id
        if user_id not in ADMIN_USER_IDS:
            if update.message:
                await update.message.reply_text("⛔ No tienes permiso.")
            elif update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text("⛔ No tienes permiso.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

