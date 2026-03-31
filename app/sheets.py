from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials


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
    def __init__(self, service_account_info: dict, responses_sheet_url: str, knowledge_base_sheet_url: str):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        client = gspread.authorize(credentials)

        self.responses_sheet = client.open_by_url(responses_sheet_url).sheet1
        self.knowledge_base_sheet = client.open_by_url(knowledge_base_sheet_url).sheet1
        self._ensure_headers()

    def _ensure_headers(self) -> None:
        if self.responses_sheet.row_values(1) != RESPONSES_HEADERS:
            self.responses_sheet.update("A1:H1", [RESPONSES_HEADERS])

        if self.knowledge_base_sheet.row_values(1) != KNOWLEDGE_BASE_HEADERS:
            self.knowledge_base_sheet.update("A1:C1", [KNOWLEDGE_BASE_HEADERS])

    def get_knowledge_templates(self) -> list[KnowledgeTemplate]:
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
        self.responses_sheet.append_row(row, value_input_option="USER_ENTERED")
