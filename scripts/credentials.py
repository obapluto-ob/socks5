import secrets
import string

BASE_USERNAME = "emonigatsaucee"
PORT_START = 10800
PORT_END = 19999


def generate_username():
    return BASE_USERNAME


def generate_password(user_id=None):
    from app.models import PasswordHistory
    alphabet = string.ascii_letters + string.digits
    for _ in range(100):
        password = "".join(secrets.choice(alphabet) for _ in range(4))
        if user_id:
            already_used = PasswordHistory.query.filter_by(
                user_id=user_id, password=password
            ).first()
            if already_used:
                continue
        return password
    raise RuntimeError("Could not generate unique password after 100 attempts")


def assign_port():
    from app.models import ProxyUser
    used_ports = {u.port for u in ProxyUser.query.with_entities(ProxyUser.port).all()}
    for port in range(PORT_START, PORT_END + 1):
        if port not in used_ports:
            return port
    raise RuntimeError("No available ports in range")


def save_password_history(user_id, password):
    from app.models import PasswordHistory
    from app import db
    history = PasswordHistory(user_id=user_id, password=password)
    db.session.add(history)
    db.session.commit()
