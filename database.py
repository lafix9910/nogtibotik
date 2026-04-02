"""
Модуль базы данных SQLite.
Содержит все операции с базой данных для записи клиентов.
"""

import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


class Database:
    """Класс для работы с базой данных SQLite."""

    def __init__(self, db_path: str = "nail_salon.db"):
        """Инициализация базы данных."""
        self.db_path = db_path

    async def init_db(self):
        """Создание таблиц в базе данных."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS work_days (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    is_closed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS time_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    is_available INTEGER DEFAULT 1,
                    booking_id INTEGER,
                    UNIQUE(date, time)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    reminder_sent INTEGER DEFAULT 0
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    booking_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    run_time TEXT NOT NULL,
                    job_id TEXT UNIQUE NOT NULL,
                    sent INTEGER DEFAULT 0
                )
            """)

            await db.commit()

    async def generate_work_days(self):
        """Генерация рабочих дней на 1 неделю вперед."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT date FROM work_days")
            existing_dates = {row[0] for row in await cursor.fetchall()}

            today = datetime.now().date()
            new_dates = []

            for i in range(7):
                date = today + timedelta(days=i)
                date_str = date.isoformat()
                if date_str not in existing_dates:
                    new_dates.append((date_str,))

            if new_dates:
                await db.executemany(
                    "INSERT OR IGNORE INTO work_days (date) VALUES (?)",
                    new_dates
                )
                await db.commit()
                
                for date_str, in new_dates:
                    for hour in range(9, 19):
                        time = f"{hour:02d}:00"
                        await db.execute(
                            "INSERT OR IGNORE INTO time_slots (date, time) VALUES (?, ?)",
                            (date_str, time)
                        )
                await db.commit()

    async def get_available_dates(self) -> List[str]:
        """Получение списка доступных дат."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT date FROM work_days 
                WHERE is_closed = 0 
                AND date >= date('now')
                ORDER BY date
            """)
            return [row[0] for row in await cursor.fetchall()]

    async def is_date_closed(self, date: str) -> bool:
        """Проверка, закрыт ли день."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT is_closed FROM work_days WHERE date = ?",
                (date,)
            )
            result = await cursor.fetchone()
            return result[0] == 1 if result else True

    async def add_time_slot(self, date: str, time: str) -> bool:
        """Добавление временного слота."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR IGNORE INTO time_slots (date, time) VALUES (?, ?)",
                    (date, time)
                )
                await db.commit()
                return True
        except Exception:
            return False

    async def remove_time_slot(self, date: str, time: str) -> bool:
        """Удаление временного слота."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM time_slots WHERE date = ? AND time = ? AND is_available = 1",
                (date, time)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_available_slots(self, date: str) -> List[str]:
        """Получение доступных временных слотов на дату."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT time FROM time_slots 
                WHERE date = ? AND is_available = 1 
                ORDER BY time
            """, (date,))
            return [row[0] for row in await cursor.fetchall()]

    async def get_all_slots(self, date: str) -> List[Tuple]:
        """Получение всех временных слотов на дату."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT time, is_available FROM time_slots 
                WHERE date = ? 
                ORDER BY time
            """, (date,))
            return await cursor.fetchall()

    async def has_active_booking(self, user_id: int) -> bool:
        """Проверка, есть ли у пользователя активная запись."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM bookings 
                WHERE user_id = ?
            """, (user_id,))
            result = await cursor.fetchone()
            return result[0] > 0

    async def create_booking(self, user_id: int, user_name: str, 
                           phone: str, date: str, time: str) -> bool:
        """Создание записи клиента."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT is_available FROM time_slots 
                WHERE date = ? AND time = ?
            """, (date, time))
            result = await cursor.fetchone()
            
            if not result or result[0] == 0:
                return False

            await db.execute("""
                INSERT INTO bookings (user_id, user_name, phone, date, time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, user_name, phone, date, time))
            
            cursor = await db.execute("SELECT last_insert_rowid()")
            booking_id = (await cursor.fetchone())[0]

            await db.execute("""
                UPDATE time_slots 
                SET is_available = 0, booking_id = ?
                WHERE date = ? AND time = ?
            """, (booking_id, date, time))

            await db.commit()
            return True

    async def get_booking(self, user_id: int) -> Optional[Tuple]:
        """Получение активной записи пользователя."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_name, phone, date, time, created_at
                FROM bookings 
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            return await cursor.fetchone()

    async def cancel_booking(self, user_id: int, booking_id: int = None) -> bool:
        """Отмена записи клиента."""
        async with aiosqlite.connect(self.db_path) as db:
            if booking_id:
                cursor = await db.execute(
                    "SELECT date, time FROM bookings WHERE id = ? AND user_id = ?",
                    (booking_id, user_id)
                )
                booking = await cursor.fetchone()
                
                if not booking:
                    return False

                date, time = booking

                await db.execute(
                    "DELETE FROM reminders WHERE booking_id = ?",
                    (booking_id,)
                )

                await db.execute(
                    "DELETE FROM bookings WHERE id = ?",
                    (booking_id,)
                )

                await db.execute("""
                    UPDATE time_slots 
                    SET is_available = 1, booking_id = NULL
                    WHERE date = ? AND time = ?
                """, (date, time))

                await db.commit()
                return True
            else:
                cursor = await db.execute(
                    "SELECT id, date, time FROM bookings WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                    (user_id,)
                )
                booking = await cursor.fetchone()
                
                if not booking:
                    return False

                booking_id, date, time = booking

                await db.execute(
                    "DELETE FROM reminders WHERE booking_id = ?",
                    (booking_id,)
                )

                await db.execute(
                    "DELETE FROM bookings WHERE id = ?",
                    (booking_id,)
                )

                await db.execute("""
                    UPDATE time_slots 
                    SET is_available = 1, booking_id = NULL
                    WHERE date = ? AND time = ?
                """, (date, time))

                await db.commit()
                return True

    async def get_all_bookings(self, date: str = None) -> List[Tuple]:
        """Получение всех записей."""
        async with aiosqlite.connect(self.db_path) as db:
            if date:
                cursor = await db.execute("""
                    SELECT id, user_id, user_name, phone, date, time, created_at
                    FROM bookings 
                    WHERE date = ?
                    ORDER BY date, time
                """, (date,))
            else:
                cursor = await db.execute("""
                    SELECT id, user_id, user_name, phone, date, time, created_at
                    FROM bookings 
                    ORDER BY date, time
                """)
            return await cursor.fetchall()

    async def get_bookings_count(self, date: str) -> int:
        """Получение количества записей на дату."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM bookings WHERE date = ?",
                (date,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def add_reminder(self, booking_id: int, user_id: int, 
                          run_time: str, job_id: str):
        """Добавление напоминания в базу данных."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO reminders (booking_id, user_id, run_time, job_id)
                VALUES (?, ?, ?, ?)
            """, (booking_id, user_id, run_time, job_id))
            await db.commit()

    async def remove_reminder(self, job_id: str):
        """Удаление напоминания."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM reminders WHERE job_id = ?", (job_id,))
            await db.commit()

    async def get_pending_reminders(self) -> List[Tuple]:
        """Получение ожидающих напоминаний."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, booking_id, user_id, run_time, job_id
                FROM reminders 
                WHERE sent = 0
                ORDER BY run_time
            """)
            return await cursor.fetchall()

    async def mark_reminder_sent(self, job_id: str):
        """Отметка напоминания как отправленного."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE reminders SET sent = 1 WHERE job_id = ?",
                (job_id,)
            )
            await db.commit()

    async def close_day(self, date: str):
        """Закрытие дня для записи."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE work_days SET is_closed = 1 WHERE date = ?",
                (date,)
            )
            await db.commit()

    async def open_day(self, date: str):
        """Открытие дня для записи."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE work_days SET is_closed = 0 WHERE date = ?",
                (date,)
            )
            await db.commit()

    async def get_all_dates(self) -> List[str]:
        """Получение всех рабочих дат (включая закрытые)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT date FROM work_days 
                ORDER BY date
            """)
            return [row[0] for row in await cursor.fetchall()]
    
    async def add_single_work_day(self, date: str):
        """Добавление одного рабочего дня со слотами."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO work_days (date) VALUES (?)",
                (date,)
            )
            await db.commit()
            
            for hour in range(9, 19):
                time = f"{hour:02d}:00"
                await db.execute(
                    "INSERT OR IGNORE INTO time_slots (date, time) VALUES (?, ?)",
                    (date, time)
                )
            await db.commit()
    
    async def remove_single_work_day(self, date: str):
        """Удаление рабочего дня и всех слотов."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM time_slots WHERE date = ?", (date,))
            await db.execute("DELETE FROM work_days WHERE date = ?", (date,))
            await db.commit()


db = Database()
