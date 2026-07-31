import threading
from app import create_app, socketio
from app.monitor import start_monitor

app = create_app()

if __name__ == "__main__":
    # Start SOCKS5 server in background thread
    from socks5_server import start_socks5_server
    socks_thread = threading.Thread(target=start_socks5_server, daemon=True)
    socks_thread.start()

    # Start connection monitor
    start_monitor(app)

    # Start Flask
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
