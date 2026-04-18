from flask import Flask, render_template, request, jsonify, Response, url_for
import io
import traceback
import sqlite3
import time
import json
import threading
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
from traffic_analysis import (
    fetch_traffic_data, get_latest_traffic, analyze_peak_hours, plot_traffic,
    traffic_summary, traffic_by_weekday, plot_weekday_trends, plot_heatmap,
    load_model, predict_traffic
)

app = Flask(__name__)
app.secret_key = 'traffic_flow_secret_key'

# Socket.IO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ==========================================
# DATABASE INITIALIZATION
# ==========================================
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('traffic.db')
    cur = conn.cursor()
    
    # Create traffic_alerts table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS traffic_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road TEXT NOT NULL,
            severity TEXT,
            lat REAL,
            lng REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            congestion_level INTEGER
        )
    ''')
    
    # Create traffic_data table for historical data
    cur.execute('''
        CREATE TABLE IF NOT EXISTS traffic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road TEXT,
            vehicle_count INTEGER,
            timestamp DATETIME,
            congestion_level INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

# Road coordinates mapping
ROAD_COORDS = {
    "Main Street": (37.7749, -122.4194),
    "Broadway": (37.7793, -122.4192),
    "Market Street": (37.7937, -122.3965),
    "Central Ave": (37.7689, -122.4313),
    "Sunset Blvd": (37.7622, -122.4696),
    "5th Avenue": (37.7850, -122.4080),
    "Park Street": (37.7915, -122.3970),
    "Bay Street": (37.7780, -122.4120),
}

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
            SELECT id, road, severity, lat, lng, timestamp, congestion_level 
            FROM traffic_alerts 
            ORDER BY timestamp DESC LIMIT ?
        ''', (limit,))
        rows = cur.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            _id, road, severity, lat, lng, ts, congestion = row
            if not lat or not lng:
                if road in ROAD_COORDS:
                    lat, lng = ROAD_COORDS[road]
            alerts.append({
                'id': _id,
                'road': road,
                'severity': severity,
                'lat': lat,
                'lng': lng,
                'timestamp': ts,
                'congestion_level': congestion or 0
            })
        return list(reversed(alerts))
    except Exception as e:
        print(f"[ERROR] Failed to fetch alerts: {e}")
        return []

def broadcast_alert(alert_data):
    """Broadcast new alert to all connected clients"""
    try:
        socketio.emit('new_alert', alert_data, broadcast=True, namespace='/')
        print(f"[INFO] Alert broadcasted: {alert_data['road']}")
    except Exception as e:
        print(f"[ERROR] Broadcast failed: {e}")

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
        
        # Generate plots
        plot_traffic(hourly_avg)  # saves to static/plots/traffic_plot.png
        
        # Get summary statistics
        summary = traffic_summary(df) if df is not None and not df.empty else {}
        peak_hours_str = ', '.join(f"{h}:00" for h in peak_hours) if peak_hours else "N/A"
        
        # Get recent alerts
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
    """Simple test route to confirm server is working"""
    return "<h1>Server is Running!</h1><p>Go to <a href='/'>Home</a> or <a href='/map'>Map</a></p>"

@app.route("/map")
def traffic_map():
    """Display traffic map with real-time alerts"""
    alerts = get_alerts_with_traffic(limit=20)
    return render_template('map.html', alerts=alerts)

@app.route("/dashboard")
def dashboard():
    """Dashboard page: summary, weekday chart, heatmap, and alerts"""
    try:
        df = fetch_traffic_data()
        summary = traffic_summary(df) if df is not None and not df.empty else {}
        weekday_avg = traffic_by_weekday(df)
        plot_weekday_trends(weekday_avg)  # saves to static/plots/weekday_plot.png
        plot_heatmap(df)  # saves to static/plots/heatmap.png
        
        # Get alerts for dashboard
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

    # Handle AJAX/JSON POST
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

            # Prepare features (current model uses hour and day_of_week)
            features = [hour, day_of_week]
            pred_value = predict_traffic(model, features)

            # Average from dataset
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

    # GET request -> render form
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
        
        # Calculate statistics
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
        vehicle_count = data.get('vehicle_count', 0)
        
        if not road:
            return jsonify({'error': 'road is required'}), 400
        
        # Get coordinates
        lat, lng = ROAD_COORDS.get(road, (None, None))
        
        # Calculate congestion level
        congestion = calculate_congestion_level(vehicle_count)
        
        # Auto-determine severity based on congestion
        severity = determine_severity(congestion)
        
        timestamp = datetime.now().isoformat()
        
        # Insert into database
        conn = sqlite3.connect('traffic.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO traffic_alerts 
            (road, severity, lat, lng, timestamp, congestion_level) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (road, severity, lat, lng, timestamp, congestion))
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
            'congestion_level': congestion
        }
        
        # Broadcast to all connected clients
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
        
        # Group by road and get stats
        road_stats = df.groupby('road').agg({
            'vehicle_count': ['mean', 'max', 'min', 'count']
        }).round(2)
        
        result = []
        for road in road_stats.index:
            result.append({
                'road': road,
                'avg_vehicles': float(road_stats.loc[road, ('vehicle_count', 'mean')]),
                'max_vehicles': float(road_stats.loc[road, ('vehicle_count', 'max')]),
                'min_vehicles': float(road_stats.loc[road, ('vehicle_count', 'min')]),
                'records': int(road_stats.loc[road, ('vehicle_count', 'count')])
            })
        
        return jsonify({'roads': result})
    except Exception as e:
        print(f"[ERROR] Error in traffic by road: {e}")
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
        print("[INFO] Client connected, sent initial alerts")
    except Exception as e:
        print(f"[ERROR] Failed to send initial alerts: {e}")

@socketio.on('request_updates')
def handle_update_request():
    """Client requests latest traffic updates"""
    try:
        alerts = get_alerts_with_traffic(limit=10)
        emit('alerts_update', {'alerts': alerts, 'timestamp': datetime.now().isoformat()})
        print("[INFO] Sent updates to client")
    except Exception as e:
        print(f"[ERROR] Update request failed: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    print("[INFO] Client disconnected")

# ==========================================
# BACKGROUND TASKS
# ==========================================

def real_time_poller():
    """Poll database every 3 seconds and broadcast updates to all clients"""
    last_check = time.time()
    alert_cache = set()
    
    while True:
        try:
            current_time = time.time()
            if current_time - last_check >= 3:  # Every 3 seconds
                alerts = get_alerts_with_traffic(limit=5)
                for alert in alerts:
                    alert_id = alert['id']
                    if alert_id not in alert_cache:
                        broadcast_alert(alert)
                        alert_cache.add(alert_id)
                        # Keep only last 50 in cache
                        if len(alert_cache) > 50:
                            alert_cache.pop()
                last_check = current_time
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Poller error: {e}")
            time.sleep(5)

# ==========================================
# MAIN APPLICATION ENTRY POINT
# ==========================================

if __name__ == "__main__":
    import socket
    
    # Find an available port
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
    
    print(f"[SUCCESS] Starting Socket.IO app on http://127.0.0.1:{PORT}/")
    
    # Start real-time poller in background
    try:
        socketio.start_background_task(real_time_poller)
        print("[INFO] Real-time poller started")
    except Exception as e:
        print(f"[WARNING] Socket.IO background task failed, using threading: {e}")
        t = threading.Thread(target=real_time_poller, daemon=True)
        t.start()
        print("[INFO] Real-time poller started (threaded)")

    # Run app with Socket.IO server
    try:
        socketio.run(app, host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[ERROR] Failed to start Socket.IO server: {e}")
        traceback.print_exc()
