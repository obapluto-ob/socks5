"""
Pure Python SOCKS5 server — replaces Dante on Windows.
Reads users from PostgreSQL via Flask app context.
"""
import socket
import threading
import struct
import os
from dotenv import load_dotenv

load_dotenv()

HOST = "0.0.0.0"
PORT = int(os.getenv("PROXY_PORT", 10800))

# SOCKS5 constants
VER = 0x05
AUTH_USER_PASS = 0x02
AUTH_NONE = 0x00
AUTH_NO_ACCEPTABLE = 0xFF
CMD_CONNECT = 0x01
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04
REP_SUCCESS = 0x00
REP_FAILURE = 0x01


def get_active_users():
    """Load active users from DB."""
    try:
        from app import create_app
        from app.models import ProxyUser
        app = create_app()
        with app.app_context():
            users = ProxyUser.query.filter_by(is_active=True).all()
            return {u.username: u.password for u in users}
    except Exception as e:
        print(f"[socks5] DB error: {e}")
        return {}


def authenticate(username, password):
    users = get_active_users()
    return users.get(username) == password


def handle_client(conn, addr):
    try:
        # Greeting
        data = conn.recv(2)
        if len(data) < 2 or data[0] != VER:
            conn.close()
            return
        nmethods = data[1]
        methods = conn.recv(nmethods)

        # Require username/password auth
        conn.sendall(bytes([VER, AUTH_USER_PASS]))

        # Auth subnegotiation
        ver = conn.recv(1)[0]
        ulen = conn.recv(1)[0]
        username = conn.recv(ulen).decode()
        plen = conn.recv(1)[0]
        password = conn.recv(plen).decode()

        if not authenticate(username, password):
            conn.sendall(bytes([0x01, 0x01]))  # auth failed
            conn.close()
            return

        conn.sendall(bytes([0x01, 0x00]))  # auth success

        # Request
        header = conn.recv(4)
        if header[1] != CMD_CONNECT:
            conn.sendall(bytes([VER, REP_FAILURE, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
            conn.close()
            return

        atyp = header[3]
        if atyp == ATYP_IPV4:
            dst_addr = socket.inet_ntoa(conn.recv(4))
        elif atyp == ATYP_DOMAIN:
            dlen = conn.recv(1)[0]
            dst_addr = conn.recv(dlen).decode()
        elif atyp == ATYP_IPV6:
            dst_addr = socket.inet_ntop(socket.AF_INET6, conn.recv(16))
        else:
            conn.close()
            return

        dst_port = struct.unpack(">H", conn.recv(2))[0]

        # Connect to destination
        try:
            remote = socket.create_connection((dst_addr, dst_port), timeout=10)
        except Exception:
            conn.sendall(bytes([VER, REP_FAILURE, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))
            conn.close()
            return

        # Success response
        conn.sendall(bytes([VER, REP_SUCCESS, 0x00, ATYP_IPV4, 0, 0, 0, 0, 0, 0]))

        # Relay traffic
        _relay(conn, remote)

    except Exception as e:
        pass
    finally:
        conn.close()


def _relay(client, remote):
    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            src.close()
            dst.close()

    t1 = threading.Thread(target=forward, args=(client, remote), daemon=True)
    t2 = threading.Thread(target=forward, args=(remote, client), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def start_socks5_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(100)
    print(f"[socks5] Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    start_socks5_server()
