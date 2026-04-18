from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import pandas as pd
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

CSV_PATH = "traffic_data.csv"

def read_traffic_data():
    if not os.path.exists(CSV_PATH):
        return None

    df = pd.read_csv(CSV_PATH)
    if df.empty:
        return None

    hours = df["hour"].tolist() if "hour" in df.columns else list(range(len(df)))
    speeds = df["speed"].tolist()

    return {
        "labels": hours,
        "traffic": speeds
    }

def get_latest_speed():
    data = read_traffic_data()
    if not data:
        return None
    return data["traffic"][-1]  # latest speed value

def check_traffic_conditions():
    speed = get_latest_speed()
    if speed is None:
        return None
    if speed < 20:
        return f"🚨 Heavy congestion expected! Current speed: {speed} km/h"
    elif speed < 40:
        return f"⚠ Moderate traffic! Speed: {speed} km/h"
    return None

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/traffic-data")
def traffic_data():
    data = read_traffic_data()
    if data:
        return jsonify(data)
    return jsonify({"labels": [], "traffic": []})

def background_alerts():
    while True:
        alert = check_traffic_conditions()
        if alert:
            socketio.emit("traffic_alert", {"message": alert})
            print("Alert sent:", alert)
        socketio.sleep(5)

if __name__ == "__main__":
    socketio.start_background_task(background_alerts)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
