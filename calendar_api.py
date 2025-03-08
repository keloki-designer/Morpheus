"""
Модуль для работы с Google Calendar API через сервисный аккаунт
"""
import logging
import json
import os
from datetime import datetime, timedelta
import dateutil.parser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials
import config

logger = logging.getLogger(__name__)

# Определяем необходимые разрешения для доступа к Google Calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]

import logging
import os
from datetime import datetime, timedelta
import dateutil.parser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials
import config

# Отключаем file_cache, чтобы убрать предупреждение
import googleapiclient.discovery_cache
googleapiclient.discovery_cache.DISABLED = True

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class CalendarAPI:
    def __init__(self, credentials_file=config.GOOGLE_CREDENTIALS_FILE, calendar_id=config.CALENDAR_ID):
        self.credentials_file = credentials_file
        self.calendar_id = calendar_id
        self.service = None
        self._authenticate()

    def _authenticate(self):
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"Файл учетных данных {self.credentials_file} не найден")
                return

            creds = Credentials.from_service_account_file(
                self.credentials_file, scopes=SCOPES
            )
            self.service = build("calendar", "v3", credentials=creds)
            logger.info("Аутентификация в Google Calendar API успешна")
        except Exception as e:
            logger.error(f"Ошибка при аутентификации в Google Calendar API: {str(e)}")
            self.service = None


    def create_meeting(self, summary, description, start_time, duration_minutes=60, attendee_email=None):
        """
        Создание встречи в календаре

        Args:
            summary (str): Тема встречи
            description (str): Описание встречи
            start_time (str): Время начала встречи в формате ISO или текстовом описании
            duration_minutes (int): Продолжительность встречи в минутах
            attendee_email (str, optional): Email участника встречи

        Returns:
            tuple: (success, event_id, meet_link) - успешность операции, ID события, ссылка на Google Meet
        """
        try:
            if not self.service:
                logger.error("Сервис Google Calendar не инициализирован")
                return False, None, None

            # Парсим время начала встречи
            try:
                if isinstance(start_time, str):
                    start_dt = dateutil.parser.parse(start_time)
                else:
                    start_dt = start_time
            except Exception as e:
                logger.error(f"Не удалось распознать время встречи: {str(e)}")
                return False, None, None

            # Вычисляем время окончания встречи
            end_dt = start_dt + timedelta(minutes=duration_minutes)

            # Подготавливаем данные для события
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "Europe/Moscow",  
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "Europe/Moscow",
                },
                "conferenceData": {
                    "createRequest": {
                        "requestId": f"meet-{int(datetime.now().timestamp())}",
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
            }

            # Если указан email участника, добавляем его
            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]

            # Создаем событие в календаре
            event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=1
            ).execute()

            logger.info(f"Встреча успешно создана: {event.get('id')}")

            # Получаем ссылку на встречу Google Meet
            meet_link = None
            for entry_point in event.get("conferenceData", {}).get("entryPoints", []):
                if entry_point.get("entryPointType") == "video":
                    meet_link = entry_point.get("uri")
                    break

            return True, event.get("id"), meet_link
        except HttpError as e:
            logger.error(f"Ошибка при создании встречи в Google Calendar: {str(e)}")
            return False, None, None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при создании встречи: {str(e)}")
            return False, None, None

    def cancel_meeting(self, event_id):
        """
        Отмена встречи в календаре

        Args:
            event_id (str): ID события в календаре

        Returns:
            bool: Успешность операции
        """
        try:
            if not self.service:
                logger.error("Сервис Google Calendar не инициализирован")
                return False

            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Встреча успешно отменена: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Ошибка при отмене встречи в Google Calendar: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при отмене встречи: {str(e)}")
            return False
