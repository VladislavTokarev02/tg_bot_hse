import os
from dotenv import load_dotenv # библиотека, которая будет загружать все переменные окружения

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

if not TOKEN:
    raise ValueError("Переменная окружения BOT TOKEN не установлена.")

if not API_KEY:
    raise ValueError("Переменная окружения API_KEY не установлена")