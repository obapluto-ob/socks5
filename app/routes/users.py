from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models import ProxyUser, ConnectionLog, BlockedIP, SystemEvent
from app.schemas import ProxyUserSchema, ConnectionLogSchema, BlockedIPSchema, SystemEventSchema
from marshmallow import ValidationError
from scripts.sync_dante_users import sync_dante

users_bp = Blueprint("users", __name__)
user_schema = ProxyUserSchema()
users_schema = ProxyUserSchema(many=True)
log_schema = ConnectionLogSchema(many=True)
blocked_schema = BlockedIPSchema(many=True)
events_schema = SystemEventSchema(many=True)

@users_bp.route("/", methods=["GET"])
@jwt_required()
def list_users():
    users = ProxyUser.query.all()
    return jsonify(users_schema.dump(users)), 200

@users_bp.route("/", methods=["POST"])
@jwt_required()
def create_user():
    try:
        data = user_schema.load(request.get_json())
    except ValidationError as e:
        return jsonify({"errors": e.messages}), 400

    if ProxyUser.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409

    user = ProxyUser(username=data["username"], password=data["password"])
    db.session.add(user)
    db.session.commit()
    sync_dante()
    return jsonify(user_schema.dump(user)), 201

@users_bp.route("/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    user = ProxyUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    sync_dante()
    return jsonify({"message": f"User {user.username} deleted"}), 200

@users_bp.route("/<int:user_id>/toggle", methods=["PATCH"])
@jwt_required()
def toggle_user(user_id):
    user = ProxyUser.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    sync_dante()
    return jsonify(user_schema.dump(user)), 200

@users_bp.route("/<int:user_id>/rotate", methods=["POST"])
@jwt_required()
def rotate_user(user_id):
    from flask import current_app
    from scripts.rotate_credentials import rotate_user_credentials
    user = ProxyUser.query.get_or_404(user_id)
    rotate_user_credentials(user.username, current_app._get_current_object())
    return jsonify({"message": f"Credentials rotated for {user.username}"}), 200

@users_bp.route("/<int:user_id>/logs", methods=["GET"])
@jwt_required()
def user_logs(user_id):
    logs = ConnectionLog.query.filter_by(user_id=user_id).order_by(ConnectionLog.connected_at.desc()).limit(50).all()
    return jsonify(log_schema.dump(logs)), 200

@users_bp.route("/blocked", methods=["GET"])
@jwt_required()
def blocked_ips():
    blocked = BlockedIP.query.order_by(BlockedIP.blocked_at.desc()).all()
    return jsonify(blocked_schema.dump(blocked)), 200

@users_bp.route("/blocked/<int:block_id>", methods=["DELETE"])
@jwt_required()
def unblock_ip(block_id):
    blocked = BlockedIP.query.get_or_404(block_id)
    db.session.delete(blocked)
    db.session.commit()
    return jsonify({"message": f"IP {blocked.ip_address} unblocked"}), 200

@users_bp.route("/events", methods=["GET"])
@jwt_required()
def system_events():
    events = SystemEvent.query.order_by(SystemEvent.created_at.desc()).limit(100).all()
    return jsonify(events_schema.dump(events)), 200
