import os
import re
import logging
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

def get_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("О здравии", callback_data="ozdravii")],
        [InlineKeyboardButton("Об упокоении", callback_data="oupokoenii")],
        [InlineKeyboardButton("Пожертвовать", callback_data="donate")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=get_keyboard())

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data in ["ozdravii", "oupokoenii"]:
        context.user_data["type"] = query.data
        await query.message.reply_text("Введите имена в родительном падеже: Марии, младенца Сергия")
    elif query.data == "donate":
        with open("static/qr-code.jpg", "rb") as qr:
            await query.message.reply_photo(
                photo=qr,
                caption="Введите сумму в приложении банка по ссылке https://qr.nspk.ru/BS2A003TTV82T23F844A34OJIMUM20JS?type=01&bank=100000000005&crc=7FF6 Спасибо!"
            )
        await query.message.reply_text("Выберите действие:", reply_markup=get_keyboard())

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
        response = "✅ Имена о здравии приняты." if note_type == "ozdravii" else "✅ Имена об упокоении приняты."
        await update.message.reply_text(response, reply_markup=get_keyboard())
    else:
        await update.message.reply_text("⚠ Не удалось распознать имена. Попробуйте снова.", reply_markup=get_keyboard())
    context.user_data["type"] = None

async def export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.constants import ChatAction
    import yadisk

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
            try:
                token = os.getenv("YANDEX_DISK_TOKEN")
                if token:
                    y = yadisk.YaDisk(token=token)
                    y.upload(path, f"/pominovenie/{os.path.basename(path)}", overwrite=True)
            except Exception as e:
                logging.error(f"Ошибка при выгрузке на Яндекс.Диск: {e}")
            os.remove(path)
            exported = True

    if exported:
        await update.message.reply_text("✅ Записки выгружены, скопированы на Яндекс.Диск и обнулены.")
    else:
        await update.message.reply_text("⚠ Папка с записками пуста.")


from utils.yadisk_utils import upload_docx_to_yadisk
from datetime import datetime
import os
import shutil

async def upload_yadisk_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "").split(",")))
    if update.effective_user.id not in ADMIN_IDS:
        return
    filename = f"zapiski_{datetime.now().strftime('%Y-%m-%d')}.docx"
    file_path = os.path.join(".", filename)
    if not os.path.exists(file_path):
        await update.message.reply_text("Файл не найден для загрузки.")
        return
    archived_path = os.path.join(".", f"арх_{filename}")
    shutil.move(file_path, archived_path)
    success = upload_docx_to_yadisk(archived_path)
    if success:
        await update.message.reply_text("Файл успешно загружен на Яндекс.Диск.")
    else:
        await update.message.reply_text("Ошибка при загрузке на Яндекс.Диск.")
