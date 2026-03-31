from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.ai_service import ReviewAssistant
from app.sheets import GoogleSheetsService


class ReviewBot:
    def __init__(self, telegram_token: str, assistant: ReviewAssistant, sheets_service: GoogleSheetsService):
        self.application = Application.builder().token(telegram_token).build()
        self.assistant = assistant
        self.sheets_service = sheets_service

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_review))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Здравствуйте! Отправьте отзыв клиента, и я подготовлю корректный ответ."
        )

    async def process_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return

        review_text = update.message.text.strip()
        if not review_text:
            await update.message.reply_text("Пожалуйста, отправьте текстовый отзыв.")
            return

        review_id = str(update.message.message_id)
        templates = self.sheets_service.get_knowledge_templates()
        result = self.assistant.build_reply(review_text, templates)

        self.sheets_service.append_response(
            review_id=review_id,
            review_text=review_text,
            tone=result.tone,
            topic=result.topic,
            answer_text=result.answer,
            template_label=result.template_label,
        )

        await update.message.reply_text(result.answer)

    def run(self) -> None:
        self.application.run_polling()
