from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app import db
from app.models import ProxyUser, ConnectionLog, BlockedIP, SystemEvent
from app.schemas import ProxyUserSchema, ConnectionLogSchema, BlockedIPSchema, SystemEventSchema
from scripts.sync_dante_users import sync_dante
from scripts.credentials import generate_username, generate_password, assign_port, save_password_history

users_bp = Blueprint("users", __name__)
user_schema = ProxyUserSchema()
users_schema = ProxyUserSchema(many=True)
log_schema = ConnectionLogSchema(many=True)
blocked_schema = BlockedIPSchema(many=True)
events_schema = SystemEventSchema(many=True)


@users_bp.route("/", methods=["GET"])
@jwt_required()
def list_users():
    return jsonify(users_schema.dump(ProxyUser.query.all())), 200


@users_bp.route("/", methods=["POST"])
@jwt_required()
def create_user():
    username = generate_username()
    port = assign_port()
    password = generate_password()

    user = ProxyUser(username=username, password=password, port=port)
    db.session.add(user)
    db.session.flush()
    save_password_history(user.id, password)
    db.session.commit()
    sync_dante()

    public_ip = _get_public_ip()
    return jsonify({
        **user_schema.dump(user),
        "proxy_string": f"{username}:{password}@{public_ip}:{port}"
    }), 201


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
    return jsonify(blocked_schema.dump(BlockedIP.query.order_by(BlockedIP.blocked_at.desc()).all())), 200


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


def _get_public_ip():
    try:
        import requests
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "YOUR_PUBLIC_IP"
