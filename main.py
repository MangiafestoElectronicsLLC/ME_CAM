from loguru import logger
from web.app import app
import os

os.makedirs("logs", exist_ok=True)

if __name__ == "__main__":
    logger.add("logs/mecam.log", rotation="10 MB", retention="14 days", backtrace=True, diagnose=True)
    app.run(host="0.0.0.0", port=8080, debug=False)
