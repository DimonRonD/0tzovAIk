import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_model: str
    responses_sheet_url: str
    knowledge_base_sheet_url: str
    system_prompt_doc_url: str
    google_service_account_info: dict


def load_settings() -> Settings:
    load_dotenv()

    google_service_account_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    google_service_account_info = json.loads(google_service_account_raw)

    private_key = google_service_account_info.get("private_key")
    if isinstance(private_key, str):
        google_service_account_info["private_key"] = private_key.replace("\\n", "\n")

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        responses_sheet_url=os.getenv("GOOGLE_RESPONSES_SHEET_URL", ""),
        knowledge_base_sheet_url=os.getenv("GOOGLE_KNOWLEDGE_BASE_SHEET_URL", ""),
        system_prompt_doc_url=os.getenv("SYSTEM_PROMPT_DOC_URL", ""),
        google_service_account_info=google_service_account_info,
    )
