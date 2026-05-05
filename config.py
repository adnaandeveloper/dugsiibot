import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ALLOWED_USERS = [int(x) for x in os.getenv("ALLOWED_USERS","").split(",") if x]