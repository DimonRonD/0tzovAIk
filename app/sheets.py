from __future__ import annotations

import logging
from collections import Counter, defaultdict
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


@dataclass(frozen=True)
class AnalyticsSummary:
    report_date: str
    total_reviews: int
    tone_counts: dict[str, int]
    urgent_by_day_and_tone: dict[str, dict[str, int]]


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

    def get_analytics_summary(self, report_date: str) -> AnalyticsSummary:
        logger.info("Построение аналитики по таблице откликов для даты %s", report_date)
        records = self.responses_sheet.get_all_records()

        tone_counts: Counter[str] = Counter()
        urgent_by_day_and_tone: defaultdict[str, Counter[str]] = defaultdict(Counter)
        total_reviews = 0

        for row in records:
            response_date = str(row.get("Response_date", "")).strip()
            tone = str(row.get("Tone", "")).strip() or "не указано"
            template_label = str(row.get("Template", "")).strip()
            row_date = self._extract_date(response_date)

            if row_date == report_date:
                total_reviews += 1
                tone_counts[tone] += 1

            if "urgent" in template_label.lower() and row_date:
                urgent_by_day_and_tone[row_date][tone] += 1

        logger.info(
            "Аналитика построена: total_reviews=%s, urgent_days=%s",
            total_reviews,
            len(urgent_by_day_and_tone),
        )
        return AnalyticsSummary(
            report_date=report_date,
            total_reviews=total_reviews,
            tone_counts=dict(sorted(tone_counts.items())),
            urgent_by_day_and_tone={
                day: dict(sorted(counts.items()))
                for day, counts in sorted(urgent_by_day_and_tone.items())
            },
        )

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

    @staticmethod
    def _extract_date(value: str) -> str:
        if not value:
            return ""

        normalized = value.strip().replace("/", "-").replace(".", "-")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
            try:
                return datetime.strptime(normalized, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        return ""
