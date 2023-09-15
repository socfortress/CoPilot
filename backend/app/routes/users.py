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
