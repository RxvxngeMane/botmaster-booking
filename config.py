
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "Не задан BOT_TOKEN. "
        "Добавь токен в переменные окружения."
    )

ADMIN_IDS = [
    int(user_id.strip())
    for user_id in __import__("os").getenv(
        "ADMIN_IDS", ""
    ).split(",")
    if user_id.strip().isdigit()
]