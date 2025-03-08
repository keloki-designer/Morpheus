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

# Исправленный фрагмент для GigaChatProvider в api_providers.py

class GigaChatProvider(TextGenerationAPI):
    """
    Реализация для работы с Sber GigaChat API
    """

    def __init__(self):
        logger.info("Инициализация GigaChat API провайдера")
        self.api_key = config.GIGACHAT_API_KEY
        self.model = config.GIGACHAT_MODEL
        self.token = None

        # Инициализация атрибута verify перед вызовом _get_token()
        self.verify = True
        # Проверяем, существует ли путь к сертификатам
        if hasattr(config, 'CERT_PATH') and config.CERT_PATH:
            self.verify = config.CERT_PATH
        elif not self.verify:
            logger.warning("Использование verify=False небезопасно! Настройте сертификаты для продакшена.")

        # Теперь вызываем метод, когда verify уже определен
        self._get_token()
    def _get_token(self):
        """Получение токена авторизации для GigaChat API"""
        try:
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "scope": "GIGACHAT_API_PERS"
            }

            response = requests.post(
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                headers=headers,
                data=data,
                verify=self.verify  # Используем настроенный verify
            )

            if response.status_code == 200:
                self.token = response.json().get("access_token")
                logger.info("Токен GigaChat успешно получен")
            else:
                logger.error(f"Ошибка получения токена GigaChat: {response.text}")
        except Exception as e:
            logger.error(f"Ошибка при получении токена GigaChat: {str(e)}")

    def generate_response(self, prompt, chat_history, user_message):
        """
        Генерация ответа с использованием GigaChat API
        """
        try:
            # Если токен не получен или истек, получаем новый
            if not self.token:
                self._get_token()
                if not self.token:
                    return "Извините, сервис временно недоступен. Не удалось получить доступ к API."

            formatted_prompt = prompt.format(
                chat_history=chat_history,
                user_message=user_message
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": formatted_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }

            response = requests.post(
                "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
                headers=headers,
                json=data,
                verify=self.verify  # Используем настроенный verify
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            elif response.status_code == 401:
                # Токен устарел, получаем новый и пробуем еще раз
                self._get_token()
                if self.token:
                    return self.generate_response(prompt, chat_history, user_message)
                else:
                    logger.error("Не удалось обновить токен GigaChat")
                    return "Извините, сервис временно недоступен. Не удалось получить доступ к API."
            else:
                logger.error(f"Ошибка при запросе к GigaChat API: {response.text}")
                return "Извините, произошла ошибка при генерации ответа. Попробуйте позже."
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа через GigaChat: {str(e)}")
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