from __future__ import annotations

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.ai_service import ReviewAssistant
from app.sheets import AnalyticsSummary, GoogleSheetsService


logger = logging.getLogger(__name__)


class ReviewBot:
    def __init__(
        self,
        telegram_token: str,
        assistant: ReviewAssistant,
        sheets_service: GoogleSheetsService,
        enable_verbose_logs: bool = False,
    ):
        self.application = Application.builder().token(telegram_token).build()
        self.assistant = assistant
        self.sheets_service = sheets_service
        self.enable_verbose_logs = enable_verbose_logs

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("analize", self.analize))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_review))
        self.application.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Получена команда /start")
        await update.message.reply_text(
            "Здравствуйте! Отправьте отзыв клиента, и я подготовлю корректный ответ."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Получена команда /help")
        await update.message.reply_text(self._format_help_message())

    async def analize(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Получена команда /analize")
        report_date = self._parse_report_date(context.args[0] if context.args else "")

        try:
            analytics = self.sheets_service.get_analytics_summary(report_date)
            await update.message.reply_text(self._format_analytics_message(analytics))
            logger.info("Аналитика отправлена пользователю за дату %s", report_date)
        except ValueError:
            await update.message.reply_text(
                "Неверный формат даты. Используйте `/analize 2026-03-31` или `/analize 31.03.2026`.",
                parse_mode="Markdown",
            )
        except Exception:
            logger.exception("Ошибка при построении аналитики за дату %s", report_date)
            await update.message.reply_text(
                "Не удалось получить аналитику. Попробуйте еще раз чуть позже."
            )

    async def process_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            logger.debug("Обновление пропущено: нет message или пользователя")
            return

        review_text = update.message.text.strip()
        if not review_text:
            logger.info("Получено пустое сообщение")
            await update.message.reply_text("Пожалуйста, отправьте текстовый отзыв.")
            return

        review_id = str(update.message.message_id)
        logger.info("Получен новый отзыв: id=%s user_id=%s", review_id, update.effective_user.id)
        if self.enable_verbose_logs:
            logger.debug("Текст отзыва: %s", review_text)

        try:
            templates = self.sheets_service.get_knowledge_templates()
            result = self.assistant.build_reply(review_text, templates)
            logger.info(
                "Ответ подготовлен: tone=%s topic=%s template=%s",
                result.tone,
                result.topic,
                result.template_label,
            )

            self.sheets_service.append_response(
                review_id=review_id,
                review_text=review_text,
                tone=result.tone,
                topic=result.topic,
                answer_text=result.answer,
                template_label=result.template_label,
            )

            await update.message.reply_text(result.answer)
            logger.info("Ответ отправлен пользователю")
        except Exception:
            logger.exception("Ошибка при обработке отзыва id=%s", review_id)
            await update.message.reply_text(
                "Не удалось обработать отзыв автоматически. Попробуйте еще раз чуть позже."
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.exception("Необработанная ошибка Telegram", exc_info=context.error)

    def run(self) -> None:
        logger.info("Запуск Telegram polling")
        self.application.run_polling()

    @staticmethod
    def _parse_report_date(raw_date: str) -> str:
        if not raw_date:
            return datetime.now().strftime("%Y-%m-%d")

        normalized = raw_date.strip().replace("/", ".").replace("-", ".")
        for fmt in ("%d.%m.%Y", "%Y.%m.%d"):
            try:
                return datetime.strptime(normalized, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise ValueError("invalid date format")

    @staticmethod
    def _format_analytics_message(analytics: AnalyticsSummary) -> str:
        tone_lines = (
            [f"- {tone}: {count}" for tone, count in analytics.tone_counts.items()]
            if analytics.tone_counts
            else ["- отзывов нет"]
        )

        urgent_lines: list[str] = []
        if analytics.urgent_by_day_and_tone:
            for day, counts in analytics.urgent_by_day_and_tone.items():
                total = sum(counts.values())
                details = ", ".join(f"{tone}: {count}" for tone, count in counts.items())
                urgent_lines.append(f"- {day}: всего {total} ({details})")
        else:
            urgent_lines.append("- записей с Urgent нет")

        return "\n".join(
            [
                f"Analitics for {analytics.report_date}",
                "",
                "1. Отзывы за выбранную дату",
                f"- всего отзывов: {analytics.total_reviews}",
                *tone_lines,
                "",
                "2. Urgent по дням и типам",
                *urgent_lines,
            ]
        )

    @staticmethod
    def _format_help_message() -> str:
        return "\n".join(
            [
                "Доступные команды:",
                "/start - краткое приветствие и запуск бота",
                "/help - список всех доступных команд",
                "/analize - аналитика по отзывам за текущий день",
                "/analize YYYY-MM-DD - аналитика за указанную дату",
                "/analize DD.MM.YYYY - аналитика за указанную дату в русском формате",
                "",
                "Также можно просто отправить текст отзыва, и бот подготовит ответ автоматически.",
            ]
        )
