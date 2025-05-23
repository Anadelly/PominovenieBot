import os
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from handlers import start, button, handle_message, export_notes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Пример: https://pominoveniebot.onrender.com
PORT = int(os.environ.get("PORT", 10000))

application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler("export", export_notes))

# 💥 Ключевая строка: запуск PTB Webhook-сервера
application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
