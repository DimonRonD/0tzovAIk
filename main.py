import argparse
import logging

from colorama import Fore, Style, init

from app.ai_service import ReviewAssistant
from app.bot import ReviewBot
from app.config import load_settings
from app.prompts import load_system_prompt
from app.sheets import GoogleSheetsService


logger = logging.getLogger(__name__)


class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Fore.LIGHTBLACK_EX,
        logging.INFO: Fore.WHITE,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        formatted_message = super().format(record)
        return f"{color}{formatted_message}{Style.RESET_ALL}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ИИ-ассистент для работы с отзывами клиентов")
    parser.add_argument("--logs", action="store_true", help="Включить логирование уровней INFO, WARNING, ERROR")
    parser.add_argument("--debug", action="store_true", help="Включить логирование всех уровней, включая DEBUG")
    return parser.parse_args()


def configure_logging(log_level: int) -> None:
    init(autoreset=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    root_logger.addHandler(console_handler)


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
    args = parse_args()
    log_level = logging.DEBUG if args.debug else logging.INFO
    configure_logging(log_level=log_level)
    logger.info("Запуск приложения")
    logger.info("Режим логирования: %s", "DEBUG" if args.debug else "INFO")

    validate_settings()
    settings = load_settings()
    logger.info("Конфигурация загружена")
    system_prompt = load_system_prompt(settings.system_prompt_doc_url)
    logger.info("Системный промпт получен из Google Docs")

    sheets_service = GoogleSheetsService(
        service_account_info=settings.google_service_account_info,
        responses_sheet_url=settings.responses_sheet_url,
        knowledge_base_sheet_url=settings.knowledge_base_sheet_url,
        enable_verbose_logs=args.debug,
    )
    assistant = ReviewAssistant(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        system_prompt=system_prompt,
    )
    bot = ReviewBot(
        telegram_token=settings.telegram_bot_token,
        assistant=assistant,
        sheets_service=sheets_service,
        enable_verbose_logs=args.debug,
    )
    logger.info("Инициализация завершена, бот запускается")
    bot.run()


if __name__ == "__main__":
    main()
