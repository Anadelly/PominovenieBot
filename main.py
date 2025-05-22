import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from docx import Document
from datetime import datetime
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("О здравии", callback_data='ozdravii')],
        [InlineKeyboardButton("Об упокоении", callback_data='oupokoenii')],
        [InlineKeyboardButton("Пожертвовать", callback_data='donate')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data in ['ozdravii', 'oupokoenii']:
        context.user_data['type'] = query.data
        await query.message.reply_text("Пожалуйста, введите имена:")
    elif query.data == 'donate':
        await query.message.reply_photo(photo=open('static/qr_code.png', 'rb'),
                                        caption="Отсканируйте QR-код в приложении банка и введите сумму пожертвования.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_type = context.user_data.get('type')
    if note_type:
        names = re.findall(r'\b[А-Яа-яёЁ]+\b', update.message.text)
        if names:
            filename = f"{'о_здравии' if note_type == 'ozdravii' else 'о_упокоении'}_{datetime.now().strftime('%d%m%Y')}.docx"
            doc = Document()
            table = doc.add_table(rows=1, cols=3)
            row_cells = table.rows[0].cells
            for i in range(3):
                if i < len(names):
                    row_cells[i].text = names[i]
            doc.save(filename)
            await update.message.reply_text("Записка сохранена.")
        else:
            await update.message.reply_text("Не удалось распознать имена. Пожалуйста, попробуйте снова.")
        context.user_data['type'] = None

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
