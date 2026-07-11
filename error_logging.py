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
            logger.exception(f"""
            User: {getattr(user, "id", "Unknown")}
            Username: {getattr(user, "username", "Unknown")}
            Message: {event_text}
            """)
            raise
