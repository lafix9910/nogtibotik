"""
Главный файл запуска Telegram-бота.
Содержит инициализацию бота, диспетчера, планировщика и запуск polling.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Импорт конфигурации
import config

# Импорт модулей бота
from database import db
from handlers import router
from utils import restore_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальный планировщик
scheduler = AsyncIOScheduler()


async def main():
    """
    Главная функция запуска бота.
    """
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключаем роутер
    dp.include_router(router)
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных...")
    await db.init_db()
    await db.generate_work_days()
    logger.info("База данных готова.")
    
    # Запускаем планировщик
    logger.info("Запуск планировщика...")
    scheduler.start()
    
    # Восстанавливаем задачи из базы данных
    await restore_scheduler(bot, scheduler)
    logger.info("Задачи напоминаний восстановлены.")
    
    # Запуск polling
    logger.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
