# ИИ-ассистент для работы с отзывами клиентов

## Назначение проекта
Проект реализует Telegram-бота на Python, который:
- принимает отзывы клиентов;
- определяет тон и тему отзыва;
- ищет подходящий шаблон ответа в базе знаний Google Sheets;
- формирует ответ через OpenAI;
- отправляет ответ клиенту в Telegram;
- сохраняет отзыв и ответ в Google Sheets.

## Логика работы
1. Клиент отправляет отзыв в Telegram-бот.
2. Приложение загружает шаблоны из Google Sheets базы знаний.
3. Модель OpenAI выбирает подходящий шаблон.
4. Если шаблон найден, его `id` записывается в поле `Template`.
5. Если шаблон не найден, в поле `Template` записывается `Urgent`.
6. Модель формирует корректный ответ на русском языке.
7. Ответ отправляется пользователю в Telegram.
8. Отзыв и результат обработки сохраняются в таблицу откликов.

## Структура проекта
- `main.py` - точка входа.
- `app/config.py` - загрузка конфигурации из `.env`.
- `app/prompts.py` - системный промпт.
- `app/ai_service.py` - выбор шаблона и генерация ответа через OpenAI.
- `app/sheets.py` - чтение и запись данных в Google Sheets.
- `app/bot.py` - Telegram-бот.
- `docs/system_prompt.md` - текст системного промпта.
- `docs/update_guide.md` - инструкция по обновлению ассистента.

## Переменные окружения
В проекте используется файл `.env` со следующими переменными:

- `TELEGRAM_BOT_TOKEN` - токен Telegram-бота.
- `OPENAI_API_KEY` - ключ OpenAI.
- `GOOGLE_RESPONSES_SHEET_URL` - ссылка на таблицу с отзывами и ответами.
- `GOOGLE_KNOWLEDGE_BASE_SHEET_URL` - ссылка на таблицу базы знаний.
- `SYSTEM_PROMPT_DOC_URL` - ссылка на Google Docs с системным промптом.
- `OPENAI_MODEL` - используемая модель OpenAI.
- `GOOGLE_SERVICE_ACCOUNT_JSON` - JSON сервисного аккаунта Google одной строкой.

## Форматы таблиц

### Таблица откликов
Используются столбцы:
- `id`
- `Response_date`
- `Response`
- `Tone`
- `Topic`
- `Answer_date`
- `Answer`
- `Template`

Ссылка: [Google Sheets - Responses](https://docs.google.com/spreadsheets/d/1tYdiPfQX0s0CL3kGSk3syi-xO1d_g0WvZP9oc8VJq28/edit?usp=sharing)

### База знаний
Используются столбцы:
- `id`
- `Response_Template`
- `Answer_Template`

Ссылка: [Google Sheets - Knowledge Base](https://docs.google.com/spreadsheets/d/1rG68bCXDCQf1wNdm3lkMMikqzNS8y8ETK5t7fqUqwBQ/edit?usp=sharing)

## Системный промпт
Исходный документ промпта:
[Google Docs - System Prompt](https://docs.google.com/document/d/102I_M2LmMFYSeROoICA-Ilax2rzH6CGmJevmb8TTK7Y/edit?usp=sharing)

Локальная версия промпта находится в `docs/system_prompt.md`, а рабочая строка для приложения - в `app/prompts.py`.

## Настройка
1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:
   `pip install -r requirements.txt`
3. Заполните файл `.env`.
4. Убедитесь, что сервисный аккаунт Google имеет доступ на чтение и запись к таблице откликов и доступ на чтение к базе знаний.
5. Запустите приложение:
   `python main.py`

## Запуск через Docker
1. Заполните файл `.env`.
2. Соберите и запустите контейнер:
   `docker compose up --build -d`
3. Для остановки используйте:
   `docker compose down`

## Особенности реализации
- Бот работает через long polling.
- Для выбора шаблона и генерации ответа используется OpenAI.
- Если шаблон не найден, система маркирует запись как `Urgent`.
- Ответы формируются на русском языке в вежливом и корректном стиле.
- Данные сохраняются в Google Sheets сразу после обработки отзыва.

## Ограничения и важные замечания
- Для записи в Google Sheets требуется сервисный аккаунт Google.
- Ссылка на Google Docs с промптом хранится в `.env`, но приложение использует локальную версию промпта из кода.
- Если потребуется, можно доработать проект так, чтобы промпт автоматически подтягивался из опубликованного документа.

## Обновление ассистента
Подробная инструкция находится в `docs/update_guide.md`.
