import logging
import os
from telegram_log_handler import TelegramLogHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(f"{LOG_DIR}/bot.log", encoding="utf-8")
file_handler.setFormatter(formatter)

error_handler = logging.FileHandler(f"{LOG_DIR}/errors.log", encoding="utf-8")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

console = logging.StreamHandler()
console.setFormatter(formatter)

telegram_handler = TelegramLogHandler()
telegram_handler.setLevel(logging.ERROR)
telegram_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console)
logger.addHandler(telegram_handler)