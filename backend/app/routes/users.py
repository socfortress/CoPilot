# routes/users.py

from flask import Blueprint
from flask import jsonify
from flask import request

from app.services.users.universal import UniversalService

bp = Blueprint("users", __name__)


@bp.route("/register", methods=["POST"])
def register():
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400
    response, status_code = UniversalService.register_user(request.json)
    return jsonify(response), status_code


@bp.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400
    response, status_code = UniversalService.login_user(request.json)
    return jsonify(response), status_code

@bp.route("/refresh", methods=["POST"])
def refresh():
    # Fetch the token from the Authorization header
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"message": "Missing or malformed Authorization header", "success": False}), 400

    token = auth_header.split(" ")[1]
    response, status_code = UniversalService.refresh_token(token)

    return jsonify(response), status_code
