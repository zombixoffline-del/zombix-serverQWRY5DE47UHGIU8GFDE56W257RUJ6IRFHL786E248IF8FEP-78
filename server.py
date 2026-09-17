import eventlet
eventlet.monkey_patch()

from flask import Flask, request
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# {sid: {"x":..., "y":..., "dir":..., "anim":..., "loc":..., "char":..., "bike":..., "name":..., "last_seen":...}}
players = {}

@socketio.on("connect")
def on_connect():
    print(f"[+] {request.sid} подключился. Всего: {len(players)}")

@socketio.on("register")
def handle_register(data):
    players[request.sid] = {
        "x": 0, "y": 0, "dir": "down", "anim": "idle",
        "loc": "home", "char": "fighter", "bike": False,
        "name": data.get("name", "Игрок"),
        "last_seen": time.time()
    }
    # Отправляем новому игроку список всех остальных
    others = {sid: {k: v for k, v in p.items() if k != "last_seen"} 
              for sid, p in players.items() if sid != request.sid}
    emit("all_players", others)

@socketio.on("state")
def handle_state(data):
    if request.sid not in players:
        return
    players[request.sid].update({
        "x": data.get("x", 0),
        "y": data.get("y", 0),
        "dir": data.get("dir", "down"),
        "anim": data.get("anim", "idle"),
        "loc": data.get("loc", "home"),
        "char": data.get("char", "fighter"),
        "bike": data.get("bike", False),
        "last_seen": time.time()
    })
    # Рассылаем всем ОСТАЛЬНЫМ игрокам
    state_out = {
        "sid": request.sid,
        "x": players[request.sid]["x"],
        "y": players[request.sid]["y"],
        "dir": players[request.sid]["dir"],
        "anim": players[request.sid]["anim"],
        "loc": players[request.sid]["loc"],
        "char": players[request.sid]["char"],
        "bike": players[request.sid]["bike"],
        "name": players[request.sid]["name"],
    }
    emit("player_update", state_out, broadcast=True, include_self=False)

@socketio.on("disconnect")
def on_disconnect():
    if request.sid in players:
        del players[request.sid]
    emit("player_left", {"sid": request.sid}, broadcast=True)
    print(f"[-] {request.sid} отключился. Всего: {len(players)}")

@socketio.on("ping_alive")
def handle_ping():
    if request.sid in players:
        players[request.sid]["last_seen"] = time.time()

# Чистим "мёртвых" игроков (не было пинга > 30 сек)
def cleanup_loop():
    while True:
        eventlet.sleep(15)
        now = time.time()
        dead = [sid for sid, p in players.items() if now - p.get("last_seen", 0) > 30]
        for sid in dead:
            del players[sid]
            socketio.emit("player_left", {"sid": sid})

eventlet.spawn(cleanup_loop)

@app.route("/")
def index():
    return f"Zombix Global Server. Players online: {len(players)}"

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
