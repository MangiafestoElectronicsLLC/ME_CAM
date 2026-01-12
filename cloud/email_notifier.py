import smtplib
from email.mime.text import MIMEText
from utils.logger import get_logger

logger = get_logger("email_notifier")


class EmailNotifier:
    def __init__(self, enabled: bool = False, smtp_host: str = "", smtp_port: int = 587,
                 username: str = "", password: str = "", from_addr: str = "", to_addr: str = ""):
        self.enabled = enabled
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addr = to_addr

    def send_alert(self, subject: str, body: str):
        if not self.enabled:
            return

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = self.to_addr

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
                s.starttls()
                s.login(self.username, self.password)
                s.send_message(msg)
            logger.info("Alert email sent.")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
