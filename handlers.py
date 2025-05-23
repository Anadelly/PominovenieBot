import re
import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from docx import Document
from docx.shared import Pt

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"START called: message={bool(update.message)}, callback={bool(update.callback_query)}")

    keyboard = [
        [InlineKeyboardButton("О здравии", callback_data="ozdravii")],
        [InlineKeyboardButton("Об упокоении", callback_data="oupokoenii")],
        [InlineKeyboardButton("Помощь храму", callback_data="donate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logging.info(f"BUTTON clicked: data={query.data}")
    if query.data in ["ozdravii", "oupokoenii"]:
        context.user_data["type"] = query.data
        await query.message.reply_text("Пожалуйста, введите имена в формате: Марии, Сергия")
    elif query.data == "donate":
        with open("static/qr-code.jpg", "rb") as qr:
            await query.message.reply_photo(
                photo=qr,
                caption="📷 Отсканируйте QR-код и введите сумму в приложении банка по ссылке https://qr.nspk.ru/BS2A003TTV82T23F844A34OJIMUM20JS?type=01&bank=100000000005&crc=7FF6 Спасибо!"
            )

# остальная часть handle_message и export_notes — без изменений

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_type = context.user_data.get("type")
    if note_type:
        names = re.findall(r"[А-Яа-яёЁ ]+", update.message.text)
        names = [name.strip() for name in names if name.strip()]
        if names:
            now = datetime.now().strftime("%d%m%Y")
            filename = f"{'о_здравии' if note_type == 'ozdravii' else 'о_упокоении'}_{now}.docx"
            os.makedirs("zapiski", exist_ok=True)
            filepath = os.path.join("zapiski", filename)
            doc = Document()
            table = doc.add_table(rows=1, cols=3)
            cells = table.rows[0].cells
            for i in range(min(3, len(names))):
                paragraph = cells[i].paragraphs[0]
                run = paragraph.add_run(names[i])
                run.font.size = Pt(14)
            doc.save(filepath)
            await update.message.reply_text("Записка сохранена. 🙏")
        else:
            await update.message.reply_text("Не удалось распознать имена. Попробуйте снова.")
        context.user_data["type"] = None

async def export_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
    if user_id not in admin_ids:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return
    folder = "zapiski"
    if not os.path.exists(folder):
        await update.message.reply_text("Папка с записками пуста.")
        return
    files = [f for f in os.listdir(folder) if f.endswith(".docx")]
    if not files:
        await update.message.reply_text("Нет новых записок.")
        return
    for file in files:
        with open(os.path.join(folder, file), "rb") as doc:
            await update.message.reply_document(document=doc, filename=file)
