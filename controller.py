# controller.py
"""
Модуль бота-контроллера для управления ботом-имитатором
"""
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

        # Инициализация клиента Telegram
        self.bot = Client(
            "controller_bot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN
        )

        # Регистрация обработчиков команд
        self._register_handlers()

    def _register_handlers(self):
        """
        Регистрация обработчиков команд и сообщений
        """

        # Команда /start
        @self.bot.on_message(filters.command("start") & filters.private)
        async def start_command(client, message):
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
        @self.bot.on_message(filters.command("help") & filters.private)
        async def help_command(client, message):
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
        @self.bot.on_message(filters.command("chats") & filters.private)
        async def chats_command(client, message):
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
                text += f"ID: {chat_id}\nПользователь: {username}\nПоследнее сообщение: {last_time}\n"

                # Добавляем кнопки управления
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Деактивировать", callback_data=f"deactivate_{chat_id}"),
                    ]
                ])

                # Отправляем сообщение с кнопками
                await message.reply(text, reply_markup=keyboard)
                text = ""  # Сбрасываем текст для следующего чата

            # Если есть остаток текста, отправляем его
            if text:
                await message.reply(text)

        # Команда /activate - активировать автоответчик для чата
        @self.bot.on_message(filters.command("activate") & filters.private)
        async def activate_command(client, message):
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
        @self.bot.on_message(filters.command("deactivate") & filters.private)
        async def deactivate_command(client, message):
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
        @self.bot.on_message(filters.command("provider") & filters.private)
        async def provider_command(client, message):
            provider = self.db.get_api_provider()
            await message.reply(f"Текущий провайдер API: {provider}")

        # Команда /set_provider - изменить провайдер API
        @self.bot.on_message(filters.command("set_provider") & filters.private)
        async def set_provider_command(client, message):
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
        @self.bot.on_callback_query()
        async def handle_callback(client, callback_query):
            data = callback_query.data

            # Обработка кнопки деактивации чата
            if data.startswith("deactivate_"):
                chat_id = data.split("_")[1]

                if self.db.deactivate_chat(chat_id):
                    await callback_query.answer("Чат деактивирован")
                    await callback_query.message.edit_text(
                        callback_query.message.text + "\n\n✅ Автоматический режим деактивирован"
                    )
                else:
                    await callback_query.answer("Не удалось деактивировать чат", show_alert=True)

    async def start(self):
        """
        Запуск бота-контроллера
        """
        try:
            await self.bot.start()
            logger.info("Бот-контроллер запущен")

            # Бесконечный цикл для поддержания работы бота
            await asyncio.sleep(86400)  # 24 часа
        except Exception as e:
            logger.error(f"Ошибка при запуске бота-контроллера: {str(e)}")

    async def stop(self):
        """
        Остановка бота-контроллера
        """
        try:
            await self.bot.stop()
            logger.info("Бот-контроллер остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота-контроллера: {str(e)}")