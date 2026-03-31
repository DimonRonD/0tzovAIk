from app.ai_service import ReviewAssistant
from app.bot import ReviewBot
from app.config import load_settings
from app.sheets import GoogleSheetsService


def validate_settings() -> None:
    settings = load_settings()
    missing_fields = []

    if not settings.telegram_bot_token:
        missing_fields.append("TELEGRAM_BOT_TOKEN")
    if not settings.openai_api_key:
        missing_fields.append("OPENAI_API_KEY")
    if not settings.responses_sheet_url:
        missing_fields.append("GOOGLE_RESPONSES_SHEET_URL")
    if not settings.knowledge_base_sheet_url:
        missing_fields.append("GOOGLE_KNOWLEDGE_BASE_SHEET_URL")
    if not settings.system_prompt_doc_url:
        missing_fields.append("SYSTEM_PROMPT_DOC_URL")
    if not settings.google_service_account_info or "client_email" not in settings.google_service_account_info:
        missing_fields.append("GOOGLE_SERVICE_ACCOUNT_JSON")

    if missing_fields:
        formatted = ", ".join(missing_fields)
        raise ValueError(f"Заполните переменные окружения в .env: {formatted}")


def main() -> None:
    validate_settings()
    settings = load_settings()

    sheets_service = GoogleSheetsService(
        service_account_info=settings.google_service_account_info,
        responses_sheet_url=settings.responses_sheet_url,
        knowledge_base_sheet_url=settings.knowledge_base_sheet_url,
    )
    assistant = ReviewAssistant(api_key=settings.openai_api_key, model=settings.openai_model)
    bot = ReviewBot(
        telegram_token=settings.telegram_bot_token,
        assistant=assistant,
        sheets_service=sheets_service,
    )
    bot.run()


if __name__ == "__main__":
    main()
