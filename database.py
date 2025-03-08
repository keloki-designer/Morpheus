# database.py
"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
import json
import os
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для работы с базой данных
    """

    def __init__(self, db_path=config.DATABASE_PATH):
        """
        Инициализация соединения с базой данных

        Args:
            db_path (str): Путь к файлу базы данных
        """
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """
        Инициализация структуры базы данных
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Таблица для хранения активных автоматических чатов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_chats (
                chat_id TEXT PRIMARY KEY,
                username TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_message_time TEXT,
                created_at TEXT
            )
            ''')

            # Таблица для хранения настроек ботов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            ''')

            # Таблица для хранения запланированных встреч
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                username TEXT,
                meeting_time TEXT,
                calendar_event_id TEXT,
                created_at TEXT
            )
            ''')

            # Устанавливаем начальные настройки, если их нет
            cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
            ''', ('api_provider', config.API_PROVIDER))

            conn.commit()
            conn.close()
            logger.info("База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации базы данных: {str(e)}")

    def add_active_chat(self, chat_id, username):
        """
        Добавление нового активного чата

        Args:
            chat_id (str): ID чата в Telegram
            username (str): Имя пользователя

        Returns:
            bool: Успешность операции
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
            INSERT OR REPLACE INTO active_chats (chat_id, username, is_active, last_message_time, created_at) 
            VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, username, True, now, now))

            conn.commit()
            conn.close()
            logger.info(f"Добавлен активный чат: {chat_id} ({username})")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении активного чата: {str(e)}")
            return False

    def deactivate_chat(self, chat_id):
        """
        Деактивация автоматического режима в чате

        Args:
            chat_id (str): ID чата в Telegram

        Returns:
            bool: Успешность операции
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE active_chats SET is_active = 0 WHERE chat_id = ?
            ''', (chat_id,))

            conn.commit()
            conn.close()
            logger.info(f"Деактивирован чат: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при деактивации чата: {str(e)}")
            return False

    def activate_chat(self, chat_id):
        """
        Активация автоматического режима в чате

        Args:
            chat_id (str): ID чата в Telegram

        Returns:
            bool: Успешность операции
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE active_chats SET is_active = 1 WHERE chat_id = ?
            ''', (chat_id,))

            conn.commit()
            conn.close()
            logger.info(f"Активирован чат: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при активации чата: {str(e)}")
            return False

    def is_chat_active(self, chat_id):
        """
        Проверка, активен ли автоматический режим в чате

        Args:
            chat_id (str): ID чата в Telegram

        Returns:
            bool: Активен ли автоматический режим
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            SELECT is_active FROM active_chats WHERE chat_id = ?
            ''', (chat_id,))

            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке активности чата: {str(e)}")
            return False

    def get_active_chats(self):
        """
        Получение списка всех активных чатов

        Returns:
            list: Список словарей с информацией о чатах
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
            SELECT * FROM active_chats WHERE is_active = 1
            ''')

            rows = cursor.fetchall()
            chats = [dict(row) for row in rows]
            conn.close()

            return chats
        except Exception as e:
            logger.error(f"Ошибка при получении активных чатов: {str(e)}")
            return []

    def update_last_message_time(self, chat_id):
        """
        Обновление времени последнего сообщения в чате

        Args:
            chat_id (str): ID чата в Telegram

        Returns:
            bool: Успешность операции
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
            UPDATE active_chats SET last_message_time = ? WHERE chat_id = ?
            ''', (now, chat_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени последнего сообщения: {str(e)}")
            return False

    def get_api_provider(self):
        """
        Получение текущего провайдера API из настроек

        Returns:
            str: Название провайдера API
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            SELECT value FROM settings WHERE key = 'api_provider'
            ''')

            result = cursor.fetchone()
            conn.close()

            if result:
                return result[0]
            return config.API_PROVIDER
        except Exception as e:
            logger.error(f"Ошибка при получении провайдера API: {str(e)}")
            return config.API_PROVIDER

    def set_api_provider(self, provider):
        """
        Установка провайдера API в настройках

        Args:
            provider (str): Название провайдера API

        Returns:
            bool: Успешность операции
        """
        try:
            if provider.lower() not in ['openai', 'gigachat']:
                logger.error(f"Неизвестный провайдер API: {provider}")
                return False

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE settings SET value = ? WHERE key = 'api_provider'
            ''', (provider.lower(),))

            conn.commit()
            conn.close()
            logger.info(f"Установлен провайдер API: {provider}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке провайдера API: {str(e)}")
            return False

    def add_scheduled_meeting(self, chat_id, username, meeting_time, calendar_event_id):
        """
        Добавление информации о запланированной встрече

        Args:
            chat_id (str): ID чата в Telegram
            username (str): Имя пользователя
            meeting_time (str): Время встречи в ISO формате
            calendar_event_id (str): ID события в Google Calendar

        Returns:
            bool: Успешность операции
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
            INSERT INTO scheduled_meetings (chat_id, username, meeting_time, calendar_event_id, created_at) 
            VALUES (?, ?, ?, ?, ?)
            ''', (chat_id, username, meeting_time, calendar_event_id, now))

            conn.commit()
            conn.close()
            logger.info(f"Добавлена встреча для {username} в {meeting_time}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении встречи: {str(e)}")
            return False