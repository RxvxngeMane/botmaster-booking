
import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN
from app.database.db import init_db, close_db
from app.handlers.client import router as client_router
from app.handlers.booking import router as booking_router
from app.handlers.admin import router as admin_router
from app.services.reminders import reminder_loop


async def main():
    session = AiohttpSession(
        proxy="http://127.0.0.1:10809"
    )

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
    )

    dp = Dispatcher()

    dp.include_router(client_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)

    reminder_task = None

    try:
        await init_db()
        print("База данных подключена!")
        print("BOOKING PRO запущен!")

        reminder_task = asyncio.create_task(
            reminder_loop(bot)
        )

        await dp.start_polling(bot)

    finally:
        if reminder_task is not None:
            reminder_task.cancel()

            with suppress(asyncio.CancelledError):
                await reminder_task

        await close_db()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
