# main.py
"""
Основной модуль для запуска ботов
"""
import logging
import asyncio
import sys
from imitator import TelegramImitator
from controller import TelegramController
import config

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def start_bots():
    """
    Запуск обоих ботов
    """
    try:
        # Инициализация ботов
        imitator_bot = TelegramImitator()
        controller_bot = TelegramController()

        # Запуск ботов
        imitator_task = asyncio.create_task(imitator_bot.start())
        controller_task = asyncio.create_task(controller_bot.start())

        # Обработка сигналов завершения
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown(imitator_bot, controller_bot)))
        loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(shutdown(imitator_bot, controller_bot)))

        # Ждем завершения работы ботов
        await asyncio.gather(imitator_task, controller_task)

    except Exception as e:
        logger.error(f"Ошибка при запуске ботов: {str(e)}")
        sys.exit(1)


async def shutdown(imitator_bot, controller_bot):
    """
    Корректное завершение работы ботов
    """
    logger.info("Получен сигнал завершения работы")

    # Останавливаем ботов
    await imitator_bot.stop()
    await controller_bot.stop()

    # Завершаем работу асинхронного цикла
    asyncio.get_event_loop().stop()


if __name__ == "__main__":
    import signal

    logger.info("Запуск приложения")

    try:
        # Запускаем асинхронный цикл
        asyncio.run(start_bots())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено по команде пользователя")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        sys.exit(1)