import logging
from aiogram import BaseMiddleware

logger = logging.getLogger(__name__)

class ErrorLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception:
            user = data.get("event_from_user")
            event_text = getattr(event, "text", None)
            callback = getattr(event, "data", None)
            chat = getattr(getattr(event, "chat", None), "id", None)
            logger.exception(f"""
            User: {getattr(user, "id", "Unknown")}
            Username: {getattr(user, "username", "Unknown")}
            Message: {event_text}
            Callback: {callback}
            Chat: {chat}
            """)
            raise
