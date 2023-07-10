from flask import Flask
from app import db
from app import app

from loguru import logger


logger.add(
    "debug.log",
    format="{time} {level} {message}",
    level="INFO",
    rotation="10 MB",
    compression="zip",
)
logger.debug("Starting CoPilot...")

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
