from app import db
from datetime import datetime
import bcrypt

class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())


class ProxyUser(db.Model):
    __tablename__ = "proxy_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_rotated = db.Column(db.DateTime, nullable=True)
    connections = db.relationship("ConnectionLog", backref="user", lazy=True, cascade="all, delete-orphan")
    password_history = db.relationship("PasswordHistory", backref="user", lazy=True, cascade="all, delete-orphan")


class PasswordHistory(db.Model):
    __tablename__ = "password_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("proxy_users.id"), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.utcnow)


class ConnectionLog(db.Model):
    __tablename__ = "connection_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("proxy_users.id"), nullable=False)
    client_ip = db.Column(db.String(50))
    connected_at = db.Column(db.DateTime, default=datetime.utcnow)
    disconnected_at = db.Column(db.DateTime, nullable=True)
    bytes_sent = db.Column(db.BigInteger, default=0)
    bytes_received = db.Column(db.BigInteger, default=0)
    was_kicked = db.Column(db.Boolean, default=False)


class BlockedIP(db.Model):
    __tablename__ = "blocked_ips"
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), unique=True, nullable=False)
    reason = db.Column(db.String(255))
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)


class SystemEvent(db.Model):
    __tablename__ = "system_events"
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50))  # rotation, block, connect, disconnect
    message = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
