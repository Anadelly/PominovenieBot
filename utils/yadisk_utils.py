import yadisk
import os
import logging
from datetime import datetime

def upload_docx_to_yadisk(file_path):
    token = os.environ.get("YANDEX_DISK_TOKEN")
    if not token:
        logging.error("YANDEX_DISK_TOKEN не найден в переменных окружения")
        return False
    y = yadisk.YaDisk(token=token)
    if not y.check_token():
        logging.error("Недействительный токен Яндекс.Диска")
        return False
    date_folder = datetime.now().strftime("%Y-%m-%d")
    remote_dir = f"/записки/{date_folder}"
    try:
        if not y.is_dir(remote_dir):
            y.mkdir(remote_dir)
        remote_path = f"{remote_dir}/{os.path.basename(file_path)}"
        y.upload(file_path, remote_path, overwrite=True)
        return True
    except Exception as e:
        logging.exception(f"Ошибка при загрузке файла на Яндекс.Диск: {e}")
        return False
