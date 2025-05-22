import re
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from docx import Document
from docx.shared import Pt

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
        await query.message.reply_text("Пожалуйста, введите имена в формате:\n\nболящей Марии, младенца Сергия")
    elif query.data == 'donate':
        with open('static/qr-code.jpg', 'rb') as qr:
            await query.message.reply_photo(
                photo=qr,
                caption="📷 Отсканируйте QR-код в приложении банка и введите сумму перевода.\n\n💖 Спасибо за помощь!"
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_type = context.user_data.get('type')
    if note_type:
        names = re.findall(r'[А-Яа-яёЁ ]+', update.message.text)
        names = [name.strip() for name in names if name.strip()]
        if names:
            now = datetime.now().strftime("%d%m%Y")
            filename = f\"{'о_здравии' if note_type == 'ozdravii' else 'о_упокоении'}_{now}.docx\"
            filepath = os.path.join(\"zapiski\", filename)
            os.makedirs(\"zapiski\", exist_ok=True)
            doc = Document()
            table = doc.add_table(rows=1, cols=3)
            cells = table.rows[0].cells
            for i in range(min(3, len(names))):
                paragraph = cells[i].paragraphs[0]
                run = paragraph.add_run(names[i])
                run.font.size = Pt(14)
            doc.save(filepath)
            await update.message.reply_text(\"Записка сохранена. 🙏\")
        else:
            await update.message.reply_text(\"Не удалось распознать имена. Попробуйте снова.\")
        context.user_data['type'] = None
