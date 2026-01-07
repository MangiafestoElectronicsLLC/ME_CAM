from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from loguru import logger
from config_manager import get_config
import os

def upload_to_gdrive(filepath):
    cfg = get_config()
    gcfg = cfg["google_drive"]

    if not gcfg["enabled"]:
        logger.info("[GDRIVE] Upload disabled.")
        return None

    try:
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(gcfg["credentials_file"])

        if gauth.credentials is None:
            logger.error("[GDRIVE] Missing credentials.json")
            return None

        drive = GoogleDrive(gauth)

        file = drive.CreateFile({
            "title": os.path.basename(filepath),
            "parents": [{"id": gcfg["folder_id"]}]
        })
        file.SetContentFile(filepath)
        file.Upload()

        logger.info(f"[GDRIVE] Uploaded: {filepath}")
        return file["id"]

    except Exception as e:
        logger.error(f"[GDRIVE] Upload failed: {e}")
        return None
