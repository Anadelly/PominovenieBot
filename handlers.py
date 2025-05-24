
import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from docx import Document
from docx.shared import Pt

ZAPISKI_DIR = "zapiski"
ZDRAVIE_FILE = os.path.join(ZAPISKI_DIR, "о_здравии.docx")
UPOKOENIE_FILE = os.path.join(ZAPISKI_DIR, "о_упокоении.docx")

def ensure_dir():
    os.makedirs(ZAPISKI_DIR, exist_ok=True)

def append_to_docx(filepath, names, sender):
    if os.path.exists(filepath):
        doc = Document(filepath)
    else:
        doc = Document()
        doc.add_table(rows=0, cols=1)
    table = doc.tables[0]
    for name in names:
        row = table.add_row()
        cell = row.cells[0]
        para = cell.paragraphs[0]
        para.add_run(f"{name} ({sender})").font.size = Pt(14)
    doc.save(filepath)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("О здравии", callback_data="ozdravii")],
        [InlineKeyboardButton("Об упокоении", callback_data="oupokoenii")],
        [InlineKeyboardButton("Пожертвовать", callback_data="donate")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data in ["ozdravii", "oupokoenii"]:
        context.user_data["type"] = query.data
        await query.message.reply_text("Пожалуйста, введите имена в формате: Марии, Сергия")
    elif query.data == "donate":
        with open("static/qr-code.jpg", "rb") as qr:
            await query.message.reply_photo(
                photo=qr,
                caption="Введите сумму в приложении банка по ссылке https://qr.nspk.ru/BS2A003TTV82T23F844A34OJIMUM20JS?type=01&bank=100000000005&crc=7FF6 Спасибо!"
            )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_type = context.user_data.get("type")
    if not note_type:
        return

    ensure_dir()
    names = re.findall(r"[А-Яа-яёЁ ]+", update.message.text)
    names = [name.strip() for name in names if name.strip()]
    sender = update.effective_user.full_name or "неизвестный"

    if names:
        filepath = ZDRAVIE_FILE if note_type == "ozdravii" else UPOKOENIE_FILE
        append_to_docx(filepath, names, sender)
        await update.message.reply_text("🙏 Имена записаны. Спасибо.")
    else:
        await update.message.reply_text("⚠ Не удалось распознать имена. Попробуйте снова.")
    context.user_data["type"] = None

async def export_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.constants import ChatAction

    user_id = update.effective_user.id
    admin_ids = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
    if user_id not in admin_ids:
        await update.message.reply_text("⛔ У вас нет доступа к этой команде.")
        return

    ensure_dir()
    exported = False
    for path in [ZDRAVIE_FILE, UPOKOENIE_FILE]:
        if os.path.exists(path):
            await update.message.chat.send_action(action=ChatAction.UPLOAD_DOCUMENT)
            with open(path, "rb") as f:
                await update.message.reply_document(f)
            os.remove(path)
            exported = True

    if exported:
        await update.message.reply_text("✅ Записки выгружены и обнулены.")
    else:
        await update.message.reply_text("⚠ Папка с записками пуста.")
