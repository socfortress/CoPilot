from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, get_jwt, decode_token, jwt_required
from app.models.users import Users

def check_jwt_in_db():
    """Check if JWT exists in the database and is valid."""
    current_user_identity = get_jwt_identity()  # Get identity email from current token
    user = Users.query.filter_by(usersEmail=current_user_identity).first()  # Fetch user from DB

    if not user:
        return jsonify({"message": "User not found", "success": False}), 404

    # Extract the token from the current request
    current_token = get_jwt()['jti']  # 'jti' is the unique identifier for a JWT

    # Decode the stored token to get its JTI
    decoded_stored_token = decode_token(user.jwtToken)
    stored_jti = decoded_stored_token['jti']

    if stored_jti != current_token:
        return jsonify({"message": "Token mismatch", "success": False}), 401

    return None  # Return None if everything is fine

def jwt_db_check(fn):
    """Decorator to check JWT against the database."""
    @wraps(fn)
    @jwt_required()  # First ensure that a valid JWT token is present
    def wrapper(*args, **kwargs):
        response = check_jwt_in_db()
        if response:
            return response
        return fn(*args, **kwargs)
    return wrapper
