
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from sqlalchemy import select

from app.database.db import SessionFactory
from app.database.models import Appointment, Customer, Service


logger = logging.getLogger(__name__)


async def send_due_reminders(bot: Bot) -> None:
    now = datetime.now()

    async with SessionFactory() as session:
        result = await session.execute(
            select(Appointment, Customer.telegram_id, Service.name)
            .join(Customer, Appointment.customer_id == Customer.id)
            .join(Service, Appointment.service_id == Service.id)
            .where(
                Appointment.status == "confirmed",
                Appointment.start_time > now,
                Appointment.start_time <= now + timedelta(hours=24),
                Appointment.start_time - timedelta(hours=24) <= now,
                Appointment.reminder_sent.is_(False),
            )
        )

        reminders = result.all()

        for appointment, telegram_id, service_name in reminders:
            # Проверяем, что напоминание действительно уже пора отправлять.
            if appointment.start_time > now + timedelta(hours=24):
                continue

            try:
                await bot.send_message(
                    telegram_id,
                    "🔔 Напоминаем о вашей записи!\n\n"
                    f"✂️ Услуга: {service_name}\n"
                    f"📅 Дата: "
                    f"{appointment.start_time.strftime('%d.%m.%Y')}\n"
                    f"🕒 Время: "
                    f"{appointment.start_time.strftime('%H:%M')}\n\n"
                    "Будем ждать вас! 😊",
                )

                appointment.reminder_sent = True
                await session.commit()

            except Exception:
                await session.rollback()
                logger.exception(
                    "Не удалось отправить напоминание "
                    "по записи №%s",
                    appointment.id,
                )


async def reminder_loop(bot: Bot) -> None:
    while True:
        try:
            await send_due_reminders(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка в службе напоминаний")

        await asyncio.sleep(60)
