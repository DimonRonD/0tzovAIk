from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from app.sheets import KnowledgeTemplate


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewReply:
    tone: str
    topic: str
    answer: str
    template_label: str


class ReviewAssistant:
    def __init__(self, api_key: str, model: str, system_prompt: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        logger.debug("Клиент OpenAI инициализирован с моделью %s", model)

    def build_reply(self, review_text: str, templates: list[KnowledgeTemplate]) -> ReviewReply:
        logger.info("Начало генерации ответа")
        logger.debug("Длина текста отзыва: %s", len(review_text))
        logger.debug("Шаблонов в базе знаний: %s", len(templates))

        matched_template = self._match_template(review_text, templates)
        template_label = matched_template.template_id if matched_template else "Urgent"
        answer_template = matched_template.answer_template if matched_template else ""
        logger.info("Результат подбора шаблона: %s", template_label)

        request_reply = self._build_request_reply(review_text, matched_template, template_label)
        if request_reply is not None:
            logger.info("Применен специальный сценарий для типа 'Просьба'")
            return request_reply

        user_prompt = self._build_user_prompt(review_text, templates, answer_template, template_label)
        logger.debug("Подготовлен пользовательский промпт для генерации ответа")
        response = self.client.responses.create(
            model=self.model,
            text={"format": {"type": "json_object"}},
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_text = response.output_text.strip()
        logger.debug("Получен ответ модели: %s", raw_text)
        parsed = self._parse_json_response(raw_text)
        logger.info("Ответ модели успешно разобран")

        return ReviewReply(
            tone=parsed["tone"].strip(),
            topic=parsed["topic"].strip(),
            answer=parsed["answer"].strip(),
            template_label=template_label,
        )

    def _match_template(self, review_text: str, templates: list[KnowledgeTemplate]) -> KnowledgeTemplate | None:
        if not templates:
            logger.info("База знаний пуста, шаблон не выбирается")
            return None

        heuristic_match = self._match_template_by_similarity(review_text, templates)
        if heuristic_match is not None:
            logger.info("Найден близкий шаблон по Response_Template: %s", heuristic_match.template_id)
            return heuristic_match

        template_lines = []
        for template in templates:
            template_lines.append(
                f'ID: {template.template_id}; '
                f'Пример отзыва: {template.response_template}; '
                f'Шаблон ответа: {template.answer_template}'
            )

        logger.debug("Отправлен запрос на выбор шаблона")
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
        logger.debug("Модель выбрала шаблон: %s", selected)
        for template in templates:
            if template.template_id == selected:
                logger.info("Найден подходящий шаблон: %s", template.template_id)
                return template
        logger.info("Подходящий шаблон не найден")
        return None

    def _parse_json_response(self, raw_text: str) -> dict:
        if not raw_text:
            logger.error("Модель вернула пустой ответ вместо JSON")
            raise ValueError("OpenAI вернул пустой ответ")

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Не удалось разобрать полный ответ как JSON, пробую извлечь JSON-блок")

        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            candidate = raw_text[json_start : json_end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                logger.error("Извлеченный JSON-блок тоже невалиден: %s", candidate)

        raise ValueError("OpenAI вернул невалидный JSON")

    def _build_request_reply(
        self,
        review_text: str,
        matched_template: KnowledgeTemplate | None,
        template_label: str,
    ) -> ReviewReply | None:
        normalized_text = review_text.lower()
        request_markers = [
            "прошу",
            "пожалуйста",
            "сделайте",
            "помогите",
            "одолжите",
            "можете",
            "можно",
        ]
        if not any(marker in normalized_text for marker in request_markers):
            return None

        answer_text = (
            matched_template.answer_template.strip()
            if matched_template and matched_template.answer_template.strip()
            else "Конечно, ваше пожелание будет выполнено, велосипедисты уже выехали. Спасибо за обращение."
        )

        return ReviewReply(
            tone="просьба",
            topic="просьба клиента",
            answer=answer_text,
            template_label=template_label,
        )

    def _match_template_by_similarity(
        self, review_text: str, templates: list[KnowledgeTemplate]
    ) -> KnowledgeTemplate | None:
        review_tokens = self._tokenize(review_text)
        if not review_tokens:
            return None

        best_template: KnowledgeTemplate | None = None
        best_score = 0.0

        for template in templates:
            template_tokens = self._tokenize(template.response_template)
            if not template_tokens:
                continue

            overlap = review_tokens & template_tokens
            score = len(overlap) / len(template_tokens)
            logger.debug(
                "Сравнение с шаблоном %s: совпало %s из %s токенов, score=%.2f",
                template.template_id,
                len(overlap),
                len(template_tokens),
                score,
            )

            if score > best_score:
                best_score = score
                best_template = template

        if best_template is not None and best_score >= 0.5:
            return best_template
        return None

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Zа-яА-Я0-9]+", text.lower()))

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
            "Нужно определить тон, тему и подготовить итоговый ответ.\n"
            "Верни результат строго в JSON-формате с полями tone, topic и answer."
        )
