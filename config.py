import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/socks5db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-change-this")
    DANTE_LOG = os.getenv("DANTE_LOG", "C:/dante/logs/sockd.log")
    DANTE_CONF = os.getenv("DANTE_CONF", "C:/dante/sockd.conf")
    DANTE_PASSWD = os.getenv("DANTE_PASSWD", "C:/dante/sockd.passwd")
    PROXY_PORT = int(os.getenv("PROXY_PORT", 10800))
    MAX_CONNECTIONS_PER_USER = int(os.getenv("MAX_CONNECTIONS_PER_USER", 2))
