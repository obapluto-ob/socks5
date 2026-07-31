from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(dashboard_bp, url_prefix="/")

    return app
