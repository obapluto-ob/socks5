import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

DANTE_PASSWD = os.getenv("DANTE_PASSWD", "C:/dante/sockd.passwd")


def sync_dante():
    from app.models import ProxyUser
    from app import db

    users = ProxyUser.query.filter_by(is_active=True).all()

    os.makedirs(os.path.dirname(DANTE_PASSWD), exist_ok=True)
    with open(DANTE_PASSWD, "w") as f:
        for user in users:
            f.write(f"{user.username}:{user.password}\n")

    try:
        subprocess.run(["pkill", "-HUP", "sockd"], check=False)
    except Exception as e:
        print(f"[sync_dante] Could not reload Dante: {e}")

    print(f"[sync_dante] Synced {len(users)} active users.")
