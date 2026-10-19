
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. "
        "Добавь токен в переменные окружения."
    )
