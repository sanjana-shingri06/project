from flask import Flask, render_template, request, jsonify, Response, url_for
import io
import traceback
import sqlite3
import time
import json
import threading
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit, join_room, leave_room
from traffic_analysis import (
    fetch_traffic_data, get_latest_traffic, analyze_peak_hours, plot_traffic,
    traffic_summary, traffic_by_weekday, plot_weekday_trends, plot_heatmap,
    load_model, predict_traffic
)
import random

app = Flask(__name__)
app.secret_key = 'traffic_flow_secret_key'

# Socket.IO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', 
                   ping_timeout=60, ping_interval=25)

# ==========================================
# DATABASE INITIALIZATION WITH MIGRATION
# ==========================================
def init_db():
    """Initialize SQLite database with enhanced schema"""
    conn = sqlite3.connect('traffic.db')
    cur = conn.cursor()
    
    # Check if traffic_alerts table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_alerts'")
    table_exists = cur.fetchone()
    
    if not table_exists:
        # Create traffic_alerts table
        cur.execute('''
            CREATE TABLE traffic_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                road TEXT NOT NULL,
                severity TEXT,
                lat REAL,
                lng REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                congestion_level INTEGER,
                vehicle_count INTEGER,
                incident_type TEXT
            )
        ''')
        print("[OK] Created traffic_alerts table")
    else:
        # Check and add missing columns
        cur.execute("PRAGMA table_info(traffic_alerts)")
        columns = [row[1] for row in cur.fetchall()]
        
        for col_name in ['lat', 'lng', 'congestion_level', 'vehicle_count', 'incident_type']:
            if col_name not in columns:
                try:
                    col_type = 'REAL' if col_name in ['lat', 'lng'] else 'INTEGER' if col_name == 'vehicle_count' else 'TEXT'
                    cur.execute(f"ALTER TABLE traffic_alerts ADD COLUMN {col_name} {col_type}")
                    print(f"[OK] Added {col_name} column to traffic_alerts")
                except Exception as e:
                    print(f"[WARNING] Could not add {col_name} column: {e}")
    
    # Create traffic_data table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road TEXT,
            vehicle_count INTEGER,
            timestamp DATETIME,
            congestion_level INTEGER,
            speed REAL,
            incidents INTEGER
        )
    ''')
    
    # Create real-time updates table for tracking
    cur.execute('''
        CREATE TABLE IF NOT EXISTS traffic_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road TEXT,
            vehicle_count INTEGER,
            congestion_level INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            speed REAL
        )
    ''')
    
    # Create incident reports table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_type TEXT,
            location TEXT,
            lat REAL,
            lng REAL,
            severity TEXT,
            description TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

# Road coordinates mapping with more details
ROAD_COORDS = {
    "Main Street": {"lat": 37.7749, "lng": -122.4194, "speed_limit": 35},
    "Broadway": {"lat": 37.7793, "lng": -122.4192, "speed_limit": 30},
    "Market Street": {"lat": 37.7937, "lng": -122.3965, "speed_limit": 25},
    "Central Ave": {"lat": 37.7689, "lng": -122.4313, "speed_limit": 40},
    "Sunset Blvd": {"lat": 37.7622, "lng": -122.4696, "speed_limit": 45},
    "5th Avenue": {"lat": 37.7850, "lng": -122.4080, "speed_limit": 35},
    "Park Street": {"lat": 37.7915, "lng": -122.3970, "speed_limit": 30},
    "Bay Street": {"lat": 37.7780, "lng": -122.4120, "speed_limit": 35},
}

INCIDENT_TYPES = ["Accident", "Construction", "Breakdown", "Congestion", "Weather", "Event"]

def calculate_congestion_level(vehicle_count):
    """Calculate congestion level (0-100) based on vehicle count"""
    if vehicle_count < 50:
        return 10
    elif vehicle_count < 100:
        return 30
    elif vehicle_count < 200:
        return 50
    elif vehicle_count < 300:
        return 70
    else:
        return 100

def determine_severity(congestion_level):
    """Determine severity based on congestion level"""
    if congestion_level >= 70:
        return "high"
    elif congestion_level >= 40:
        return "medium"
    else:
        return "low"

def get_alerts_with_traffic(limit=20):
    """Fetch alerts with traffic data and coordinates"""
    try:
        conn = sqlite3.connect('traffic.db')
        cur = conn.cursor()
        cur.execute('''
            SELECT id, road, severity, lat, lng, timestamp, congestion_level, vehicle_count, incident_type
            FROM traffic_alerts 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = cur.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            _id, road, severity, lat, lng, ts, congestion, vcount, incident_type = row
            if not lat or not lng:
                if road in ROAD_COORDS:
                    lat = ROAD_COORDS[road]["lat"]
                    lng = ROAD_COORDS[road]["lng"]
            alerts.append({
                'id': _id,
                'road': road,
                'severity': severity,
                'lat': lat,
                'lng': lng,
                'timestamp': ts,
                'congestion_level': congestion or 0,
                'vehicle_count': vcount or 0,
                'incident_type': incident_type or 'Traffic'
            })
        return list(reversed(alerts))
    except Exception as e:
        print(f"[ERROR] Failed to fetch alerts: {e}")
        return []

