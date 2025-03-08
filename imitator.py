# imitator.py
"""
Модуль бота-имитатора для Telegram
"""
import logging
import os
import json
import asyncio
import re
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, Exception as PyrogramException
import config
from database import Database
from api_providers import get_api_provider
from calendar_api import CalendarAPI

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("imitator.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TelegramImitator:
    """
    Класс для бота-имитатора Telegram
    """

    def __init__(self):
        """
        Инициализация бота-имитатора
        """
        self.db = Database()
        self.api_provider = get_api_provider()
        self.calendar_api = CalendarAPI()

        # Создаем директории для хранения истории чатов, если их нет
        os.makedirs(config.CHAT_HISTORY_PATH, exist_ok=True)
        os.makedirs(config.SESSIONS_PATH, exist_ok=True)

        # Инициализация клиента Telegram
        session_path = os.path.join(config.SESSIONS_PATH, config.SESSION_NAME)
        self.client = Client(
            session_path,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE_NUMBER
        )

        # Регистрация обработчика сообщений
        @self.client.on_message(filters.private & ~filters.me)
        async def message_handler(client, message):
            await self._handle_message(client, message)

    async def start(self):
        """
        Запуск бота-имитатора
        """
        try:
            await self.client.start()
            logger.info("Бот-имитатор запущен")

            # Бесконечный цикл для поддержания работы бота
            await asyncio.sleep(86400)  # 24 часа
        except Exception as e:
            logger.error(f"Ошибка при запуске бота-имитатора: {str(e)}")

    async def stop(self):
        """
        Остановка бота-имитатора
        """
        try:
            await self.client.stop()
            logger.info("Бот-имитатор остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота-имитатора: {str(e)}")

    async def _handle_message(self, client, message):
        """
        Обработка входящего сообщения

        Args:
            client: Клиент Telegram
            message: Объект сообщения
        """
        try:
            chat_id = str(message.chat.id)
            username = message.from_user.username or message.from_user.first_name

            # Проверяем, нужно ли автоматически отвечать в этом чате
            if not self.db.is_chat_active(chat_id):
                logger.info(f"Чат {chat_id} не активен для автоматических ответов")
                return

            # Обновляем время последнего сообщения
            self.db.update_last_message_time(chat_id)

            # Получаем сообщение пользователя
            user_message = message.text or message.caption or ""

            # Проверяем запрос на расписание встречи
            meeting_info = self._extract_meeting_info(user_message)
            if meeting_info:
                await self._schedule_meeting(client, message, meeting_info, username)
                return

            # Загружаем историю чата
            chat_history = self._load_chat_history(chat_id)

            # Обновляем API провайдера по настройкам из БД
            provider_name = self.db.get_api_provider()
            if provider_name.lower() != config.API_PROVIDER.lower():
                self.api_provider = get_api_provider()

            # Генерируем автоматический ответ
            response = self.api_provider.generate_response(
                config.IMITATOR_PROMPT,
                chat_history,
                user_message
            )

            # Добавляем сообщения в историю чата
            self._save_chat_message(chat_id, "user", user_message)
            self._save_chat_message(chat_id, "assistant", response)

            # Отправляем ответ
            await self._send_response(client, message, response)

        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {str(e)}")

    def _extract_meeting_info(self, message):
        """
        Извлечение информации о встрече из сообщения пользователя

        Args:
            message (str): Сообщение пользователя

        Returns:
            dict or None: Информация о встрече или None, если не найдена
        """
        try:
            if not message:
                return None

            # Простые регулярные выражения для поиска даты и времени
            # В реальном проекте стоит использовать более сложные алгоритмы или NLP
            date_patterns = [
                r"(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?",  # DD/MM/YYYY или DD/MM
                r"(?:завтра|сегодня|послезавтра)",
                r"(\d{1,2})(?:\s+)(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)"
            ]

            time_patterns = [
                r"(\d{1,2}):(\d{2})",  # HH:MM
                r"в\s+(\d{1,2})(?:\s*)(часов|час)",  # в 15 часов
                r"(\d{1,2})(?:\s*)(утра|вечера|дня)"  # 3 часа дня
            ]

            # Проверяем наличие упоминания о встрече
            meeting_keywords = ["встреча", "встретиться", "созвон", "консультация", "консультацию"]
            has_meeting_request = any(keyword in message.lower() for keyword in meeting_keywords)

            if not has_meeting_request:
                return None

            # Ищем дату и время в сообщении
            found_date = None
            for pattern in date_patterns:
                matches = re.search(pattern, message.lower())
                if matches:
                    found_date = matches.group(0)
                    break

            found_time = None
            for pattern in time_patterns:
                matches = re.search(pattern, message.lower())
                if matches:
                    found_time = matches.group(0)
                    break

            if found_date or found_time:
                return {
                    "date": found_date,
                    "time": found_time,
                    "raw_message": message
                }

            return None
        except Exception as e:
            logger.error(f"Ошибка при извлечении информации о встрече: {str(e)}")
            return None

    async def _schedule_meeting(self, client, message, meeting_info, username):
        """
        Планирование встречи в календаре и отправка подтверждения

        Args:
            client: Клиент Telegram
            message: Объект сообщения
            meeting_info (dict): Информация о встрече
            username (str): Имя пользователя
        """
        try:
            chat_id = str(message.chat.id)

            # Подготавливаем информацию для создания встречи
            # В реальном проекте здесь должна быть более сложная логика обработки даты и времени
            now = datetime.now()

            # Простая логика для определения времени встречи (для примера)
            # В реальном проекте стоит использовать библиотеки для разбора времени
            meeting_time = now.replace(hour=now.hour + 1, minute=0)

            # Создаем встречу в календаре
            success, event_id, meet_link = self.calendar_api.create_meeting(
                summary=f"Консультация с {username}",
                description=f"Автоматически запланированная встреча по запросу пользователя: {meeting_info['raw_message']}",
                start_time=meeting_time,
                duration_minutes=60
            )

            if success and event_id and meet_link:
                # Сохраняем информацию о встрече в БД
                self.db.add_scheduled_meeting(
                    chat_id=chat_id,
                    username=username,
                    meeting_time=meeting_time.isoformat(),
                    calendar_event_id=event_id
                )

                # Отправляем подтверждение пользователю
                meeting_date = meeting_time.strftime("%d.%m.%Y")
                meeting_time_str = meeting_time.strftime("%H:%M")

                response = (
                    f"Отлично! Я запланировал(а) для вас встречу на {meeting_date} в {meeting_time_str}.\n\n"
                    f"Ссылка для подключения: {meet_link}\n\n"
                    f"Пожалуйста, добавьте эту встречу в свой календарь. Буду ждать вас в указанное время!"
                )

                # Сохраняем сообщения в историю чата
                self._save_chat_message(chat_id, "user", meeting_info['raw_message'])
                self._save_chat_message(chat_id, "assistant", response)

                # Отправляем ответ
                await self._send_response(client, message, response)
            else:
                # Отправляем сообщение об ошибке
                response = (
                    "К сожалению, не удалось запланировать встречу. "
                    "Возможно, вы могли бы уточнить желаемое время и дату? "
                    "Или мы можем попробовать другой способ связи."
                )

                # Сохраняем сообщения в историю чата
                self._save_chat_message(chat_id, "user", meeting_info['raw_message'])
                self._save_chat_message(chat_id, "assistant", response)

                # Отправляем ответ
                await self._send_response(client, message, response)
        except Exception as e:
            logger.error(f"Ошибка при планировании встречи: {str(e)}")
            await message.reply("Произошла ошибка при планировании встречи. Пожалуйста, попробуйте позже.")

    async def _send_response(self, client, message, response):
        """
        Отправка ответа пользователю

        Args:
            client: Клиент Telegram
            message: Объект сообщения
            response (str): Текст ответа
        """
        try:
            # Имитируем печатание для более естественного общения
            await client.send_chat_action(message.chat.id, "typing")

            # Добавляем небольшую задержку для реалистичности
            typing_speed = min(len(response) * 0.05, 5)  # Максимум 5 секунд
            await asyncio.sleep(typing_speed)

            # Отправляем ответ
            await message.reply(response)
            logger.info(f"Отправлен ответ пользователю {message.from_user.id}")
        except FloodWait as e:
            # Обработка ограничения на частоту сообщений
            logger.warning(f"FloodWait: Ожидание {e.x} секунд перед отправкой сообщения")
            await asyncio.sleep(e.x)
            await message.reply(response)
        except PyrogramException as e:
            logger.error(f"Ошибка Pyrogram при отправке ответа: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа: {str(e)}")

    def _load_chat_history(self, chat_id):
        """
        Загрузка истории чата

        Args:
            chat_id (str): ID чата

        Returns:
            str: История чата в формате для промпта
        """
        try:
            history_file = os.path.join(config.CHAT_HISTORY_PATH, f"{chat_id}.json")

            if not os.path.exists(history_file):
                return ""

            with open(history_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)

            # Форматируем историю для промпта, ограничивая длину
            history = ""
            messages = messages[-10:]  # Ограничиваем количество сообщений для истории

            for msg in messages:
                role = "Пользователь" if msg["role"] == "user" else "Ассистент"
                history += f"{role}: {msg['content']}\n\n"

            # Ограничиваем общую длину истории
            if len(history) > config.MAX_HISTORY_LENGTH:
                history = history[-config.MAX_HISTORY_LENGTH:]
                # Находим первое начало сообщения пользователя
                pos = history.find("Пользователь:")
                if pos > 0:
                    history = history[pos:]

            return history
        except Exception as e:
            logger.error(f"Ошибка при загрузке истории чата: {str(e)}")
            return ""

    def _save_chat_message(self, chat_id, role, content):
        """
        Сохранение сообщения в историю чата

        Args:
            chat_id (str): ID чата
            role (str): Роль отправителя (user/assistant)
            content (str): Содержимое сообщения
        """
        try:
            history_file = os.path.join(config.CHAT_HISTORY_PATH, f"{chat_id}.json")

            # Загружаем существующую историю или создаем новую
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            else:
                messages = []

            # Добавляем новое сообщение
            messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })

            # Сохраняем обновленную историю
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении сообщения: {str(e)}")