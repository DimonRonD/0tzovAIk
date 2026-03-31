from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI

from app.prompts import SYSTEM_PROMPT
from app.sheets import KnowledgeTemplate


@dataclass(frozen=True)
class ReviewReply:
    tone: str
    topic: str
    answer: str
    template_label: str


class ReviewAssistant:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def build_reply(self, review_text: str, templates: list[KnowledgeTemplate]) -> ReviewReply:
        matched_template = self._match_template(review_text, templates)
        template_label = matched_template.template_id if matched_template else "Urgent"
        answer_template = matched_template.answer_template if matched_template else ""

        user_prompt = self._build_user_prompt(review_text, templates, answer_template, template_label)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.output_text.strip()
        parsed = json.loads(raw_text)

        return ReviewReply(
            tone=parsed["tone"].strip(),
            topic=parsed["topic"].strip(),
            answer=parsed["answer"].strip(),
            template_label=template_label,
        )

    def _match_template(self, review_text: str, templates: list[KnowledgeTemplate]) -> KnowledgeTemplate | None:
        if not templates:
            return None

        template_lines = []
        for template in templates:
            template_lines.append(
                f'ID: {template.template_id}; '
                f'Пример отзыва: {template.response_template}; '
                f'Шаблон ответа: {template.answer_template}'
            )

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Ты выбираешь один лучший шаблон ответа из базы знаний. "
                        "Если подходящего шаблона нет, верни только слово Urgent. "
                        "Если шаблон подходит, верни только его ID без пояснений."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Отзыв клиента:\n{review_text}\n\n"
                        f"Доступные шаблоны:\n" + "\n".join(template_lines)
                    ),
                },
            ],
        )

        selected = response.output_text.strip()
        for template in templates:
            if template.template_id == selected:
                return template
        return None

    @staticmethod
    def _build_user_prompt(
        review_text: str,
        templates: list[KnowledgeTemplate],
        answer_template: str,
        template_label: str,
    ) -> str:
        knowledge_base_note = "Подходящий шаблон не найден. Сформируй ответ с нуля."
        if template_label != "Urgent":
            knowledge_base_note = (
                f"Найден шаблон {template_label}. Используй его как основу ответа и адаптируй под конкретный отзыв. "
                f"Шаблон ответа: {answer_template}"
            )

        return (
            f"Отзыв клиента:\n{review_text}\n\n"
            f"{knowledge_base_note}\n\n"
            "Нужно определить тон, тему и подготовить итоговый ответ."
        )
