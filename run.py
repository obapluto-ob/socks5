from app import create_app, socketio
from app.monitor import start_monitor

app = create_app()

if __name__ == "__main__":
    start_monitor(app)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
