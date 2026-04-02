"""
Утилиты бота.
Содержит функции проверки подписки, планировщика и другие вспомогательные функции.
"""

import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import ChatMemberUpdated
import config
from database import db


async def check_subscription(bot: Bot, user_id: int) -> bool:
    """
    Проверка подписки пользователя на канал.
    Возвращает True, если пользователь подписан.
    """
    try:
        member = await bot.get_chat_member(
            chat_id=config.CHANNEL_ID,
            user_id=user_id
        )
        
        # Проверяем статус пользователя
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False


async def send_reminder(bot: Bot, user_id: int, time: str):
    """Отправка напоминания пользователю."""
    try:
        message = (
            f"Напоминаем, что вы записаны на наращивание ресниц завтра в <b>{time}</b>.\n"
            f"Ждём вас ✨"
        )
        await bot.send_message(user_id, message, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки напоминания: {e}")


async def schedule_reminder(bot: Bot, user_id: int, date: str, time: str, booking_id: int, scheduler):
    """Планирование напоминания за 24 часа до записи."""
    
    # Парсим дату и время
    try:
        booking_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError:
        booking_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
    
    # Вычисляем время напоминания (за 24 часа)
    reminder_time = booking_datetime - timedelta(hours=24)
    
    # Проверяем, что до напоминания больше 24 часов
    now = datetime.now()
    if reminder_time <= now:
        return None
    
    # Создаем job_id
    job_id = f"reminder_{booking_id}_{user_id}"
    
    # Добавляем задачу в планировщик
    scheduler.add_job(
        send_reminder,
        'date',
        run_date=reminder_time,
        args=[bot, user_id, time],
        id=job_id,
        replace_existing=True
    )
    
    # Сохраняем в базу данных
    await db.add_reminder(
        booking_id=booking_id,
        user_id=user_id,
        run_time=reminder_time.isoformat(),
        job_id=job_id
    )
    
    return job_id


async def cancel_reminder(job_id: str, scheduler):
    """Отмена напоминания."""
    
    try:
        job = scheduler.get_job(job_id)
        if job:
            job.remove()
    except Exception:
        pass
    
    await db.remove_reminder(job_id)


async def restore_scheduler(bot: Bot, scheduler):
    """Восстановление задач планировщика после перезапуска."""
    
    reminders = await db.get_pending_reminders()
    
    for reminder in reminders:
        reminder_id, booking_id, user_id, run_time_str, job_id = reminder
        
        try:
            run_time = datetime.fromisoformat(run_time_str)
            
            # Проверяем, что время ещё не прошло
            if run_time > datetime.now():
                scheduler.add_job(
                    send_reminder,
                    'date',
                    run_date=run_time,
                    args=[bot, user_id, ""],  # Время будет взято из БД при отправке
                    id=job_id,
                    replace_existing=True
                )
        except Exception as e:
            print(f"Ошибка восстановления задачи {job_id}: {e}")


def format_date_russian(date_str: str) -> str:
    """Форматирование даты в русский формат."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        return f"{date_obj.day} {months[date_obj.month]} {date_obj.year} г."
    except ValueError:
        return date_str


def format_time_russian(time_str: str) -> str:
    """Форматирование времени в русский формат."""
    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        return f"{time_obj.hour}:{time_obj.strftime('%M')}"
    except ValueError:
        return time_str
