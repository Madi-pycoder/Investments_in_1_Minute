import logging
import asyncio
import traceback
from aiogram import Bot
from config import TOKEN, ERROR_CHAT_ID

class TelegramLogHandler(logging.Handler):
    def emit(self, record):
        try:
            text = self.format(record)
            async def send():
                bot = Bot(TOKEN)
                try:
                    await bot.send_message(ERROR_CHAT_ID,
                        f"❌ <b>Bot error</b>\n\n"
                        f"<pre>{text[:3900]}</pre>",
                        parse_mode="HTML")
                finally:
                    await bot.session.close()
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(send())
            except RuntimeError:
                asyncio.run(send())
        except Exception:
            print(traceback.format_exc())