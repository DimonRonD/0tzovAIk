from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


logger = logging.getLogger(__name__)


RESPONSES_HEADERS = [
    "id",
    "Response_date",
    "Response",
    "Tone",
    "Topic",
    "Answer_date",
    "Answer",
    "Template",
]

KNOWLEDGE_BASE_HEADERS = [
    "id",
    "Response_Template",
    "Answer_Template",
]


@dataclass(frozen=True)
class KnowledgeTemplate:
    template_id: str
    response_template: str
    answer_template: str


class GoogleSheetsService:
    def __init__(
        self,
        service_account_info: dict,
        responses_sheet_url: str,
        knowledge_base_sheet_url: str,
        enable_verbose_logs: bool = False,
    ):
        self.enable_verbose_logs = enable_verbose_logs
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        logger.info("Инициализация клиента Google Sheets")
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scope)
        client = gspread.authorize(credentials)

        self.responses_sheet = client.open_by_url(responses_sheet_url).sheet1
        self.knowledge_base_sheet = client.open_by_url(knowledge_base_sheet_url).sheet1
        logger.info("Таблицы Google Sheets успешно открыты")
        self._ensure_headers()

    def _ensure_headers(self) -> None:
        logger.debug("Проверка заголовков таблиц")
        if self.responses_sheet.row_values(1) != RESPONSES_HEADERS:
            self.responses_sheet.update("A1:H1", [RESPONSES_HEADERS])
            logger.info("Заголовки таблицы откликов обновлены")

        if self.knowledge_base_sheet.row_values(1) != KNOWLEDGE_BASE_HEADERS:
            self.knowledge_base_sheet.update("A1:C1", [KNOWLEDGE_BASE_HEADERS])
            logger.info("Заголовки таблицы базы знаний обновлены")

    def get_knowledge_templates(self) -> list[KnowledgeTemplate]:
        logger.info("Чтение шаблонов из базы знаний")
        records = self.knowledge_base_sheet.get_all_records()
        templates: list[KnowledgeTemplate] = []

        for row in records:
            template_id = str(row.get("id", "")).strip()
            response_template = str(row.get("Response_Template", "")).strip()
            answer_template = str(row.get("Answer_Template", "")).strip()
            if not template_id or not answer_template:
                continue
            templates.append(
                KnowledgeTemplate(
                    template_id=template_id,
                    response_template=response_template,
                    answer_template=answer_template,
                )
            )

        logger.info("Загружено шаблонов: %s", len(templates))
        return templates

    def append_response(
        self,
        review_id: str,
        review_text: str,
        tone: str,
        topic: str,
        answer_text: str,
        template_label: str,
    ) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [review_id, now, review_text, tone, topic, now, answer_text, template_label]
        logger.info("Сохранение ответа в Google Sheets")
        if self.enable_verbose_logs:
            logger.debug("Данные строки: %s", row)
        self.responses_sheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info("Ответ успешно сохранен в Google Sheets")
