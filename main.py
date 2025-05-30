import os
import logging
import threading
import asyncio
from aiohttp import web
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from telegram import Update
from handlers import start, button, handle_message, export_notes, export_handler, upload_yadisk_handler

from apscheduler.schedulers.background import BackgroundScheduler

# Настройка логов
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

# Основной бот
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("export", export_notes))
application.add_handler(CommandHandler("upload_yadisk", upload_yadisk_handler))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler("export", export_notes))

# Ежедневный экспорт
from utils.yadisk_utils import upload_docx_to_yadisk
from telegram.constants import ChatAction
from export import generate_docx
import datetime
import shutil

async def scheduled_export_real(application):
    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
    if not admin_ids:
        return

    filename = f"zapiski_{datetime.datetime.now().strftime('%Y-%m-%d')}.docx"
    file_path = os.path.join(".", filename)
    generate_docx(file_path)

    archived_path = os.path.join(".", f"арх_{filename}")
    shutil.move(file_path, archived_path)

    for admin_id in admin_ids:
        try:
            await application.bot.send_chat_action(chat_id=admin_id, action=ChatAction.UPLOAD_DOCUMENT)
            await application.bot.send_document(chat_id=admin_id, document=open(archived_path, "rb"))
        except Exception as e:
            print(f"Ошибка при отправке файла админу {admin_id}: {e}")

    upload_docx_to_yadisk(archived_path)

# Планировщик
scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.add_job(scheduled_export, "cron", hour=20, minute=0)
scheduler.start()

# HTTP-заглушка (GET /)
async def handle_root(request):
    return web.Response(text="✅ Bot is alive", status=200)

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logging.exception("Ошибка в вебхуке")
    return web.Response()

async def start_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_post(f"/{BOT_TOKEN}", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    await application.initialize()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    await application.start()

    logging.info("✅ Бот запущен и готов к приёму вебхуков.")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(start_server())
