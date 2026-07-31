import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

DANTE_PASSWD = os.getenv("DANTE_PASSWD", "/etc/sockd.passwd")


def sync_dante():
    from app.models import ProxyUser

    users = ProxyUser.query.filter_by(is_active=True).all()

    # Create/update system users for Dante authentication
    for user in users:
        _ensure_system_user(user.username, user.password)

    # Remove system users that are no longer in DB or are disabled
    _cleanup_system_users(users)

    try:
        subprocess.run(["sudo", "systemctl", "reload", "danted"], check=False)
    except Exception as e:
        print(f"[sync_dante] Could not reload Dante: {e}")

    print(f"[sync_dante] Synced {len(users)} active users.")


def _ensure_system_user(username, password):
    result = subprocess.run(["id", username], capture_output=True)
    if result.returncode != 0:
        subprocess.run([
            "sudo", "useradd", "-M", "-s", "/usr/sbin/nologin", username
        ], check=False)
    proc = subprocess.Popen(["sudo", "chpasswd"], stdin=subprocess.PIPE)
    proc.communicate(input=f"{username}:{password}".encode())


def _cleanup_system_users(active_users):
    active_names = {u.username for u in active_users}
    if not os.path.exists(DANTE_PASSWD):
        return
    with open(DANTE_PASSWD, "r") as f:
        managed = {line.strip() for line in f if line.strip()}
    for username in managed - active_names:
        subprocess.run(["sudo", "userdel", username], check=False)
    with open(DANTE_PASSWD, "w") as f:
        for name in active_names:
            f.write(f"{name}\n")

