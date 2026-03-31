# Инструкция по обновлению ассистента

1. Обновите системный промпт в Google Docs и при необходимости синхронизируйте текст в `docs/system_prompt.md` и `app/prompts.py`.
2. Добавьте или скорректируйте шаблоны в таблице базы знаний Google Sheets:
   - `id`
   - `Response_Template`
   - `Answer_Template`
3. Проверьте актуальность переменных в `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `GOOGLE_RESPONSES_SHEET_URL`
   - `GOOGLE_KNOWLEDGE_BASE_SHEET_URL`
   - `SYSTEM_PROMPT_DOC_URL`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
4. При необходимости измените модель в `OPENAI_MODEL`.
5. Установите зависимости:
   `pip install -r requirements.txt`
6. Запустите приложение:
   `python main.py`
