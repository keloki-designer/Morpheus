from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from config import logger

class TelethonBot:
    def __init__(self, session_filename, api_id, api_hash):
        self.client = TelegramClient(session_filename, api_id, api_hash)
        logger.info(f"Инициализация Telethon бота с сессией {session_filename}")

    async def connect(self):
        """Подключение к серверам Telegram"""
        await self.client.connect()
        logger.info("Telethon бот подключен к серверам Telegram")
        return self.client.is_connected()

    async def disconnect(self):
        """Отключение от серверов Telegram"""
        await self.client.disconnect()
        logger.info("Telethon бот отключен от серверов Telegram")

    def is_connected(self):
        """Проверка, подключен ли клиент к серверам Telegram"""
        return self.client.is_connected()

    async def is_authorized(self):
        """Проверка, авторизован ли клиент"""
        return await self.client.is_user_authorized()

    async def send_code_request(self, phone):
        """Отправка запроса на код подтверждения"""
        return await self.client.send_code_request(phone)

    async def sign_in(self, phone=None, code=None, password=None):
        """Авторизация в Telegram"""
        if password:
            return await self.client.sign_in(password=password)
        else:
            return await self.client.sign_in(phone, code)

    async def get_me(self):
        """Получение информации о текущем пользователе"""
        return await self.client.get_me()

    async def register_handlers(self):
        """Регистрация обработчиков событий"""
        logger.info("Регистрация обработчиков Telethon бота")

        @self.client.on(events.NewMessage(pattern='/start'))
        async def telethon_start_handler(event):
            logger.info(f"Получена команда /start в Telethon боте")
            await event.respond("Привет! Я бот на Telethon.")

        @self.client.on(events.NewMessage(pattern='/help'))
        async def telethon_help_handler(event):
            logger.info(f"Получена команда /help в Telethon боте")
            await event.respond("Доступные команды:\n/start - начать\n/help - помощь")

        @self.client.on(events.NewMessage)
        async def telethon_echo_handler(event):
            if event.text not in ['/start', '/help']:
                logger.info(f"Получено сообщение в Telethon боте: {event.text}")
                await event.respond(f"Вы написали: {event.text}")