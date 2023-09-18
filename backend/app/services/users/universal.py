from datetime import datetime
from datetime import timedelta
from typing import Union, Dict, Tuple, Optional
from loguru import logger
import bcrypt
from flask_jwt_extended import create_access_token, decode_token

from app import db
from app.models.users import Users


class UniversalService:
    @staticmethod
    def validate_user_input(data):
        required_fields = ["customerCode", "usersEmail", "password"]
        for field in required_fields:
            if not data.get(field):
                return False
        return True

    @staticmethod
    def user_exists(email):
        return Users.query.filter_by(usersEmail=email).first()

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def create_user(data, hashed_password):
        new_user = Users(
            customerCode=data["customerCode"],
            usersFirstName=data.get("usersFirstName"),
            usersLastName=data.get("usersLastName"),
            usersEmail=data["usersEmail"],
            usersRole=data.get("usersRole"),
            imageFile=data.get("imageFile"),
            notifications=data.get("notifications", 0),
            passwordHash=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()

    @staticmethod
    def register_user(data):
        if not UniversalService.validate_user_input(data):
            return {"message": "Missing mandatory fields", "success": False}, 400

        if UniversalService.user_exists(data["usersEmail"]):
            return {"message": "User already exists", "success": False}, 409

        hashed_password = UniversalService.hash_password(data["password"])
        UniversalService.create_user(data, hashed_password)

        return {"message": "User registered successfully", "success": True}, 201

    @staticmethod
    def authenticate_user(email, password):
        user = UniversalService.user_exists(email)
        if not user:
            return {"message": "User not found", "success": False}, 404

        if not bcrypt.checkpw(password.encode("utf-8"), user.passwordHash.encode("utf-8")):
            return {"message": "Incorrect password", "success": False}, 401

        return user

    @staticmethod
    def generate_token(email):
        return create_access_token(identity=email, expires_delta=timedelta(days=1))

    @staticmethod
    def login_user(data):
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"message": "Missing email or password parameter", "success": False}, 400

        user = UniversalService.authenticate_user(email, password)
        if isinstance(user, tuple):
            return user

        access_token = UniversalService.generate_token(email)

        user.jwtToken = access_token
        if user.tokenExpiry is None:
            user.tokenExpiry = datetime.utcnow()
        user.tokenExpiry += timedelta(days=1)

        db.session.commit()

        return {"message": "User logged in successfully", "success": True, "token": access_token}, 200

    @staticmethod
    def decode_jwt_token(encoded_token: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Decode the given JWT token.

        :param encoded_token: The encoded JWT token as a string.
        :return: A tuple containing the decoded token as a dictionary and an error as a dictionary or None.
        """
        try:
            return decode_token(encoded_token), None
        except Exception as e:
            return None, {"message": f"Failed to decode token: {str(e)}", "success": False}

    @staticmethod
    def is_within_24_hours(decoded_token: Dict) -> bool:
        """
        Check if the decoded token's expiration is within 24 hours.

        :param decoded_token: The decoded JWT token as a dictionary.
        :return: Boolean indicating if the token is within 24 hours of expiration.
        """
        original_expiry = datetime.utcfromtimestamp(decoded_token["exp"])
        return original_expiry - datetime.utcnow() <= timedelta(days=1)

    @staticmethod
    def update_user_token(user: Users, new_access_token: str) -> None:
        """
        Update the user record in the database with a new token and new expiration time.

        :param user: The user object.
        :param new_access_token: The new JWT token as a string.
        :return: None
        """
        user.jwtToken = new_access_token
        if user.tokenExpiry is None:
            user.tokenExpiry = datetime.utcnow()
        user.tokenExpiry += timedelta(days=1)
        db.session.commit()

    @staticmethod
    def refresh_token(encoded_token: str) -> Tuple[Dict, int]:
        """
        Refresh the given JWT token if its expiration is within 24 hours.

        :param encoded_token: The encoded JWT token as a string.
        :return: A tuple containing a response dictionary and a status code.
        """
        decoded_token, error = UniversalService.decode_jwt_token(encoded_token)
        if error:
            return error, 400

        email = decoded_token["sub"]
        user = UniversalService.user_exists(email)
        expiration = datetime.utcfromtimestamp(decoded_token["exp"])
        logger.info(f"Token expiration: {expiration}")

        if not user:
            return {"message": "User not found", "success": False}, 404

        if not UniversalService.is_within_24_hours(decoded_token):
            return {"message": "Token expiration is already greater than 24 hours, cannot refresh", "success": False}, 400

        new_access_token = UniversalService.generate_token(email)
        UniversalService.update_user_token(user, new_access_token)

        return {"message": "Token refreshed successfully", "success": True, "token": new_access_token}, 200

