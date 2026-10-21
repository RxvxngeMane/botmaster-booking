
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database.models import Base, Service


DATABASE_URL = "sqlite+aiosqlite:///booking.db"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    # Создаём таблицы, которых ещё нет.
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    # Добавляем столбец напоминаний в существующую базу.
    async with engine.begin() as connection:
        result = await connection.execute(
            text("PRAGMA table_info(appointments)")
        )
        columns = {
            row[1] for row in result.fetchall()
        }

        if "reminder_sent" not in columns:
            await connection.execute(
                text(
                    "ALTER TABLE appointments "
                    "ADD COLUMN reminder_sent "
                    "BOOLEAN NOT NULL DEFAULT 0"
                )
            )

    # Добавляем стартовые услуги, только если их ещё нет.
    async with SessionFactory() as session:
        result = await session.execute(
            select(Service.id).limit(1)
        )

        if result.first() is None:
            session.add_all(
                [
                    Service(
                        name="Мужская стрижка",
                        description="Стрижка и укладка",
                        price=1000,
                        duration_minutes=60,
                    ),
                    Service(
                        name="Борода",
                        description="Оформление бороды",
                        price=500,
                        duration_minutes=30,
                    ),
                    Service(
                        name="Комплекс",
                        description=(
                            "Стрижка и оформление бороды"
                        ),
                        price=1300,
                        duration_minutes=90,
                    ),
                ]
            )
            await session.commit()


async def close_db() -> None:
    await engine.dispose()
