import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, join_room, emit
import random
import string

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

rooms = {}

def generate_room_code():
    return "".join(random.choices(string.ascii_uppercase, k=4))

@socketio.on("create_room")
def handle_create_room():
    code = generate_room_code()
    while code in rooms:
        code = generate_room_code()
    rooms[code] = [request.sid]
    join_room(code)
    emit("room_created", {"code": code})

@socketio.on("join_room_req")
def handle_join_room(data):
    code = data.get("code", "").upper().strip()
    if code in rooms and len(rooms[code]) < 2:
        rooms[code].append(request.sid)
        join_room(code)
        emit("room_joined", {"ok": True, "code": code})
        emit("partner_joined", room=code, include_self=False)
    else:
        emit("room_joined", {"ok": False, "error": "Комната не найдена"})

@socketio.on("state")
def handle_state(data):
    code = data.get("room")
    if code and code in rooms:
        emit("partner_state", data, room=code, include_self=False)

@socketio.on("disconnect")
def handle_disconnect():
    for code, sids in list(rooms.items()):
        if request.sid in sids:
            sids.remove(request.sid)
            if not sids:
                del rooms[code]
            else:
                emit("partner_left", room=code)
            break

@app.route("/")
def index():
    return "Zombix Online Server is running!"

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
