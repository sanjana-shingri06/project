#!/usr/bin/env python3
"""Test script to verify all components are working"""

import sys
import os

print("=" * 60)
print("🔍 DEBUGGING TRAFFIC FLOW PREDICTION SYSTEM")
print("=" * 60)

# Test 1: Check imports
print("\n1️⃣ Testing Imports...")
try:
    from traffic_analysis import fetch_traffic_data, load_model
    print("   ✅ traffic_analysis imported")
except Exception as e:
    print(f"   ❌ traffic_analysis import failed: {e}")
    sys.exit(1)

try:
    from traffic_advanced_analytics import TrafficAnalytics, SmartTrafficController
    print("   ✅ traffic_advanced_analytics imported")
except Exception as e:
    print(f"   ❌ traffic_advanced_analytics import failed: {e}")
    sys.exit(1)

try:
    from flask import Flask
    from flask_socketio import SocketIO
    print("   ✅ Flask & Flask-SocketIO imported")
except Exception as e:
    print(f"   ❌ Flask imports failed: {e}")
    sys.exit(1)

# Test 2: Check database
print("\n2️⃣ Testing Database...")
try:
    import sqlite3
    conn = sqlite3.connect('traffic.db')
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    
    if tables:
        print(f"   ✅ Database exists with {len(tables)} tables:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f"      - {table[0]}: {count} records")
    else:
        print("   ⚠️ Database exists but no tables found")
    
    conn.close()
except Exception as e:
    print(f"   ❌ Database error: {e}")
    sys.exit(1)

# Test 3: Check templates
print("\n3️⃣ Testing Templates...")
templates = [
    'analytics.html',
    'live.html',
    'map.html',
    'dashboard.html',
    'predict.html',
    'index.html'
]

for template in templates:
    if os.path.exists(f'templates/{template}'):
        print(f"   ✅ {template}")
    else:
        print(f"   ❌ {template} NOT FOUND")

# Test 4: Check analytics module
print("\n4️⃣ Testing Analytics Module...")
try:
    analytics = TrafficAnalytics('traffic.db')
    
    # Try each method
    methods = {
        'Forecast': analytics.get_congestion_forecast,
        'Anomalies': analytics.detect_anomalies,
        'Health': analytics.get_road_health_score,
        'Environmental': analytics.get_environmental_impact,
        'Recommendations': analytics.get_ai_recommendations,
        'Peak Hours': analytics.get_peak_hours_analysis
    }
    
    for name, method in methods.items():
        try:
            result = method()
            print(f"   ✅ {name}: OK")
        except Exception as e:
            print(f"   ⚠️ {name}: {str(e)[:50]}")
except Exception as e:
    print(f"   ❌ Analytics module error: {e}")

# Test 5: Check Flask app
print("\n5️⃣ Testing Flask App...")
try:
    from app import app, socketio
    
    # Check routes
    routes = [
        '/',
        '/live',
        '/analytics',
        '/map',
        '/dashboard',
        '/predict',
        '/api/analytics/recommendations',
        '/api/analytics/road-health',
        '/api/analytics/forecast'
    ]
    
    app_routes = [str(rule) for rule in app.url_map.iter_rules()]
    
    for route in routes:
        if route in app_routes:
            print(f"   ✅ {route}")
        else:
            print(f"   ❌ {route} NOT FOUND")
except Exception as e:
    print(f"   ❌ Flask app error: {e}")

print("\n" + "=" * 60)
print("✅ DEBUG REPORT COMPLETE")
print("=" * 60)
print("\nTo start the server, run:")
print("  python app.py")
print("\nThen open in browser:")
print("  http://127.0.0.1:5000/analytics")
