import json
import os
import time
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from telethon_bot import TelethonBot
from states import TelethonAuth
from config import logger, AUTH_DATA_FILE


# Предопределенные константные строки для часто используемых ответов
HELP_TEXT = """Доступные команды:
/start - начать работу с ботом
/help - показать это сообщение
/auth - начать процесс авторизации Telethon бота
/status - проверить статус авторизации Telethon бота
/reset_auth - удалить сохраненные данные авторизации
/restart - перезапустить бота"""

START_TEXT = "Привет! Я бот-контроллер. Используйте /help для получения списка команд."
UNKNOWN_COMMAND_TEXT = "Неизвестная команда. Используйте /help для получения списка команд."


class AiogramBot:
    def __init__(self, token):
        logger.info("Инициализация aiogram бота")
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.telethon_bot = None
        self.admin_id = None  # ID администратора для авторизации

        # Кэширование статуса авторизации
        self._auth_status = None
        self._auth_status_time = 0
        self._auth_status_cache_time = 60  # Время кэширования в секундах

        # Кэширование данных авторизации
        self._auth_data_cache = None

        # Регистрация обработчиков
        self.register_handlers()




    def register_handlers(self):
        logger.info("Регистрация обработчиков aiogram бота")

        @self.dp.message(Command("start"))
        async def start_command(message: types.Message):
            logger.debug(f"Получена команда /start от пользователя {message.from_user.id}")
            await message.reply(START_TEXT)

        @self.dp.message(Command("help"))
        async def help_command(message: types.Message):
            logger.debug(f"Получена команда /help от пользователя {message.from_user.id}")
            await message.reply(HELP_TEXT)

        @self.dp.message(Command("restart"))
        async def restart_command(message: types.Message):
            logger.info(f"Получена команда /restart от пользователя {message.from_user.id}")
            await message.reply("Перезапуск бота...")

            # Сохраняем ID администратора в отдельной задаче
            if not self.admin_id and message.from_user.id:
                self.admin_id = message.from_user.id
                asyncio.create_task(self.save_admin_id(self.admin_id))

            # Завершаем все соединения
            await self.stop()

            # Перезапускаем скрипт
            logger.info("Выполняем перезапуск скрипта")
            import sys
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)

        @self.dp.message(Command("auth"))
        async def auth_command(message: types.Message, state: FSMContext):
            logger.info(f"Получена команда /auth от пользователя {message.from_user.id}")

            # Быстрый ответ пользователю
            processing_msg = await message.reply("Обрабатываю запрос...")

            # Запоминаем ID администратора
            self.admin_id = message.from_user.id
            asyncio.create_task(self.save_admin_id(self.admin_id))

            # Проверяем наличие сохраненных данных
            if await self.try_auto_auth(message):
                logger.info("Выполнена автоматическая авторизация")
                return

            await processing_msg.delete()
            await message.reply("Начинаем процесс авторизации Telethon бота.")
            await message.reply("Пожалуйста, введите API ID (получите на my.telegram.org):")
            await state.set_state(TelethonAuth.waiting_for_api_id)

        @self.dp.message(Command("reset_auth"))
        async def reset_auth_command(message: types.Message):
            logger.info(f"Получена команда /reset_auth от пользователя {message.from_user.id}")

            # Быстрый ответ пользователю
            processing_msg = await message.reply("Обрабатываю запрос...")

            # Сбрасываем кэш
            self._auth_data_cache = None
            self._auth_status = None

            # Выполняем операции с файлами в отдельной задаче
            async def reset_auth_files():
                if os.path.exists(AUTH_DATA_FILE):
                    os.remove(AUTH_DATA_FILE)

                    # Отключаем клиент, если он был подключен
                    if self.telethon_bot and self.telethon_bot.is_connected():
                        await self.telethon_bot.disconnect()
                        self.telethon_bot = None

                    # Удаляем файл сессии, если он существует
                    from config import TELETHON_SESSION_FILENAME
                    session_file = f"{TELETHON_SESSION_FILENAME}.session"
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        await message.reply(f"Файл сессии {session_file} также удален.")

                    await processing_msg.delete()
                    await message.reply("Данные авторизации удалены. Используйте /auth для новой авторизации.")
                else:
                    await processing_msg.delete()
                    await message.reply("Сохраненных данных авторизации не найдено.")

            asyncio.create_task(reset_auth_files())

        @self.dp.message(Command("status"))
        async def status_command(message: types.Message):
            logger.debug(f"Получена команда /status от пользователя {message.from_user.id}")

            # Быстрый ответ пользователю
            processing_msg = await message.reply("Проверяю статус...")

            if self.telethon_bot is None:
                await processing_msg.delete()
                await message.reply("Telethon бот не инициализирован. Используйте /auth для авторизации.")
            else:
                # Используем кэшированный статус авторизации, если он актуален
                current_time = time.time()
                if self._auth_status is not None and current_time - self._auth_status_time < self._auth_status_cache_time:
                    await processing_msg.delete()
                    await message.reply(self._auth_status)
                    return

                # Проверяем статус подключения и авторизации
                if not self.telethon_bot.is_connected():
                    status_text = "Telethon бот не подключен к серверам Telegram."
                elif not await self.telethon_bot.is_authorized():
                    status_text = "Telethon бот подключен, но не авторизован."
                else:
                    try:
                        me = await self.telethon_bot.get_me()
                        status_text = f"Telethon бот авторизован как {me.first_name} (@{me.username})."
                    except Exception as e:
                        logger.error(f"Ошибка при получении информации о пользователе: {e}")
                        status_text = "Telethon бот авторизован, но не удалось получить информацию о пользователе."

                # Обновляем кэш
                self._auth_status = status_text
                self._auth_status_time = current_time

                await processing_msg.delete()
                await message.reply(status_text)

        @self.dp.message(TelethonAuth.waiting_for_api_id)
        async def process_api_id(message: types.Message, state: FSMContext):
            logger.debug(f"Получен API ID от пользователя {message.from_user.id}")

            # Проверяем, является ли введенное значение числом
            try:
                api_id = int(message.text)
                await state.update_data(api_id=api_id)
                await message.reply("Отлично! Теперь введите API Hash:")
                await state.set_state(TelethonAuth.waiting_for_api_hash)
            except ValueError:
                await message.reply("API ID должен быть числом. Пожалуйста, попробуйте снова:")

        @self.dp.message(TelethonAuth.waiting_for_api_hash)
        async def process_api_hash(message: types.Message, state: FSMContext):
            logger.debug(f"Получен API Hash от пользователя {message.from_user.id}")

            await state.update_data(api_hash=message.text)
            await message.reply("Теперь введите номер телефона в международном формате (например, +71234567890):")
            await state.set_state(TelethonAuth.waiting_for_phone)

        @self.dp.message(TelethonAuth.waiting_for_phone)
        async def process_phone(message: types.Message, state: FSMContext):
            logger.debug(f"Получен номер телефона от пользователя {message.from_user.id}")

            processing_msg = await message.reply("Обрабатываю запрос...")

            phone = message.text.strip()
            await state.update_data(phone=phone)

            # Получаем сохраненные данные
            user_data = await state.get_data()
            api_id = user_data['api_id']
            api_hash = user_data['api_hash']

            # Инициализируем Telethon клиент
            from config import TELETHON_SESSION_FILENAME
            self.telethon_bot = TelethonBot(TELETHON_SESSION_FILENAME, api_id, api_hash)

            try:
                await self.telethon_bot.connect()
                logger.info("Telethon бот подключен к серверам Telegram")

                # Проверяем, можем ли мы авторизоваться с существующей сессией
                if await self.telethon_bot.is_authorized():
                    logger.info("Telethon бот уже авторизован через существующую сессию")

                    # Запускаем асинхронную задачу для сохранения данных
                    asyncio.create_task(self.save_auth_data(api_id, api_hash, phone))

                    # Регистрируем обработчики для Telethon бота
                    asyncio.create_task(self.telethon_bot.register_handlers())

                    await processing_msg.delete()
                    await message.reply("Вы уже авторизованы через существующую сессию! Telethon бот запущен.")
                    await state.clear()
                    return

                # Отправляем запрос на авторизацию
                await self.telethon_bot.send_code_request(phone)
                await processing_msg.delete()
                await message.reply("Код подтверждения отправлен на ваш номер телефона. Пожалуйста, введите его:")
                await state.set_state(TelethonAuth.waiting_for_code)
            except Exception as e:
                logger.error(f"Ошибка при подключении к Telegram: {e}")
                await processing_msg.delete()
                await message.reply(
                    f"Произошла ошибка: {e}\nПопробуйте начать процесс авторизации заново с командой /auth")
                await state.clear()

        @self.dp.message(TelethonAuth.waiting_for_code)
        async def process_code(message: types.Message, state: FSMContext):
            logger.debug(f"Получен код подтверждения от пользователя {message.from_user.id}")

            processing_msg = await message.reply("Выполняю авторизацию...")

            code = message.text.strip()
            user_data = await state.get_data()
            phone = user_data['phone']
            api_id = user_data['api_id']
            api_hash = user_data['api_hash']

            try:
                await self.telethon_bot.sign_in(phone, code)
                logger.info("Telethon бот успешно авторизован")

                # Сохраняем данные авторизации в отдельной задаче
                asyncio.create_task(self.save_auth_data(api_id, api_hash, phone))

                # Регистрируем обработчики для Telethon бота
                asyncio.create_task(self.telethon_bot.register_handlers())

                await processing_msg.delete()
                await message.reply("Авторизация успешно завершена! Telethon бот запущен.")
                await state.clear()
            except Exception as e:
                logger.error(f"Ошибка при авторизации: {e}")
                await processing_msg.delete()
                await message.reply(
                    f"Произошла ошибка при авторизации: {e}\nПопробуйте начать процесс авторизации заново с командой /auth")
                await state.clear()

        @self.dp.message(TelethonAuth.waiting_for_2fa)
        async def process_2fa(message: types.Message, state: FSMContext):
            logger.debug(f"Получен пароль двухфакторной аутентификации от пользователя {message.from_user.id}")

            processing_msg = await message.reply("Выполняю авторизацию...")

            password = message.text.strip()
            user_data = await state.get_data()
            api_id = user_data['api_id']
            api_hash = user_data['api_hash']
            phone = user_data['phone']

            try:
                await self.telethon_bot.sign_in(password=password)
                logger.info("Telethon бот успешно авторизован через 2FA")

                # Сохраняем данные авторизации в отдельной задаче
                asyncio.create_task(self.save_auth_data(api_id, api_hash, phone))

                # Регистрируем обработчики для Telethon бота в отдельной задаче
                asyncio.create_task(self.telethon_bot.register_handlers())

                await processing_msg.delete()
                await message.reply("Авторизация успешно завершена! Telethon бот запущен.")
                await state.clear()
            except Exception as e:
                logger.error(f"Ошибка при авторизации через 2FA: {e}")
                await processing_msg.delete()
                await message.reply(
                    f"Произошла ошибка при авторизации: {e}\nПопробуйте начать процесс авторизации заново с командой /auth")
                await state.clear()

        @self.dp.message()
        async def echo(message: types.Message):
            if message.text.startswith('/'):
                await message.reply(UNKNOWN_COMMAND_TEXT)
                return

            logger.debug(f"Получено сообщение от пользователя {message.from_user.id}")
            await message.answer(f"Вы написали: {message.text}")

    async def save_auth_data(self, api_id, api_hash, phone):
        """Сохранение данных авторизации в файл"""
        auth_data = {
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone
        }

        # Если есть сохраненный admin_id, добавляем его в данные
        if self.admin_id:
            auth_data["admin_id"] = self.admin_id

        with open(AUTH_DATA_FILE, 'w') as f:
            json.dump(auth_data, f)

        # Обновляем кэш
        self._auth_data_cache = auth_data

        logger.info(f"Данные авторизации сохранены в файл {AUTH_DATA_FILE}")

    async def save_admin_id(self, admin_id):
        """Сохранение ID администратора"""
        # Используем кэшированные данные, если они есть
        if self._auth_data_cache is not None:
            auth_data = self._auth_data_cache.copy()
        else:
            auth_data = {}
            if os.path.exists(AUTH_DATA_FILE):
                try:
                    with open(AUTH_DATA_FILE, 'r') as f:
                        auth_data = json.load(f)
                except Exception as e:
                    logger.error(f"Ошибка при чтении файла авторизации: {e}")
                    auth_data = {}

        auth_data["admin_id"] = admin_id

        with open(AUTH_DATA_FILE, 'w') as f:
            json.dump(auth_data, f)

        # Обновляем кэш
        self._auth_data_cache = auth_data

        logger.info(f"ID администратора {admin_id} сохранен в файл {AUTH_DATA_FILE}")

    async def load_auth_data(self):
        """Загрузка данных авторизации из файла"""
        # Используем кэшированные данные, если они есть
        if self._auth_data_cache is not None:
            return self._auth_data_cache

        if not os.path.exists(AUTH_DATA_FILE):
            logger.info(f"Файл с данными авторизации {AUTH_DATA_FILE} не найден")
            return None

        try:
            with open(AUTH_DATA_FILE, 'r') as f:
                auth_data = json.load(f)
                logger.info(f"Данные авторизации успешно загружены из файла {AUTH_DATA_FILE}")

                # Восстанавливаем ID администратора, если он был сохранен
                if "admin_id" in auth_data:
                    self.admin_id = auth_data["admin_id"]
                    logger.info(f"Восстановлен ID администратора: {self.admin_id}")

                # Сохраняем в кэш
                self._auth_data_cache = auth_data
                return auth_data
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных авторизации: {e}")
            return None

    async def try_auto_auth(self, message=None):
        """Попытка автоматической авторизации с сохраненными данными"""
        auth_data = await self.load_auth_data()

        if not auth_data:
            if message:
                await message.reply("Сохраненных данных авторизации не найдено. Необходима ручная авторизация.")
            logger.info("Сохраненных данных авторизации не найдено")
            return False

        api_id = auth_data.get('api_id')
        api_hash = auth_data.get('api_hash')
        phone = auth_data.get('phone')

        if not all([api_id, api_hash, phone]):
            if message:
                await message.reply("Сохраненные данные авторизации неполные. Необходима ручная авторизация.")
            logger.info("Сохраненные данные авторизации неполные")
            return False

        if message:
            await message.reply("Найдены сохраненные данные авторизации. Попытка автоматической авторизации...")
        logger.info("Найдены сохраненные данные авторизации. Попытка автоматической авторизации...")

        # Инициализируем Telethon клиент
        from config import TELETHON_SESSION_FILENAME
        self.telethon_bot = TelethonBot(TELETHON_SESSION_FILENAME, api_id, api_hash)

        try:
            await self.telethon_bot.connect()
            logger.info("Telethon бот подключен к серверам Telegram")

            # Проверяем, авторизован ли клиент
            if await self.telethon_bot.is_authorized():
                logger.info("Telethon бот успешно авторизован с существующей сессией")

                # Регистрируем обработчики в отдельной задаче
                asyncio.create_task(self.telethon_bot.register_handlers())

                me = await self.telethon_bot.get_me()

                status_message = f"Автоматическая авторизация успешна! Telethon бот запущен как {me.first_name} (@{me.username})."
                logger.info(status_message)

                if message:
                    await message.reply(status_message)
                elif self.admin_id:
                    try:
                        await self.bot.send_message(self.admin_id, status_message)
                    except Exception as e:
                        logger.error(f"Не удалось отправить сообщение администратору: {e}")

                return True
            else:
                from config import TELETHON_SESSION_FILENAME
                session_file = f"{TELETHON_SESSION_FILENAME}.session"
                if os.path.exists(session_file):
                    logger.info(f"Файл сессии {session_file} найден, но авторизация не удалась")
                    if message:
                        await message.reply("Файл сессии найден, но для авторизации требуется ввести код.")
                        await self.telethon_bot.send_code_request(phone)
                        await message.reply(
                            "Код подтверждения отправлен на ваш номер телефона. Пожалуйста, введите его через команду /auth")
                    elif self.admin_id:
                        try:
                            await self.bot.send_message(self.admin_id,
                                                        "Файл сессии найден, но для авторизации требуется ввести код. Используйте команду /auth для ввода кода.")
                        except Exception as e:
                            logger.error(f"Не удалось отправить сообщение администратору: {e}")
                else:
                    logger.info("Файл сессии не найден, требуется полная авторизация")
                    if message:
                        await message.reply(
                            "Сохраненные данные есть, но файл сессии не найден. Необходима полная авторизация.")
                    elif self.admin_id:
                        try:
                            await self.bot.send_message(self.admin_id,
                                                        "Сохраненные данные есть, но файл сессии не найден. Используйте команду /auth для авторизации.")
                        except Exception as e:
                            logger.error(f"Не удалось отправить сообщение администратору: {e}")

                await self.telethon_bot.disconnect()
                return False
        except Exception as e:
            error_msg = f"Ошибка при автоматической авторизации: {e}"
            logger.error(error_msg)

            if message:
                await message.reply(f"{error_msg}\nНеобходима ручная авторизация.")
            elif self.admin_id:
                try:
                    await self.bot.send_message(self.admin_id,
                                                f"{error_msg}\nИспользуйте команду /auth для ручной авторизации.")
                except Exception as e2:
                    logger.error(f"Не удалось отправить сообщение администратору: {e2}")

            return False

    async def start(self):
        logger.info("Запуск aiogram бота")
        try:
            # Попытка автоматической авторизации Telethon бота при запуске
            from config import AUTO_AUTH_ON_START
            if AUTO_AUTH_ON_START:
                logger.info("Попытка автоматической авторизации при запуске")
                asyncio.create_task(self.try_auto_auth())  # Запускаем в отдельной задаче

            # Запуск aiogram бота
            await self.dp.start_polling(self.bot)
            logger.info("Aiogram бот успешно запущен")
        except Exception as e:
            logger.error(f"Ошибка при запуске aiogram бота: {e}")
            raise

    async def stop(self):
        logger.info("Остановка aiogram бота")
        if self.telethon_bot and self.telethon_bot.is_connected():
            await self.telethon_bot.disconnect()
            logger.info("Telethon бот отключен")
        await self.bot.session.close()
        logger.info("Aiogram бот остановлен")