import re
import time
import threading
from datetime import datetime
from collections import defaultdict
from flask import current_app

# tracks username -> set of active client IPs
active_connections = defaultdict(set)
failed_auth_attempts = defaultdict(int)  # ip -> count
_monitor_thread = None
_lock = threading.Lock()

FAILED_AUTH_LIMIT = 5  # block IP after this many failed auths


def start_monitor(app):
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _monitor_thread = threading.Thread(target=_watch_log, args=(app,), daemon=True)
    _monitor_thread.start()


def _watch_log(app):
    from config import Config
    log_path = Config.DANTE_LOG

    with app.app_context():
        # wait for log file to exist
        while not _file_exists(log_path):
            time.sleep(3)

        with open(log_path, "r") as f:
            f.seek(0, 2)  # go to end of file
            while True:
                line = f.readline()
                if line:
                    _process_line(line.strip(), app)
                else:
                    time.sleep(0.5)


def _file_exists(path):
    import os
    return os.path.exists(path)


def _process_line(line, app):
    """Parse Dante log lines and react to events."""
    from app.models import ProxyUser, ConnectionLog, BlockedIP, SystemEvent
    from app import db, socketio
    from scripts.rotate_credentials import rotate_user_credentials

    # Dante log formats:
    # socks connect: username/tcp ... -> ip.ip.ip.ip
    # socks disconnect: username ...
    # socks-rules denied: ... from ip

    connect_match = re.search(r'socks connect.*?(\w+)/tcp.*?(\d+\.\d+\.\d+\.\d+)', line)
    disconnect_match = re.search(r'socks disconnect.*?(\w+)/tcp.*?(\d+\.\d+\.\d+\.\d+)', line)
    auth_fail_match = re.search(r'(denied|rejected).*?(\d+\.\d+\.\d+\.\d+)', line, re.IGNORECASE)

    with app.app_context():
        if connect_match:
            username = connect_match.group(1)
            client_ip = connect_match.group(2)
            _handle_connect(username, client_ip, app)

        elif disconnect_match:
            username = disconnect_match.group(1)
            client_ip = disconnect_match.group(2)
            _handle_disconnect(username, client_ip, app)

        elif auth_fail_match:
            client_ip = auth_fail_match.group(2)
            _handle_failed_auth(client_ip, app)


def _handle_connect(username, client_ip, app):
    from app.models import ProxyUser, ConnectionLog, SystemEvent
    from app import db, socketio
    from scripts.rotate_credentials import rotate_user_credentials
    from flask import current_app

    with _lock:
        active_connections[username].add(client_ip)
        count = len(active_connections[username])

    user = ProxyUser.query.filter_by(username=username).first()
    if not user:
        return

    # log connection
    log = ConnectionLog(user_id=user.id, client_ip=client_ip, connected_at=datetime.utcnow())
    db.session.add(log)

    event_msg = f"User '{username}' connected from {client_ip} ({count} active connection(s))"
    _log_event("connect", event_msg, app)

    socketio.emit("connection_update", {
        "type": "connect",
        "username": username,
        "client_ip": client_ip,
        "active_count": count
    })

    # security: if 2+ simultaneous connections → rotate credentials
    if count >= current_app.config["MAX_CONNECTIONS_PER_USER"]:
        msg = f"SECURITY: {username} has {count} connections — rotating credentials and kicking all sessions"
        _log_event("rotation", msg, app)
        socketio.emit("security_alert", {"message": msg, "username": username})
        rotate_user_credentials(username, app)

    db.session.commit()


def _handle_disconnect(username, client_ip, app):
    from app.models import ConnectionLog
    from app import db, socketio

    with _lock:
        active_connections[username].discard(client_ip)
        count = len(active_connections[username])

    # mark disconnect time
    log = ConnectionLog.query.filter_by(
        user_id=_get_user_id(username),
        client_ip=client_ip,
        disconnected_at=None
    ).order_by(ConnectionLog.connected_at.desc()).first()

    if log:
        log.disconnected_at = datetime.utcnow()
        db.session.commit()

    socketio.emit("connection_update", {
        "type": "disconnect",
        "username": username,
        "client_ip": client_ip,
        "active_count": count
    })


def _handle_failed_auth(client_ip, app):
    from app.models import BlockedIP, SystemEvent
    from app import db, socketio

    with _lock:
        failed_auth_attempts[client_ip] += 1
        count = failed_auth_attempts[client_ip]

    if count >= FAILED_AUTH_LIMIT:
        existing = BlockedIP.query.filter_by(ip_address=client_ip).first()
        if not existing:
            blocked = BlockedIP(ip_address=client_ip, reason=f"Too many failed auth attempts ({count})")
            db.session.add(blocked)
            db.session.commit()
            msg = f"BLOCKED IP {client_ip} after {count} failed auth attempts"
            _log_event("block", msg, app)
            socketio.emit("security_alert", {"message": msg, "ip": client_ip})


def _log_event(event_type, message, app):
    from app.models import SystemEvent
    from app import db
    print(f"[MONITOR] {message}")
    event = SystemEvent(event_type=event_type, message=message)
    db.session.add(event)
    db.session.commit()


def _get_user_id(username):
    from app.models import ProxyUser
    user = ProxyUser.query.filter_by(username=username).first()
    return user.id if user else None


def get_active_connections():
    with _lock:
        return {k: list(v) for k, v in active_connections.items()}
