import yagmail
from loguru import logger
from config_manager import get_config

def send_email(subject, body, attachments=None):
    cfg = get_config()
    email_cfg = cfg["email"]

    if not email_cfg["enabled"]:
        logger.info("[EMAIL] Email notifications disabled.")
        return False

    try:
        yag = yagmail.SMTP(
            user=email_cfg["username"],
            password=email_cfg["password"],
            host=email_cfg["smtp_server"],
            port=email_cfg["smtp_port"]
        )

        yag.send(
            to=email_cfg["to_address"],
            subject=subject,
            contents=body,
            attachments=attachments
        )

        logger.info(f"[EMAIL] Sent email to {email_cfg['to_address']}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email: {e}")
        return False