def get_real_time_updates(limit=50):
    """Fetch recent real-time traffic updates"""
    try:
        conn = sqlite3.connect('traffic.db')
        cur = conn.cursor()
        cur.execute('''
            SELECT road, vehicle_count, congestion_level, timestamp, speed
            FROM traffic_updates 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = cur.fetchall()
        conn.close()
        
        updates = []
        for road, vcount, congestion, ts, speed in rows:
            updates.append({
                'road': road,
                'vehicle_count': vcount,
                'congestion_level': congestion,
                'timestamp': ts,
                'speed': speed or 0
            })
        return updates
    except Exception as e:
        print(f"[ERROR] Failed to fetch real-time updates: {e}")
        return []

def broadcast_alert(alert_data):
    """Broadcast new alert to all connected clients"""
    try:
        socketio.emit('new_alert', alert_data, broadcast=True, namespace='/')
        print(f"[INFO] Alert broadcasted: {alert_data['road']}")
    except Exception as e:
        print(f"[ERROR] Broadcast failed: {e}")

def broadcast_real_time_update(update_data):
    """Broadcast real-time traffic update"""
    try:
        socketio.emit('realtime_update', update_data, broadcast=True, namespace='/')
    except Exception as e:
        print(f"[ERROR] Real-time broadcast failed: {e}")

# ==========================================
# Load ML Model
# ==========================================
try:
    model = load_model()
    MODEL_READY = model is not None
    print("[OK] Model loaded from data/traffic_model.pkl")
except Exception as e:
    model = None
    MODEL_READY = False
    print(f"[WARNING] Model failed to load: {e}")

# ==========================================
# ROUTES
# ==========================================

@app.route("/")
def home():
    """Home page: show latest traffic, peak hours, hourly chart, and alerts"""
    try:
        df = fetch_traffic_data()
        latest_ts, latest_val = get_latest_traffic(df)
        hourly_avg, peak_hours = analyze_peak_hours(df)
        
        plot_traffic(hourly_avg)
        summary = traffic_summary(df) if df is not None and not df.empty else {}
        peak_hours_str = ', '.join(f"{h}:00" for h in peak_hours) if peak_hours else "N/A"
        alerts = get_alerts_with_traffic(limit=10)
        
        return render_template(
            "index.html",
            latest_ts=latest_ts or "N/A",
            latest_val=latest_val or "N/A",
            peak_hours=peak_hours_str,
            plot_filename="plots/traffic_plot.png",
            summary=summary,
            alerts=alerts,
            total_alerts=len(alerts)
        )
    except Exception as e:
        print(f"[ERROR] Error in home route: {e}")
        traceback.print_exc()
        return render_template(
            "index.html",
            latest_ts="Error loading data",
            latest_val="N/A",
            peak_hours="N/A",
            plot_filename="",
            summary={},
            alerts=[],
            total_alerts=0
        )

@app.route("/test")
def test():
    """Simple test route"""
    return "<h1>Server is Running!</h1><p>Go to <a href='/'>Home</a> or <a href='/map'>Map</a> or <a href='/live'>Live</a></p>"

@app.route("/map")
def traffic_map():
    """Display traffic map with real-time alerts"""
    alerts = get_alerts_with_traffic(limit=20)
    return render_template('map.html', alerts=alerts)

@app.route("/live")
def live_tracking():
    """Real-time live traffic tracking dashboard"""
    roads = list(ROAD_COORDS.keys())
    return render_template('live.html', roads=roads)

@app.route("/dashboard")
def dashboard():
    """Dashboard page: summary, weekday chart, heatmap, and alerts"""
    try:
        df = fetch_traffic_data()
        summary = traffic_summary(df) if df is not None and not df.empty else {}
        weekday_avg = traffic_by_weekday(df)
        plot_weekday_trends(weekday_avg)
        plot_heatmap(df)
        alerts = get_alerts_with_traffic(limit=20)
        
        return render_template(
            "dashboard.html",
            summary=summary,
            weekday_plot="plots/weekday_plot.png",
            heatmap_plot="plots/heatmap.png",
            alerts=alerts,
            total_alerts=len(alerts)
        )
    except Exception as e:
        print(f"[ERROR] Error generating dashboard: {e}")
        traceback.print_exc()
        return render_template(
            "dashboard.html",
            summary={},
            weekday_plot="",
            heatmap_plot="",
            alerts=[],
            total_alerts=0
        ), 500

@app.route("/predict", methods=["GET", "POST"])
def predict():
    """Predict page: user selects hour/day and gets predicted traffic"""
    weather_options = ["Clear", "Clouds", "Rain", "Snow", "Mist", "Fog"]

    if request.method == "POST":
        if not MODEL_READY:
            return jsonify({"error": "Model not loaded"}), 500

        try:
            data = request.get_json(force=True)
            time_val = data.get("time")
            day_of_week = int(data.get("day_of_week", 0))

            if not time_val:
                return jsonify({"error": "time is required (HH:MM)"}), 400

            hour = int(time_val.split(":")[0])
            features = [hour, day_of_week]
            pred_value = predict_traffic(model, features)

            df = fetch_traffic_data()
            avg_count = round(df["vehicle_count"].mean(), 2) if df is not None and not df.empty else None

            return jsonify({
                "prediction": pred_value,
                "average": avg_count,
                "message": f"Predicted traffic: {pred_value} vehicles. Dataset average: {avg_count}."
            })
        except Exception as e:
            print(f"[ERROR] Prediction error: {e}")
            return jsonify({"error": str(e)}), 500

    return render_template("predict.html", weather_options=weather_options)

@app.route("/download/data")
def download_data():
    """Download full traffic dataset as CSV."""
    try:
        df = fetch_traffic_data().reset_index()
        csv_bytes = io.StringIO()
        df.to_csv(csv_bytes, index=False)
        csv_bytes.seek(0)
        return Response(
            csv_bytes.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=traffic_data.csv"}
        )
    except Exception as e:
        return Response(f"Error exporting data: {e}", status=500)

# ==========================================
# API ENDPOINTS
# ==========================================

@app.route('/api/traffic-stats', methods=['GET'])
def get_traffic_stats():
    """API endpoint to get comprehensive traffic statistics"""
    try:
        df = fetch_traffic_data()
        summary = traffic_summary(df) if df is not None and not df.empty else {}
        alerts = get_alerts_with_traffic(limit=20)
        
        total_vehicles = int(df['vehicle_count'].sum()) if df is not None and not df.empty else 0
        avg_vehicles = float(df['vehicle_count'].mean()) if df is not None and not df.empty else 0
        peak_hour = int(df['hour'].mode()[0]) if df is not None and not df.empty and len(df['hour'].mode()) > 0 else 0
        
        stats = {
            'total_vehicles': total_vehicles,
            'average_vehicles': round(avg_vehicles, 2),
            'peak_hour': peak_hour,
            'total_alerts': len(alerts),
            'high_severity_alerts': len([a for a in alerts if a['severity'] == 'high']),
            'medium_severity_alerts': len([a for a in alerts if a['severity'] == 'medium']),
            'low_severity_alerts': len([a for a in alerts if a['severity'] == 'low']),
            'alerts': alerts,
            'summary': summary
        }
        return jsonify(stats)
    except Exception as e:
        print(f"[ERROR] Error in traffic stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/create', methods=['POST'])
def create_alert():
    """Create a new alert with auto-severity calculation"""
    try:
        data = request.get_json(force=True)
        road = data.get('road')
        vehicle_count = data.get('vehicle_count', 150)
        incident_type = data.get('incident_type', 'Traffic')
        
        if not road:
            return jsonify({'error': 'road is required'}), 400
        
        # Get coordinates
        road_info = ROAD_COORDS.get(road, {})
        lat = road_info.get("lat")
        lng = road_info.get("lng")
        
        congestion = calculate_congestion_level(vehicle_count)
        severity = determine_severity(congestion)
        timestamp = datetime.now().isoformat()
        
        # Insert into database
        conn = sqlite3.connect('traffic.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO traffic_alerts 
            (road, severity, lat, lng, timestamp, congestion_level, vehicle_count, incident_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (road, severity, lat, lng, timestamp, congestion, vehicle_count, incident_type))
        conn.commit()
        alert_id = cur.lastrowid
        conn.close()
        
        alert = {
            'id': alert_id,
            'road': road,
            'severity': severity,
            'lat': lat,
            'lng': lng,
            'timestamp': timestamp,
            'congestion_level': congestion,
            'vehicle_count': vehicle_count,
            'incident_type': incident_type
        }
        
        broadcast_alert(alert)
        return jsonify(alert), 201
    except Exception as e:
        print(f"[ERROR] Error creating alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts with optional limit"""
    try:
        limit = request.args.get('limit', 20, type=int)
        alerts = get_alerts_with_traffic(limit=limit)
        return jsonify({'alerts': alerts, 'count': len(alerts)})
    except Exception as e:
        print(f"[ERROR] Error fetching alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/traffic-by-road', methods=['GET'])
def get_traffic_by_road():
    """Get traffic statistics by road"""
    try:
        df = fetch_traffic_data()
        if df is None or df.empty:
            return jsonify({'error': 'No data available'}), 404
        
        road_stats = df.groupby('road').agg({
            'vehicle_count': ['mean', 'max', 'min', 'count']
        }).round(2)
        
        result = []
        for road in road_stats.index:
            road_info = ROAD_COORDS.get(road, {})
            result.append({
                'road': road,
                'avg_vehicles': float(road_stats.loc[road, ('vehicle_count', 'mean')]),
                'max_vehicles': float(road_stats.loc[road, ('vehicle_count', 'max')]),
                'min_vehicles': float(road_stats.loc[road, ('vehicle_count', 'min')]),
                'records': int(road_stats.loc[road, ('vehicle_count', 'count')]),
                'speed_limit': road_info.get('speed_limit', 30)
            })
        
        return jsonify({'roads': result})
    except Exception as e:
        print(f"[ERROR] Error in traffic by road: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/realtime/updates', methods=['GET'])
def get_realtime_updates():
    """Get recent real-time updates"""
    try:
        limit = request.args.get('limit', 50, type=int)
        updates = get_real_time_updates(limit=limit)
        return jsonify({'updates': updates, 'count': len(updates)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/incident/report', methods=['POST'])
def report_incident():
    """Report a new traffic incident"""
    try:
        data = request.get_json(force=True)
        incident_type = data.get('incident_type', 'Other')
        location = data.get('location')
        lat = data.get('lat')
        lng = data.get('lng')
        description = data.get('description', '')
        severity = data.get('severity', 'medium')
        
        if not location:
            return jsonify({'error': 'location is required'}), 400
        
        conn = sqlite3.connect('traffic.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO incidents 
            (incident_type, location, lat, lng, severity, description, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (incident_type, location, lat, lng, severity, description, datetime.now().isoformat()))
        conn.commit()
        incident_id = cur.lastrowid
        conn.close()
        
        incident = {
            'id': incident_id,
            'incident_type': incident_type,
            'location': location,
            'lat': lat,
            'lng': lng,
            'severity': severity,
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('new_incident', incident, broadcast=True)
        return jsonify(incident), 201
    except Exception as e:
        print(f"[ERROR] Error reporting incident: {e}")
        return jsonify({'error': str(e)}), 500

# ==========================================
# SOCKET.IO EVENT HANDLERS
# ==========================================

@socketio.on('connect')
def handle_connect():
    """Send initial alerts to connected client"""
    try:
        alerts = get_alerts_with_traffic(limit=20)
        emit('initial_alerts', alerts)
        print(f"[INFO] Client {request.sid} connected")
    except Exception as e:
        print(f"[ERROR] Failed to send initial alerts: {e}")

@socketio.on('request_updates')
def handle_update_request():
    """Client requests latest traffic updates"""
    try:
        alerts = get_alerts_with_traffic(limit=10)
        emit('alerts_update', {'alerts': alerts, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        print(f"[ERROR] Update request failed: {e}")

@socketio.on('subscribe_road')
def handle_subscribe_road(data):
    """Subscribe to real-time updates for a specific road"""
    try:
        road = data.get('road')
        if road:
            join_room(road)
            emit('subscribed', {'road': road, 'message': f'Subscribed to {road}'})
            print(f"[INFO] Client subscribed to {road}")
    except Exception as e:
        print(f"[ERROR] Subscription failed: {e}")

@socketio.on('unsubscribe_road')
def handle_unsubscribe_road(data):
    """Unsubscribe from road updates"""
    try:
        road = data.get('road')
        if road:
            leave_room(road)
            emit('unsubscribed', {'road': road})
            print(f"[INFO] Client unsubscribed from {road}")
    except Exception as e:
        print(f"[ERROR] Unsubscribe failed: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    print(f"[INFO] Client {request.sid} disconnected")

# ==========================================
# BACKGROUND TASKS - REAL-TIME GENERATION
# ==========================================

def real_time_data_generator():
    """Generate realistic real-time traffic data"""
    while True:
        try:
            # Simulate real-time traffic data for each road
            for road in ROAD_COORDS.keys():
                vehicle_count = random.randint(30, 400)
                congestion = calculate_congestion_level(vehicle_count)
                severity = determine_severity(congestion)
                speed = max(5, ROAD_COORDS[road]["speed_limit"] - (congestion / 100) * 20)
                
                # Save to real-time updates table
                conn = sqlite3.connect('traffic.db')
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO traffic_updates 
                    (road, vehicle_count, congestion_level, speed)
                    VALUES (?, ?, ?, ?)
                ''', (road, vehicle_count, congestion, speed))
                conn.commit()
                conn.close()
                
                # Broadcast update
                road_info = ROAD_COORDS[road]
                update = {
                    'road': road,
                    'vehicle_count': vehicle_count,
                    'congestion_level': congestion,
                    'severity': severity,
                    'speed': round(speed, 2),
                    'lat': road_info['lat'],
                    'lng': road_info['lng'],
                    'timestamp': datetime.now().isoformat()
                }
                socketio.emit('realtime_update', update, broadcast=True)
                
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            print(f"[ERROR] Real-time generator error: {e}")
            time.sleep(10)

