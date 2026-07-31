import os
import secrets
import string
import subprocess
from datetime import datetime


def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def rotate_user_credentials(username, app):
    """Generate new password for user, sync to Dante, emit new credentials via socket."""
    from app.models import ProxyUser, SystemEvent
    from app import db, socketio
    from scripts.sync_dante_users import sync_dante

    with app.app_context():
        user = ProxyUser.query.filter_by(username=username).first()
        if not user:
            return

        new_password = generate_password()
        user.password = new_password
        user.last_rotated = datetime.utcnow()
        db.session.commit()

        sync_dante()
        _kill_dante_connections(username)

        public_ip = _get_public_ip()
        proxy_port = app.config["PROXY_PORT"]
        proxy_string = f"{user.username}:{new_password}@{public_ip}:{proxy_port}"

        print("\n" + "=" * 55)
        print("  CREDENTIALS ROTATED — SEND THESE TO YOUR BROTHER")
        print("=" * 55)
        print(f"  {proxy_string}")
        print("=" * 55 + "\n")

        socketio.emit("credentials_rotated", {
            "username": user.username,
            "password": new_password,
            "proxy_string": proxy_string,
            "host": public_ip,
            "port": proxy_port,
            "rotated_at": user.last_rotated.isoformat()
        })


def _kill_dante_connections(username):
    """Reload Dante to drop all active connections."""
    try:
        subprocess.run(["pkill", "-HUP", "sockd"], check=False)
    except Exception:
        pass


def _get_public_ip():
    try:
        import requests
        return requests.get("https://api.ipify.org", timeout=5).text.strip()
    except Exception:
        return "YOUR_PUBLIC_IP"
