# main.py
"""
Основной модуль для запуска ботов
"""
import logging
import asyncio
import sys
import signal
import traceback
import platform
from imitator import TelegramImitator
from controller import TelegramController
import config

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Флаг для отслеживания состояния завершения
shutdown_event = asyncio.Event()


async def start_bots():
    """
    Запуск обоих ботов
    """
    try:
        # Инициализация ботов
        logger.info("Инициализация имитатора бота")
        imitator_bot = TelegramImitator()

        logger.info("Инициализация контроллера бота")
        controller_bot = TelegramController()

        # Запуск ботов
        logger.info("Запуск имитатора бота")
        imitator_task = asyncio.create_task(imitator_bot.start())

        logger.info("Запуск контроллера бота")
        controller_task = asyncio.create_task(controller_bot.start())

        # Настройка обработки сигналов с учетом платформы
        setup_signal_handlers(imitator_bot, controller_bot)

        # Задача для мониторинга события завершения
        shutdown_monitor = asyncio.create_task(
            monitor_shutdown(imitator_bot, controller_bot)
        )

        # Ждем завершения работы ботов или сигнала завершения
        await asyncio.gather(imitator_task, controller_task, shutdown_monitor)

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Ошибка при запуске ботов: {str(e)}")
        logger.error(f"Подробная информация об ошибке: {error_details}")

        # Логирование информации о состоянии ботов, если они были инициализированы
        if 'imitator_bot' in locals():
            logger.error(f"Статус имитатора бота: {getattr(imitator_bot, 'status', 'Неизвестно')}")
        if 'controller_bot' in locals():
            logger.error(f"Статус контроллера бота: {getattr(controller_bot, 'status', 'Неизвестно')}")

        sys.exit(1)


def setup_signal_handlers(imitator_bot, controller_bot):
    """
    Настройка обработчиков сигналов с учетом текущей платформы
    """
    if platform.system() != 'Windows':
        # Для Unix-подобных систем используем add_signal_handler
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(
            signal.SIGINT,
            lambda: handle_exit_signal(imitator_bot, controller_bot)
        )
        loop.add_signal_handler(
            signal.SIGTERM,
            lambda: handle_exit_signal(imitator_bot, controller_bot)
        )
        logger.info("Настроены Unix-обработчики сигналов")
    else:
        # Для Windows настраиваем обработчики через signal.signal
        signal.signal(signal.SIGINT, lambda sig, frame: handle_exit_signal_windows(imitator_bot, controller_bot))
        signal.signal(signal.SIGTERM, lambda sig, frame: handle_exit_signal_windows(imitator_bot, controller_bot))
        logger.info("Настроены Windows-обработчики сигналов")


def handle_exit_signal(imitator_bot, controller_bot):
    """
    Обработчик сигналов для Unix-систем (вызывается в event loop)
    """
    logger.info("Получен сигнал завершения работы (Unix)")
    shutdown_event.set()


def handle_exit_signal_windows(imitator_bot, controller_bot):
    """
    Обработчик сигналов для Windows
    """
    logger.info("Получен сигнал завершения работы (Windows)")
    # Для Windows нужно установить событие из другого потока
    asyncio.run_coroutine_threadsafe(
        set_shutdown_event(),
        asyncio.get_event_loop()
    )


async def set_shutdown_event():
    """
    Вспомогательная функция для установки флага завершения
    """
    shutdown_event.set()


async def monitor_shutdown(imitator_bot, controller_bot):
    """
    Мониторинг события завершения и корректное завершение ботов
    """
    await shutdown_event.wait()
    logger.info("Запуск процедуры завершения")
    await shutdown(imitator_bot, controller_bot)
    # Завершаем все задачи
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()


async def shutdown(imitator_bot, controller_bot):
    """
    Корректное завершение работы ботов
    """
    logger.info("Выполняется остановка ботов")

    try:
        # Останавливаем ботов
        logger.info("Остановка имитатора бота")
        await imitator_bot.stop()

        logger.info("Остановка контроллера бота")
        await controller_bot.stop()
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Ошибка при остановке ботов: {str(e)}")
        logger.error(f"Подробная информация об ошибке: {error_details}")


if __name__ == "__main__":
    logger.info("Запуск приложения")

    try:
        # Запускаем асинхронный цикл
        asyncio.run(start_bots())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено по команде пользователя")
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Критическая ошибка: {str(e)}")
        logger.error(f"Подробная информация об ошибке: {error_details}")
        sys.exit(1)
    finally:
        logger.info("Приложение завершило работу")