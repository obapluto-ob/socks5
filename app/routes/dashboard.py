from flask import Blueprint, render_template, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.models import ProxyUser, SystemEvent, BlockedIP
from app.schemas import ProxyUserSchema, SystemEventSchema
from app.monitor import get_active_connections
from scripts.rotate_credentials import _get_public_ip

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@dashboard_bp.route("/api/dashboard/stats")
@jwt_required()
def stats():
    users = ProxyUser.query.all()
    active = get_active_connections()
    events = SystemEvent.query.order_by(SystemEvent.created_at.desc()).limit(20).all()
    blocked = BlockedIP.query.count()
    public_ip = _get_public_ip()
    port = current_app.config["PROXY_PORT"]

    proxy_users_data = []
    for u in users:
        proxy_users_data.append({
            "id": u.id,
            "username": u.username,
            "is_active": u.is_active,
            "active_connections": len(active.get(u.username, [])),
            "connected_ips": active.get(u.username, []),
            "last_rotated": u.last_rotated.isoformat() if u.last_rotated else None,
            "proxy_string": f"{u.username}:{u.password}@{public_ip}:{port}"
        })

    return jsonify({
        "public_ip": public_ip,
        "port": port,
        "total_users": len(users),
        "blocked_ips": blocked,
        "proxy_users": proxy_users_data,
        "recent_events": SystemEventSchema(many=True).dump(events)
    }), 200
