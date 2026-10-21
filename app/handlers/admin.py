from sqlalchemy import func
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from config import ADMIN_IDS
from app.database.db import SessionFactory
from app.database.models import Appointment, Customer, Service


router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    await message.answer(
        "🛠 BOOKING PRO — админ-панель\n\n"
        "Команды:\n"
        "/bookings — предстоящие записи\n"
        "/services — список услуг\n\n"
        "Добавить услугу:\n"
        "/add_service Название | Цена | Минуты | Описание\n\n"
        "Пример:\n"
        "/add_service Окрашивание | 2500 | 120 | "
        "Окрашивание и уход\n\n"
        "/stats — статистика бизнеса\n\n"
        "/complete ID — завершить посещение\n\n"
        "/cancel_booking ID — отменить запись клиента\n"
    )


@router.message(Command("services"))
async def list_services(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with SessionFactory() as session:
        result = await session.execute(
            select(Service).order_by(Service.id)
        )
        services = result.scalars().all()

    if not services:
        await message.answer("Услуг пока нет.")
        return

    lines = ["📋 Услуги BOOKING PRO:\n"]

    for service in services:
        status = "Активна" if service.is_active else "Выключена"
        lines.append(
            f"#{service.id} — {service.name}\n"
            f"Цена: {service.price} ₽ | "
            f"{service.duration_minutes} мин.\n"
            f"Статус: {status}\n"
        )

    await message.answer("\n".join(lines))


@router.message(Command("add_service"))
async def add_service(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Формат:\n"
            "/add_service Название | Цена | Минуты | Описание"
        )
        return

    fields = [part.strip() for part in parts[1].split("|")]

    if len(fields) != 4:
        await message.answer(
            "Нужно указать 4 поля через символ |.\n"
            "Пример:\n"
            "/add_service Окрашивание | 2500 | 120 | "
            "Окрашивание и уход"
        )
        return

    name, price_text, duration_text, description = fields

    try:
        price = int(price_text)
        duration = int(duration_text)
    except ValueError:
        await message.answer("Цена и длительность должны быть числами.")
        return

    if not name or price < 0 or not 5 <= duration <= 600:
        await message.answer(
            "Проверь название, цену и длительность "
            "(от 5 до 600 минут)."
        )
        return

    async with SessionFactory() as session:
        service = Service(
            name=name,
            price=price,
            duration_minutes=duration,
            description=description,
            is_active=True,
        )
        session.add(service)
        await session.commit()

    await message.answer(
        "✅ Услуга добавлена!\n\n"
        f"Название: {name}\n"
        f"Цена: {price} ₽\n"
        f"Длительность: {duration} мин."
    )


@router.message(Command("bookings"))
async def list_bookings(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment, Customer, Service)
            .join(Customer, Appointment.customer_id == Customer.id)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.status == "confirmed",
                Appointment.start_time >= datetime.now(),
            )
            .order_by(Appointment.start_time)
            .limit(30)
        )
        rows = result.all()

    if not rows:
        await message.answer("📭 Предстоящих записей нет.")
        return

    lines = ["📅 Предстоящие записи (до 30):\n"]

    for appointment, customer, service in rows:
        lines.append(
            f"Запись #{appointment.id}\n"
            f"Клиент: {customer.full_name}\n"
            f"Услуга: {service.name}\n"
            f"Дата: {appointment.start_time:%d.%m.%Y}\n"
            f"Время: {appointment.start_time:%H:%M}\n"
        )

    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    now = datetime.now()

    async with SessionFactory() as session:
        # Общее количество клиентов
        customers_result = await session.execute(
            select(func.count(Customer.id))
        )
        customers_count = customers_result.scalar_one()

        # Все записи
        appointments_result = await session.execute(
            select(func.count(Appointment.id))
        )
        appointments_count = appointments_result.scalar_one()

        # Предстоящие подтверждённые записи
        upcoming_result = await session.execute(
            select(func.count(Appointment.id)).where(
                Appointment.status == "confirmed",
                Appointment.start_time >= now,
            )
        )
        upcoming_count = upcoming_result.scalar_one()

        # Количество завершённых посещений
        completed_result = await session.execute(
            select(func.count(Appointment.id)).where(
                Appointment.status == "completed"
            )
        )
        completed_count = completed_result.scalar_one()

        # Выручка по завершённым посещениям
        revenue_result = await session.execute(
            select(func.coalesce(func.sum(Service.price), 0))
            .select_from(Appointment)
            .join(Service, Appointment.service_id == Service.id)
            .where(Appointment.status == "completed")
        )
        revenue = revenue_result.scalar_one()

        # Топ-5 услуг по количеству записей
        popular_result = await session.execute(
            select(Service.name, func.count(Appointment.id).label("total"))
            .join(Appointment, Appointment.service_id == Service.id)
            .group_by(Service.id, Service.name)
            .order_by(func.count(Appointment.id).desc())
            .limit(5)
        )
        popular_services = popular_result.all()

    popular_text = (
        "\n".join(
            f"• {name} — {count} записей"
            for name, count in popular_services
        )
        if popular_services
        else "Пока данных нет"
    )

    await message.answer(
        "📊 BOOKING PRO — статистика\n\n"
        f"👥 Клиентов: {customers_count}\n"
        f"📅 Всего записей: {appointments_count}\n"
        f"🕒 Предстоящих записей: {upcoming_count}\n"
        f"✅ Завершённых посещений: {completed_count}\n"
        f"💰 Выручка по завершённым: {revenue} ₽\n\n"
        f"🏆 Популярные услуги:\n{popular_text}"
    )


@router.message(Command("complete"))
async def complete_appointment(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /complete ID\n"
            "Пример: /complete 5"
        )
        return

    appointment_id = int(parts[1])
    now = datetime.now()

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id
            )
        )
        appointment = result.scalar_one_or_none()

        if appointment is None:
            await message.answer("❌ Запись с таким ID не найдена.")
            return

        if appointment.status != "confirmed":
            await message.answer(
                "❌ Завершить можно только подтверждённую запись."
            )
            return

        if appointment.start_time > now:
            await message.answer(
                "⏳ Эта запись ещё не началась. "
                "Отметить посещение завершённым пока нельзя."
            )
            return

        appointment.status = "completed"
        await session.commit()

    await message.answer(
        f"✅ Запись №{appointment_id} отмечена как завершённая."
    )


@router.message(Command("cancel_booking"))
async def admin_cancel_booking(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    parts = (message.text or "").split(maxsplit=1)

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "Использование: /cancel_booking ID\n"
            "Например: /cancel_booking 5"
        )
        return

    appointment_id = int(parts[1])

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id
            )
        )
        appointment = result.scalar_one_or_none()

        if appointment is None:
            await message.answer("❌ Запись с таким ID не найдена.")
            return

        if appointment.status != "confirmed":
            await message.answer(
                "⚠️ Отменить можно только подтверждённую запись.\n"
                f"Текущий статус: {appointment.status}"
            )
            return

        appointment.status = "cancelled"
        await session.commit()

    await message.answer(
        f"✅ Запись №{appointment_id} отменена администратором."
    )
