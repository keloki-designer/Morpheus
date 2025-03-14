import asyncio
import time
import sys
import os
from aiogram_bot import AiogramBot
from config import logger, AIOGRAM_TOKEN, MAX_RESTART_ATTEMPTS, RESTART_DELAY

# Функция для перезапуска программы при ошибке
async def run_with_restart():
    restart_count = 0

    while restart_count < MAX_RESTART_ATTEMPTS:
        try:
            # Создание и запуск бота
            bot = AiogramBot(AIOGRAM_TOKEN)
            await bot.start()

            # Держим программу запущенной, пока не будет нажата Ctrl+C
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Получено прерывание от пользователя")
            if 'bot' in locals():
                await bot.stop()
            break

        except Exception as e:
            logger.error(f"Произошла критическая ошибка: {e}")
            if 'bot' in locals():
                await bot.stop()

            restart_count += 1

            if restart_count < MAX_RESTART_ATTEMPTS:
                logger.info(
                    f"Попытка перезапуска ({restart_count}/{MAX_RESTART_ATTEMPTS}) через {RESTART_DELAY} секунд...")
                time.sleep(RESTART_DELAY)
            else:
                logger.error(
                    f"Достигнуто максимальное количество попыток перезапуска ({MAX_RESTART_ATTEMPTS}). Программа завершена.")
                break

    logger.info("Программа завершена")

# Главная функция
async def main():
    logger.info("Запуск main функции")
    await run_with_restart()

if __name__ == "__main__":
    asyncio.run(main())