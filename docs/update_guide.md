# Инструкция по обновлению ассистента

1. Обновите системный промпт в Google Docs. Это основной источник промпта для работающего бота.
2. При необходимости обновите `docs/system_prompt.md`, если хотите сохранить локальную документированную копию промпта.
3. Добавьте или скорректируйте шаблоны в таблице базы знаний Google Sheets:
   - `id`
   - `Response_Template`
   - `Answer_Template`
4. Проверьте актуальность переменных в `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `GOOGLE_RESPONSES_SHEET_URL`
   - `GOOGLE_KNOWLEDGE_BASE_SHEET_URL`
   - `SYSTEM_PROMPT_DOC_URL`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
5. При необходимости измените модель в `OPENAI_MODEL`.
6. Установите зависимости:
   `pip install -r requirements.txt`
7. Запустите приложение:
   `python main.py`
