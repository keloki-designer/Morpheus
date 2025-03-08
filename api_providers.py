# api_providers.py
"""
Модуль, реализующий абстрактный интерфейс для работы с различными API генерации текста
"""
import logging
from abc import ABC, abstractmethod
import requests
import openai
import json
import config
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole
import os

logger = logging.getLogger(__name__)


class TextGenerationAPI(ABC):
    """
    Абстрактный класс для работы с API генерации текста
    """

    @abstractmethod
    def generate_response(self, prompt, chat_history, user_message):
        """
        Метод для генерации ответа на основе промпта, истории чата и сообщения пользователя

        Args:
            prompt (str): Шаблон промпта
            chat_history (str): История чата
            user_message (str): Сообщение пользователя

        Returns:
            str: Сгенерированный ответ
        """
        pass


class OpenAIProvider(TextGenerationAPI):
    """
    Реализация для работы с OpenAI API
    """

    def __init__(self):
        logger.info("Инициализация OpenAI API провайдера")
        openai.api_key = config.OPENAI_API_KEY
        self.model = config.OPENAI_MODEL

    def generate_response(self, prompt, chat_history, user_message):
        try:
            formatted_prompt = prompt.format(
                chat_history=chat_history,
                user_message=user_message
            )

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": formatted_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа через OpenAI: {str(e)}")
            return "Извините, произошла ошибка при генерации ответа. Попробуйте позже."


class GigaChatProvider(TextGenerationAPI):
    """
    Реализация для работы с Sber GigaChat API с использованием библиотеки gigachat
    """

    def __init__(self):
        logger.info("Инициализация GigaChat API провайдера")
        self.api_key = config.GIGACHAT_API_KEY
        self.model = config.GIGACHAT_MODEL

        # Настройка окружения для SSL-сертификатов
        if hasattr(config, 'CERT_PATH') and config.CERT_PATH:
            # Устанавливаем переменную окружения для библиотеки requests
            os.environ['REQUESTS_CA_BUNDLE'] = config.CERT_PATH
            logger.info(f"Установлена переменная REQUESTS_CA_BUNDLE: {config.CERT_PATH}")

        # Создаем экземпляр клиента GigaChat
        self.client = None
        self._init_client()

    def _init_client(self):
        """Инициализация клиента GigaChat"""
        try:
            # Определяем, использовать ли верификацию SSL
            verify_ssl = True
            if hasattr(config, 'SSL_VERIFY') and isinstance(config.SSL_VERIFY, bool):
                verify_ssl = config.SSL_VERIFY

            # Создаем клиент с правильными параметрами
            self.client = GigaChat(
                credentials=self.api_key,
                verify_ssl_certs=verify_ssl,
                scope="GIGACHAT_API_PERS"
            )

            logger.info("Клиент GigaChat успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации клиента GigaChat: {str(e)}")
            self.client = None

    def generate_response(self, prompt, chat_history, user_message):
        """
        Генерация ответа с использованием GigaChat API
        """
        try:
            # Если клиент не инициализирован, пробуем создать его заново
            if not self.client:
                self._init_client()
                if not self.client:
                    return "Извините, сервис временно недоступен. Не удалось получить доступ к API."

            formatted_prompt = prompt.format(
                chat_history=chat_history,
                user_message=user_message
            )

            # Создаем сообщения для запроса
            messages = [
                Messages(role=MessagesRole.SYSTEM, content=formatted_prompt),
                Messages(role=MessagesRole.USER, content=user_message)
            ]

            # Выполняем запрос к API
            response = self.client.chat(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа через GigaChat: {str(e)}")

            # Если ошибка связана с авторизацией, пробуем переинициализировать клиент
            if "401" in str(e) or "auth" in str(e).lower():
                logger.info("Попытка переинициализации клиента GigaChat")
                self.client = None
                self._init_client()
                if self.client:
                    try:
                        return self.generate_response(prompt, chat_history, user_message)
                    except Exception as retry_e:
                        logger.error(f"Повторная ошибка: {str(retry_e)}")

            return "Извините, произошла ошибка при генерации ответа. Попробуйте позже."


def get_api_provider():
    """
    Фабричный метод для создания экземпляра провайдера API в зависимости от настроек

    Returns:
        TextGenerationAPI: Экземпляр класса-провайдера API
    """
    provider = config.API_PROVIDER.lower()

    if provider == "openai":
        return OpenAIProvider()
    elif provider == "gigachat":
        return GigaChatProvider()
    else:
        logger.error(f"Неизвестный провайдер API: {provider}")
        raise ValueError(f"Неизвестный провайдер API: {provider}")