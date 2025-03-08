# Telegram Бот-имитатор и Бот-контроллер

Проект для автоматизации общения в Telegram с функциями назначения встреч через Google Calendar.

## Функциональность

### Бот-имитатор:
- Автоматически отвечает на сообщения от имени вашего Telegram аккаунта
- Поддерживает работу с API OpenAI и Sber GigaChat для генерации ответов
- Планирует встречи в Google Calendar и создает видеоконференции Google Meet
- Сохраняет историю диалогов

### Бот-контроллер:
- Управление ботом-имитатором через отдельного Telegram бота
- Включение/выключение автоматического режима в чатах
- Просмотр активных диалогов
- Переключение между API для генерации ответов

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/username/telegram-imitator-bot.git
cd telegram-imitator-bot
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Создайте файл `.env` на основе `.env.example` и заполните его своими данными.

4. Получите учетные данные для Telegram API:
   - Зарегистрируйтесь на https://my.telegram.org/
   - Создайте новое приложение
   - Скопируйте API ID и API Hash в файл `.env`
   
5. Для Google Calendar API:
   - Создайте проект в Google Cloud Console
   - Включите Google Calendar API
   - Создайте учетные данные OAuth 2.0
   - Скачайте JSON файл с учетными данными и сохраните его как `google_credentials.json`

## Использование

### Запуск ботов

```bash
python main.py
```

При первом запуске бота-имитатора вам потребуется авторизоваться в Telegram:
1. Введите номер телефона
2. Введите код подтверждения, отправленный в Telegram

### Команды бота-контроллера

- `/start` - Начало работы с ботом
- `/help` - Справка по командам
- `/chats` - Список активных чатов
- `/activate {chat_id}` - Активировать автоматический режим для чата
- `/deactivate {chat_id}` - Деактивировать автоматический режим для чата
- `/provider` - Показать текущий провайдер API
- `/set_provider {provider}` - Изменить провайдер API (openai/gigachat)

## Структура проекта

- `main.py` - Основной файл для запуска ботов
- `imitator.py` - Бот-имитатор Telegram
- `controller.py` - Бот-контроллер для управления ботом-имитатором
- `api_providers.py` - Модуль для работы с API генерации текста
- `calendar_api.py` - Модуль для работы с Google Calendar API
- `database.py` - Модуль для работы с базой данных SQLite
- `config.py` - Конфигурационные параметры проекта

## Зависимости

- pyrogram - Библиотека для работы с Telegram API
- openai - Библиотека для работы с OpenAI API
- google-auth, google-api-python-client - Библиотеки для работы с Google API
- python-dotenv - Библиотека для работы с переменными окружения
- sqlite3 - Библиотека для работы с SQLite (встроена в Python)
