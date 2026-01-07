from utils.logger import get_logger

logger = get_logger("gdrive_uploader")

try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
except ImportError:
    GoogleAuth = None
    GoogleDrive = None
    logger.warning("PyDrive2 not available, Google Drive disabled.")


class GDriveUploader:
    def __init__(self, enabled: bool = False, settings_yaml: str = "client_secrets.json"):
        self.enabled = enabled and GoogleAuth is not None
        self.drive = None
        if self.enabled:
            gauth = GoogleAuth()
            gauth.LoadClientConfigFile(settings_yaml)
            gauth.LocalWebserverAuth()
            self.drive = GoogleDrive(gauth)
            logger.info("Google Drive uploader initialized.")

    def upload_file(self, file_path: str, folder_id: str = None):
        if not self.enabled or self.drive is None:
            return
        try:
            file = self.drive.CreateFile({"parents": [{"id": folder_id}]} if folder_id else {})
            file.SetContentFile(file_path)
            file.Upload()
            logger.info(f"Uploaded {file_path} to Google Drive.")
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
