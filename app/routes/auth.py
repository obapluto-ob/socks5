from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app.models import Admin
from app.schemas import LoginSchema
from marshmallow import ValidationError

auth_bp = Blueprint("auth", __name__)
login_schema = LoginSchema()

@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = login_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    admin = Admin.query.filter_by(username=data["username"]).first()
    if not admin or not admin.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(admin.id))
    return jsonify({"access_token": token}), 200
