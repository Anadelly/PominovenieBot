import os
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from handlers import start, button, handle_message, export_notes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ BOT_TOKEN и WEBHOOK_URL обязательны. Проверь переменные окружения.")

application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CommandHandler("export", export_notes))

# Планировщик
def scheduled_export():
    from types import SimpleNamespace

    class DummyMessage:
        def __init__(self, user_id):
            self.chat = self
            self.id = user_id
            self.from_user = SimpleNamespace(id=user_id)
        async def reply_text(self, text, **kwargs): logging.info(f"[AUTO EXPORT] {text}")
        async def send_action(self, *args, **kwargs): pass
        async def reply_document(self, document, **kwargs): logging.info("[AUTO EXPORT] Document sent")

    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
    if not admin_ids:
        logging.warning("⚠️ ADMIN_IDS не заданы.")
        return

    update = Update(update_id=0, message=DummyMessage(admin_ids[0]))

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(export_notes(update, application))
    except RuntimeError:
        asyncio.run(export_notes(update, application))

scheduler = BackgroundScheduler(timezone="Europe/Moscow")
scheduler.add_job(scheduled_export, "cron", hour=20, minute=0)
scheduler.start()

# Корневой маршрут
async def handle_root(request):
    return web.Response(text="✅ Bot is alive", status=200)

# Вебхук
async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logging.exception("❌ Ошибка при обработке вебхука")
    return web.Response()

# Запуск aiohttp + Telegram
async def main():
    # Сначала стартуем aiohttp
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_head("/", handle_root)
    app.router.add_post(f"/{BOT_TOKEN}", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"🌐 AIOHTTP сервер запущен на порту {PORT}")

    # Затем Telegram
    await application.initialize()
    result = await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
    logging.info(f"📬 Webhook установлен: {result}")
    await application.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await application.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
