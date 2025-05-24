import os
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from handlers import start, button, handle_message, export_notes
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler("export", export_notes))

def scheduled_export():
    from telegram import Update
    from types import SimpleNamespace
    import asyncio

    class DummyMessage:
        def __init__(self, user_id):
            self.chat = self
            self.id = user_id
            self.from_user = SimpleNamespace(id=user_id)
        async def reply_text(self, text, **kwargs):
            logging.info(f"[SCHEDULED EXPORT] {text}")
        async def send_action(self, *args, **kwargs): pass
        async def reply_document(self, *args, **kwargs): pass

    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
    if not admin_ids:
        return
    dummy = DummyMessage(admin_ids[0])
    fake_update = Update(update_id=0, message=dummy)
    asyncio.run(export_notes(fake_update, application))

scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.add_job(scheduled_export, "cron", hour=20, minute=0)
scheduler.start()

application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=BOT_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}"
)
