"""
Useful decorators for the system.
"""
from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from core.config import ADMIN_USER_IDS


def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict commands to administrators only.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args: Any, **kwargs: Any):
        user_id = update.effective_user.id
        if user_id not in ADMIN_USER_IDS:
            if update.message:
                await update.message.reply_text("⛔ You do not have permission.")
            elif update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text("⛔ You do not have permission.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

