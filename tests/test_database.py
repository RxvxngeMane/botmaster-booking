
import pytest
from sqlalchemy import select

from app.database.db import SessionFactory, init_db
from app.database.models import Customer, Service


@pytest.mark.asyncio
async def test_database_initializes():
    await init_db()

    async with SessionFactory() as session:
        result = await session.execute(
            select(Service).where(Service.is_active.is_(True))
        )
        services = result.scalars().all()

        assert len(services) >= 1

        for service in services:
            assert service.price > 0
            assert service.duration_minutes > 0


@pytest.mark.asyncio
async def test_customer_can_be_created():
    await init_db()

    async with SessionFactory() as session:
        customer = Customer(
            telegram_id=-9876543210123,
            full_name="Тестовый клиент",
            username="test_customer",
        )

        session.add(customer)
        await session.flush()

        assert customer.id is not None
        assert customer.full_name == "Тестовый клиент"
        assert customer.loyalty_points == 0

        # Не сохраняем тестового клиента в настоящую базу.
        await session.rollback()
