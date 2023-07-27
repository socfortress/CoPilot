# from flask import Flask
from loguru import logger

from app import app

logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="INFO",
    rotation="10 MB",
    compression="zip",
)
logger.debug("Starting CoPilot...")

if __name__ == "__main__":
    app.run(debug=True)
