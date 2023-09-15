from datetime import timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
import bcrypt
from app.models.users import Users
from loguru import logger
from datetime import datetime

from app import db

bp = Blueprint("users", __name__)

@bp.route("/register", methods=["POST"])
def register():
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    customerCode = request.json.get("customerCode", None)
    usersFirstName = request.json.get("usersFirstName", None)
    usersLastName = request.json.get("usersLastName", None)
    usersEmail = request.json.get("usersEmail", None)
    usersRole = request.json.get("usersRole", None)
    imageFile = request.json.get("imageFile", None)
    notifications = request.json.get("notifications", 0)  # Default to 0 if not provided
    password = request.json.get("password", None)

    # Validate mandatory fields
    if not customerCode or not usersEmail or not password:
        return jsonify({"message": "Missing mandatory fields", "success": False}), 400

    # Check if the user already exists
    existing_user = Users.query.filter_by(usersEmail=usersEmail).first()
    if existing_user:
        return jsonify({"message": "User already exists", "success": False}), 409

    # Hash the password using bcrypt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Create new user object
    new_user = Users(
        customerCode=customerCode,
        usersFirstName=usersFirstName,
        usersLastName=usersLastName,
        usersEmail=usersEmail,
        usersRole=usersRole,
        imageFile=imageFile,
        notifications=notifications,
        passwordHash=hashed_password
    )

    # Add new user to the database
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "success": True}), 201

@bp.route("/login", methods=["POST"])
def login():
    """
    Route for logging in a user.
    """
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    email = request.json.get("email", None)
    password = request.json.get("password", None)

    if not email:
        return jsonify({"message": "Missing email parameter", "success": False}), 400
    if not password:
        return jsonify({"message": "Missing password parameter", "success": False}), 400

    # Fetch the user from database (Assuming usersEmail is unique)
    user = Users.query.filter_by(usersEmail=email).first()
    if not user:
        return jsonify({"message": "User not found", "success": False}), 404

    # Check if the password is correct
    if not bcrypt.checkpw(password.encode('utf-8'), user.passwordHash.encode('utf-8')):
        return jsonify({"message": "Incorrect password", "success": False}), 401

    # Create a new access token
    access_token = create_access_token(identity=email, expires_delta=timedelta(days=1))

    # Update the user's token and expiry
    user.jwtToken = access_token
    # Update the token's expiry time
    if user.tokenExpiry is None:
        user.tokenExpiry = datetime.utcnow()  # Initialize with the current time if it's None
    user.tokenExpiry = user.tokenExpiry + timedelta(days=1)
    db.session.commit()

    return jsonify({"message": "User logged in successfully", "success": True, "token": access_token}), 200

