# BOOKING PRO — Telegram-бот для записи клиентов

BOOKING PRO — Telegram-бот для автоматизации записи клиентов на услуги. Проект разработан на Python с использованием aiogram 3, SQLAlchemy и SQLite.

## Возможности

-  Запись клиентов на услуги через Telegram.
-  Выбор даты и свободного времени.
-  Каталог услуг с ценами и продолжительностью.
-  Просмотр и отмена собственных записей.
-  Автоматические напоминания о предстоящих записях.
-  Система бонусных баллов для клиентов.
-  Административные команды для управления записями и услугами.
-  Статистика клиентов, записей и выручки.
- ️ Хранение данных в SQLite.
-  Автоматические тесты базы данных.

## Технологии

- Python 3.14+
- aiogram 3
- SQLAlchemy
- SQLite
- aiosqlite
- pytest
- pytest-asyncio
- Git и GitHub

## Установка и запуск

### 1. Клонирование проекта

```bash
git clone https://github.com/RxvxngeMane/botmaster-booking.git
cd botmaster-booking
```

### 2. Создание виртуального окружения

```bash
python -m venv .venv
```

Активация в Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Установка зависимостей

```bash
python -m pip install -r requirements.txt
```

### 4. Настройка токена

Создай переменные окружения `BOT_TOKEN` и `ADMIN_IDS`.

- `BOT_TOKEN` — токен Telegram-бота, полученный через BotFather.
- `ADMIN_IDS` — Telegram ID администраторов.

Не публикуй токен бота в открытом репозитории.

### 5. Запуск

```bash
python main.py
```

При первом запуске база данных и начальный каталог услуг создаются автоматически.

## Административные команды

| Команда | Назначение |
|---|---|
| `/admin` | Панель администратора |
| `/services` | Список услуг |
| `/add_service` | Добавление услуги |
| `/bookings` | Просмотр записей |
| `/stats` | Статистика |
| `/complete ID` | Завершение записи |
| `/cancel_booking ID` | Отмена записи |

## Структура проекта

```text
botmaster-booking/
├── app/
│   ├── database/
│   │   ├── models.py
│   │   └── db.py
│   ├── handlers/
│   │   ├── client.py
│   │   ├── booking.py
│   │   └── admin.py
│   ├── keyboards/
│   └── services/
│       └── reminders.py
├── tests/
│   └── test_database.py
├── config.py
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Тестирование

Запуск тестов:

```bash
python -m pytest -v
```

## Статус проекта

Проект находится в активной разработке. Основные функции записи, управления услугами, администрирования и напоминаний реализованы.

## Автор

### Султан Азаматович