def alert_poller():
    """Poll database and broadcast new alerts"""
    last_alert_id = 0
    while True:
        try:
            conn = sqlite3.connect('traffic.db')
            cur = conn.cursor()
            cur.execute('SELECT id FROM traffic_alerts ORDER BY id DESC LIMIT 1')
            result = cur.fetchone()
            conn.close()
            
            if result:
                latest_id = result[0]
                if latest_id > last_alert_id:
                    alerts = get_alerts_with_traffic(limit=5)
                    for alert in alerts:
                        if alert['id'] > last_alert_id:
                            broadcast_alert(alert)
                    last_alert_id = latest_id
            
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] Alert poller error: {e}")
            time.sleep(5)

# ==========================================
# MAIN APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import socket
    
    def find_available_port(start_port=5000, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                continue
        return None
    
    # Initialize database
    init_db()
    
    # Find available port
    PORT = find_available_port(5000)
    if not PORT:
        print("[ERROR] No available ports found between 5000-5009")
        exit(1)
    
    print(f"[SUCCESS] Starting Enhanced Traffic Flow App on http://127.0.0.1:{PORT}/")
    
    # Start background tasks
    try:
        socketio.start_background_task(real_time_data_generator)
        print("[INFO] Real-time data generator started")
    except Exception as e:
        print(f"[WARNING] Using threading for data generator: {e}")
        t = threading.Thread(target=real_time_data_generator, daemon=True)
        t.start()

    try:
        socketio.start_background_task(alert_poller)
        print("[INFO] Alert poller started")
    except Exception as e:
        print(f"[WARNING] Using threading for alert poller: {e}")
        t = threading.Thread(target=alert_poller, daemon=True)
        t.start()

    # Run app
    try:
        socketio.run(app, host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Failed to start app: {e}")
        traceback.print_exc()
