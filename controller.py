# controller.py
"""
Модуль бота-контроллера для управления ботом-имитатором
"""
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import Database

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8',
    handlers=[
        logging.FileHandler("controller.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TelegramController:
    """
    Класс для бота-контроллера Telegram
    """

    def __init__(self):
        """
        Инициализация бота-контроллера
        """
        self.db = Database()

        # Инициализация бота и диспетчера Telegram
        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher()

        # Регистрация обработчиков команд
        self._register_handlers()

    def _register_handlers(self):
        """
        Регистрация обработчиков команд и сообщений
        """

        # Команда /start
        @self.dp.message(Command("start"))
        async def start_command(message: types.Message):
            await message.reply(
                "Привет! Я бот-контроллер для управления ботом-имитатором.\n\n"
                "Доступные команды:\n"
                "/chats - Список активных чатов\n"
                "/activate {chat_id} - Активировать автоматический режим для чата\n"
                "/deactivate {chat_id} - Деактивировать автоматический режим для чата\n"
                "/provider - Текущий провайдер API\n"
                "/set_provider {provider} - Изменить провайдер API (openai/gigachat)\n"
                "/help - Справка по командам"
            )

        # Команда /help
        @self.dp.message(Command("help"))
        async def help_command(message: types.Message):
            await message.reply(
                "Справка по командам:\n\n"
                "/chats - Показать список всех активных чатов\n"
                "/activate {chat_id} - Активировать автоматический режим для чата\n"
                "/deactivate {chat_id} - Деактивировать автоматический режим для чата\n"
                "/provider - Показать текущий провайдер API (openai/gigachat)\n"
                "/set_provider {provider} - Изменить провайдер API (openai/gigachat)\n"
                "/help - Показать эту справку"
            )

        # Команда /chats - показать активные чаты
        @self.dp.message(Command("chats"))
        async def chats_command(message: types.Message):
            chats = self.db.get_active_chats()

            if not chats:
                await message.reply("Активных чатов не найдено.")
                return

            text = "Список активных чатов:\n\n"

            for chat in chats:
                chat_id = chat['chat_id']
                username = chat['username']
                last_time = chat['last_message_time']

                # Форматируем информацию о чате
                chat_info = f"ID: {chat_id}\nПользователь: {username}\nПоследнее сообщение: {last_time}\n"

                # Добавляем кнопки управления
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Деактивировать", callback_data=f"deactivate_{chat_id}"),
                    ]
                ])

                # Отправляем сообщение с кнопками для каждого чата отдельно
                await message.answer(chat_info, reply_markup=keyboard)

        # Команда /activate - активировать автоответчик для чата
        @self.dp.message(Command("activate"))
        async def activate_command(message: types.Message):
            # Получаем chat_id из аргументов команды
            command_parts = message.text.split()

            if len(command_parts) != 2:
                await message.reply(
                    "Пожалуйста, укажите ID чата.\n"
                    "Пример: /activate 12345678"
                )
                return

            chat_id = command_parts[1]

            # Активируем чат
            if self.db.activate_chat(chat_id):
                await message.reply(f"Автоматический режим активирован для чата {chat_id}")
            else:
                await message.reply(
                    f"Не удалось активировать автоматический режим для чата {chat_id}.\n"
                    "Возможно, этот чат не существует в базе данных."
                )

        # Команда /deactivate - деактивировать автоответчик для чата
        @self.dp.message(Command("deactivate"))
        async def deactivate_command(message: types.Message):
            # Получаем chat_id из аргументов команды
            command_parts = message.text.split()

            if len(command_parts) != 2:
                await message.reply(
                    "Пожалуйста, укажите ID чата.\n"
                    "Пример: /deactivate 12345678"
                )
                return

            chat_id = command_parts[1]

            # Деактивируем чат
            if self.db.deactivate_chat(chat_id):
                await message.reply(f"Автоматический режим деактивирован для чата {chat_id}")
            else:
                await message.reply(
                    f"Не удалось деактивировать автоматический режим для чата {chat_id}.\n"
                    "Возможно, этот чат не существует в базе данных."
                )

        # Команда /provider - показать текущий провайдер API
        @self.dp.message(Command("provider"))
        async def provider_command(message: types.Message):
            provider = self.db.get_api_provider()
            await message.reply(f"Текущий провайдер API: {provider}")

        # Команда /set_provider - изменить провайдер API
        @self.dp.message(Command("set_provider"))
        async def set_provider_command(message: types.Message):
            # Получаем название провайдера из аргументов команды
            command_parts = message.text.split()

            if len(command_parts) != 2:
                await message.reply(
                    "Пожалуйста, укажите название провайдера (openai/gigachat).\n"
                    "Пример: /set_provider openai"
                )
                return

            provider = command_parts[1].lower()

            if provider not in ["openai", "gigachat"]:
                await message.reply(
                    "Некорректное название провайдера. Поддерживаемые провайдеры: openai, gigachat"
                )
                return

            # Устанавливаем провайдер
            if self.db.set_api_provider(provider):
                await message.reply(f"Провайдер API изменен на: {provider}")
            else:
                await message.reply("Не удалось изменить провайдер API. Пожалуйста, попробуйте позже.")

        # Обработчик callback-запросов (для кнопок)
        @self.dp.callback_query()
        async def handle_callback(callback: types.CallbackQuery):
            data = callback.data

            # Обработка кнопки деактивации чата
            if data.startswith("deactivate_"):
                chat_id = data.split("_")[1]

                if self.db.deactivate_chat(chat_id):
                    await callback.answer("Чат деактивирован")
                    # Обновляем текст сообщения
                    await callback.message.edit_text(
                        callback.message.text + "\n\n✅ Автоматический режим деактивирован"
                    )
                else:
                    await callback.answer("Не удалось деактивировать чат", show_alert=True)

    async def start(self):
        """
        Запуск бота-контроллера
        """
        try:
            logger.info("Запуск бота-контроллера...")

            # Запуск поллинга
            await self.dp.start_polling(self.bot)

            logger.info("Бот-контроллер запущен")
        except Exception as e:
            logger.error(f"Ошибка при запуске бота-контроллера: {str(e)}")

    async def stop(self):
        """
        Остановка бота-контроллера
        """
        try:
            # Закрытие сессии бота
            await self.bot.session.close()
            logger.info("Бот-контроллер остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота-контроллера: {str(e)}")