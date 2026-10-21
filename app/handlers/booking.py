
from datetime import date, datetime, time, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select, or_

from app.database.db import SessionFactory
from app.database.models import Appointment, Customer, Service


router = Router()


class BookingState(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()


def services_keyboard(services):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{service.name} — {service.price} ₽",
                    callback_data=f"service:{service.id}",
                )
            ]
            for service in services
        ]
    )


def dates_keyboard():
    today = date.today()
    buttons = []

    for offset in range(7):
        day = today + timedelta(days=offset)
        buttons.append([
            InlineKeyboardButton(
                text=day.strftime("%d.%m.%Y"),
                callback_data=f"date:{day.isoformat()}",
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def available_slots(day: date, duration: int):
    """Находит свободные получасовые слоты с 10:00 до 18:00."""

    opening = datetime.combine(day, time(10, 0))
    closing = datetime.combine(day, time(18, 0))
    now = datetime.now()
    slots = []

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment).where(
                Appointment.specialist_id == 0,
                Appointment.status == "confirmed",
                Appointment.start_time < closing,
                Appointment.end_time > opening,
            )
        )
        appointments = result.scalars().all()

    current = opening

    while current + timedelta(minutes=duration) <= closing:
        end = current + timedelta(minutes=duration)

        overlaps = any(
            appointment.start_time < end
            and appointment.end_time > current
            for appointment in appointments
        )

        if current > now and not overlaps:
            slots.append(current)

        current += timedelta(minutes=30)

    return slots


def slots_keyboard(slots):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=slot.strftime("%H:%M"),
                    callback_data=f"time:{slot.isoformat()}",
                )
            ]
            for slot in slots
        ]
    )


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext):
    async with SessionFactory() as session:
        result = await session.execute(
            select(Service).where(Service.is_active.is_(True))
            .order_by(Service.id)
        )
        services = result.scalars().all()

    if not services:
        await message.answer("Пока нет доступных услуг.")
        return

    await state.clear()
    await state.set_state(BookingState.choosing_service)

    await message.answer(
        "Выбери услугу:",
        reply_markup=services_keyboard(services),
    )


@router.callback_query(
    BookingState.choosing_service,
    F.data.startswith("service:"),
)
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])

    async with SessionFactory() as session:
        service = await session.get(Service, service_id)

    if service is None or not service.is_active:
        await callback.answer("Услуга недоступна.", show_alert=True)
        return

    await state.update_data(
        service_id=service.id,
        duration=service.duration_minutes,
        price=service.price,
        service_name=service.name,
    )
    await state.set_state(BookingState.choosing_date)

    await callback.message.edit_text(
        f"Услуга: {service.name}\n"
        f"Цена: {service.price} ₽\n"
        f"Длительность: {service.duration_minutes} мин.\n\n"
        "Выбери дату:",
        reply_markup=dates_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    BookingState.choosing_date,
    F.data.startswith("date:"),
)
async def choose_date(callback: CallbackQuery, state: FSMContext):
    selected_day = date.fromisoformat(callback.data.split(":")[1])

    if not date.today() <= selected_day <= date.today() + timedelta(days=6):
        await callback.answer("Выбери дату из списка.", show_alert=True)
        return

    data = await state.get_data()
    slots = await available_slots(selected_day, data["duration"])

    if not slots:
        await callback.answer("На эту дату свободного времени нет.")
        return

    await state.update_data(selected_date=selected_day.isoformat())
    await state.set_state(BookingState.choosing_time)

    await callback.message.edit_text(
        f"Дата: {selected_day.strftime('%d.%m.%Y')}\n"
        "Выбери свободное время:",
        reply_markup=slots_keyboard(slots),
    )
    await callback.answer()


