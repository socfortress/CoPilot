import bcrypt
from datetime import datetime, timedelta
from app.models.users import Users
from app import db
from flask_jwt_extended import create_access_token

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
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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
            passwordHash=hashed_password
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

        if not bcrypt.checkpw(password.encode('utf-8'), user.passwordHash.encode('utf-8')):
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
