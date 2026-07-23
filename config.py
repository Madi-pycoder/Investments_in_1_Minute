from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
DB_URL_POSTGRES = os.getenv("DB_URL_POSTGRES")
REDIS_URL = os.getenv("REDIS_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ERROR_CHAT_ID = int(os.getenv("ERROR_CHAT_ID"))


FORBIDDEN_KEYWORDS = [
    "bank", "credit", "insurance", "casino", "gambling", "betting",
    "alcohol", "brewery", "tobacco", "porn", "adult", "weapons",
    "defense", "mortgage", "reit", "lending", "consumer finance"]
QUESTIONABLE_KEYWORDS = [
    "financial services", "capital markets", "asset management"]
FORCED_HARAM = {"SPY", "VOO", "IVV", "BRK-B", "BRK.B"}
SHARIAH_ETFS = {"SPUS", "HLAL", "SPRE", "SPSK", "UMMA", "SPTE", "SPWO", "ISDE", "GLD"}
STANDARD_CONFIG = {
    "AAOIFI": {
        "debt_limit": 0.30,
        "cash_limit": 0.30,
        "receivables_limit": 0.49,
        "interest_limit": 0.05,
        "denominator": "market_cap"},
    "MSCI": {
        "debt_limit": 0.33,
        "cash_limit": 0.33,
        "receivables_limit": 0.49,
        "interest_limit": 0.05,
        "denominator": "total_assets"}}
SHARIAH_BUFFER = 0.02


REPRESENTATIVE = {
    "lt100k": 50_000,
    "100_500": 300_000,
    "500_2m": 1_250_000,
    "gt2m": 2_500_000,}