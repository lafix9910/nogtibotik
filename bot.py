"""
Главный файл запуска Telegram-бота.
Содержит инициализацию бота, диспетчера, планировщика и запуск polling.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from database import db
from handlers import router, set_scheduler
from utils import restore_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def main():
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    set_scheduler(scheduler)
    
    dp.include_router(router)
    
    logger.info("Инициализация базы данных...")
    await db.init_db()
    await db.generate_work_days()
    logger.info("База данных готова.")
    
    logger.info("Запуск планировщика...")
    scheduler.start()
    
    await restore_scheduler(bot, scheduler)
    logger.info("Задачи напоминаний восстановлены.")
    
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
