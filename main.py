
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        "Привет! 👋\n\n"
        "Я бот для записи клиентов.\n"
        "Скоро здесь можно будет выбрать услугу "
        "и записаться на удобное время."
    )


@dp.message()
async def message_handler(message: Message):
    await message.answer(
        "Пока я учусь работать 😊\n"
        "Нажми /start, чтобы открыть главное меню."
    )


async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
