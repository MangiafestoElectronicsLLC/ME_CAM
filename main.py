from web.app import app
from loguru import logger

if __name__ == "__main__":
    logger.add("logs/mecam.log", rotation="10 MB", retention="14 days")
    # Flask dev server – behind systemd, fine for LAN appliance
    app.run(host="0.0.0.0", port=8080, debug=False)
from web.app import app

if __name__ == "__main__":
    # Run Flask dashboard + camera system
    app.run(host="0.0.0.0", port=8080)
