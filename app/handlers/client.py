
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from sqlalchemy import select

from app.database.db import SessionFactory
from app.database.models import Customer


router = Router()

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записаться")],
        [
            KeyboardButton(text="👤 Мои записи"),
            KeyboardButton(text="⭐ Мои бонусы"),
        ],
    ],
    resize_keyboard=True,
)


@router.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    if user is None:
        return

    async with SessionFactory() as session:
        result = await session.execute(
            select(Customer).where(
                Customer.telegram_id == user.id
            )
        )
        customer = result.scalar_one_or_none()

        if customer is None:
            customer = Customer(
                telegram_id=user.id,
                full_name=user.full_name,
                username=user.username,
            )
            session.add(customer)
            await session.commit()
            greeting = "Рад знакомству! Твой профиль создан 🎉"
        else:
            customer.full_name = user.full_name
            customer.username = user.username
            await session.commit()
            greeting = "С возвращением! 👋"

    await message.answer(
        f"Привет, {user.first_name}! 👋\n\n"
        f"{greeting}\n\n"
        "Добро пожаловать в BOOKING PRO.\n"
        "Здесь ты сможешь выбирать услуги, "
        "записываться и получать бонусы.",
        reply_markup=main_menu,
    )
