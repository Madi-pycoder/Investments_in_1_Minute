from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
DB_URL_POSTGRES = os.getenv("DB_URL_POSTGRES")
REDIS_URL = os.getenv("REDIS_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ERROR_CHAT_ID = int(os.getenv("ERROR_CHAT_ID"))