@router.callback_query(
    BookingState.choosing_time,
    F.data.startswith("time:"),
)
async def choose_time(callback: CallbackQuery, state: FSMContext):
    selected_time = datetime.fromisoformat(callback.data.split(":", 1)[1])
    data = await state.get_data()

    selected_day = date.fromisoformat(data["selected_date"])
    start = datetime.combine(selected_day, selected_time.time())
    end = start + timedelta(minutes=data["duration"])

    if start <= datetime.now():
        await callback.answer("Это время уже прошло.", show_alert=True)
        return

    async with SessionFactory() as session:
        customer_result = await session.execute(
            select(Customer).where(
                Customer.telegram_id == callback.from_user.id
            )
        )
        customer = customer_result.scalar_one_or_none()

        if customer is None:
            await state.clear()
            await callback.answer(
                "Сначала отправь /start.",
                show_alert=True,
            )
            return

        # Повторно проверяем пересечение записей перед сохранением.
        conflict_result = await session.execute(
            select(Appointment.id).where(
                Appointment.specialist_id == 0,
                Appointment.status == "confirmed",
                Appointment.start_time < end,
                Appointment.end_time > start,
            ).limit(1)
        )

        if conflict_result.first() is not None:
            await callback.answer(
                "Это время только что заняли. Выбери другое.",
                show_alert=True,
            )
            await state.set_state(BookingState.choosing_date)
            await callback.message.edit_text(
                "Время уже занято. Выбери дату ещё раз:",
                reply_markup=dates_keyboard(),
            )
            return

        appointment = Appointment(
            customer_id=customer.id,
            service_id=data["service_id"],
            specialist_id=0,
            start_time=start,
            end_time=end,
            status="confirmed",
        )
        session.add(appointment)
        await session.commit()

    await state.clear()

    await callback.message.edit_text(
        "✅ Запись создана!\n\n"
        f"Услуга: {data['service_name']}\n"
        f"Дата: {start.strftime('%d.%m.%Y')}\n"
        f"Время: {start.strftime('%H:%M')}\n"
        f"Стоимость: {data['price']} ₽\n\n"
        "Запись сохранена в базе данных."
    )
    await callback.answer("Готово!")


@router.message(F.text == "👤 Мои записи")
async def my_appointments(message: Message):
    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment, Service)
            .join(Service, Appointment.service_id == Service.id)
            .join(Customer, Appointment.customer_id == Customer.id)
            .where(
                Customer.telegram_id == message.from_user.id,
                Appointment.status == "confirmed",
                Appointment.start_time >= datetime.now(),
            )
            .order_by(Appointment.start_time)
        )
        appointments = result.all()

    if not appointments:
        await message.answer(
            "📭 У тебя пока нет предстоящих записей.\n\n"
            "Нажми «📅 Записаться», чтобы выбрать услугу."
        )
        return

    for appointment, service in appointments:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌ Отменить запись",
                        callback_data=f"cancel:{appointment.id}",
                    )
                ]
            ]
        )

        await message.answer(
            "📅 Твоя запись\n\n"
            f"Услуга: {service.name}\n"
            f"Дата: {appointment.start_time:%d.%m.%Y}\n"
            f"Время: {appointment.start_time:%H:%M}\n"
            f"Стоимость: {service.price} ₽",
            reply_markup=keyboard,
        )


@router.callback_query(F.data.startswith("cancel:"))
async def cancel_appointment(callback: CallbackQuery):
    appointment_id = int(callback.data.split(":")[1])

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment)
            .join(Customer, Appointment.customer_id == Customer.id)
            .where(
                Appointment.id == appointment_id,
                Customer.telegram_id == callback.from_user.id,
                Appointment.status == "confirmed",
                Appointment.start_time >= datetime.now(),
            )
        )
        appointment = result.scalar_one_or_none()

        if appointment is None:
            await callback.answer(
                "Запись не найдена или уже отменена.",
                show_alert=True,
            )
            return

        appointment.status = "cancelled"
        await session.commit()

    await callback.message.edit_text(
        "✅ Запись отменена.\n\n"
        "Освободившееся время снова доступно для бронирования."
    )
    await callback.answer("Запись отменена!")
