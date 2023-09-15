from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
import bcrypt
from app.models import Users  # Import your Users model here
from loguru import logger

bp = Blueprint("login", __name__)

@bp.route("/login", methods=["POST"])
def login():
