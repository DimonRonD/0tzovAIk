from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.ai_service import ReviewAssistant
from app.sheets import GoogleSheetsService


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
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_review))
        self.application.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.info("Получена команда /start")
        await update.message.reply_text(
            "Здравствуйте! Отправьте отзыв клиента, и я подготовлю корректный ответ."
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
