"""
Advanced Analytics Module for Traffic Flow Prediction
Features: Predictive analytics, anomaly detection, AI recommendations
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from collections import defaultdict
import json

class TrafficAnalytics:
    """Advanced traffic analytics and predictions"""
    
    def __init__(self, db_path='traffic.db'):
        self.db_path = db_path
    
    def get_congestion_forecast(self, hours_ahead=6):
        """Predict congestion patterns for next N hours using simple ML"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Get last 48 hours of data
            cur.execute('''
                SELECT road, congestion_level, timestamp 
                FROM traffic_updates 
                WHERE timestamp > datetime('now', '-48 hours')
                ORDER BY timestamp DESC
            ''')
            rows = cur.fetchall()
            conn.close()
            
            if not rows:
                return {}
            
            # Group by road and calculate trends
            road_data = defaultdict(list)
            for road, cong, ts in rows:
                road_data[road].append(cong)
            
            forecast = {}
            for road, congestion_values in road_data.items():
                if len(congestion_values) > 2:
                    # Calculate average and trend
                    avg = np.mean(congestion_values)
                    trend = (congestion_values[0] - congestion_values[-1]) / max(len(congestion_values), 1)
                    
                    # Simple linear forecast
                    forecasted_congestion = avg + (trend * (hours_ahead / 6))
                    forecasted_congestion = max(0, min(100, forecasted_congestion))
                    
                    forecast[road] = {
                        'current': congestion_values[0],
                        'predicted': round(forecasted_congestion, 2),
                        'trend': 'increasing' if trend > 0 else 'decreasing',
                        'confidence': 0.85
                    }
            
            return forecast
        except Exception as e:
            print(f"[ERROR] Forecast error: {e}")
            return {}
    
    def detect_anomalies(self):
        """Detect unusual traffic patterns (anomalies)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Get last 24 hours
            cur.execute('''
                SELECT road, vehicle_count, timestamp 
                FROM traffic_updates 
                WHERE timestamp > datetime('now', '-24 hours')
                ORDER BY road, timestamp
            ''')
            rows = cur.fetchall()
            conn.close()
            
            road_data = defaultdict(list)
            for road, count, ts in rows:
                road_data[road].append(count)
            
            anomalies = []
            for road, counts in road_data.items():
                if len(counts) > 3:
                    mean = np.mean(counts)
                    std = np.std(counts)
                    
                    # Values > 2 std devs are anomalies
                    for i, count in enumerate(counts):
                        if abs(count - mean) > 2 * std:
                            anomalies.append({
                                'road': road,
                                'vehicle_count': count,
                                'expected_range': f"{int(mean-std)}-{int(mean+std)}",
                                'severity': 'high' if count > mean + 2*std else 'medium'
                            })
            
            return anomalies
        except Exception as e:
            print(f"[ERROR] Anomaly detection error: {e}")
            return []
    
    def get_ai_recommendations(self):
        """Generate AI-powered traffic management recommendations"""
        try:
            anomalies = self.detect_anomalies()
            forecast = self.get_congestion_forecast()
            
            recommendations = []
            
            # High congestion recommendations
            for road, data in forecast.items():
                if data['predicted'] > 70:
                    recommendations.append({
                        'type': 'route_optimization',
                        'road': road,
                        'recommendation': f'High congestion predicted on {road}. Consider alternative routes.',
                        'priority': 'high',
                        'action': 'notify_commuters'
                    })
            
            # Anomaly-based recommendations
            for anomaly in anomalies:
                recommendations.append({
                    'type': 'incident_investigation',
                    'road': anomaly['road'],
                    'recommendation': f"Unusual traffic pattern detected on {anomaly['road']}. Investigate potential incident.",
                    'priority': 'high' if anomaly['severity'] == 'high' else 'medium',
                    'action': 'dispatch_investigation'
                })
            
            return recommendations
        except Exception as e:
            print(f"[ERROR] Recommendation error: {e}")
            return []
    
    def get_peak_hours_analysis(self):
        """Analyze peak hours per road"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT road, strftime('%H', timestamp) as hour, AVG(congestion_level) as avg_congestion
                FROM traffic_updates
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY road, hour
                ORDER BY road, hour
            ''')
            rows = cur.fetchall()
            conn.close()
            
            peak_analysis = defaultdict(lambda: {'peak_hour': None, 'peak_congestion': 0})
            for road, hour, avg_cong in rows:
                if avg_cong > peak_analysis[road]['peak_congestion']:
                    peak_analysis[road]['peak_hour'] = int(hour)
                    peak_analysis[road]['peak_congestion'] = round(avg_cong, 2)
            
            return dict(peak_analysis)
        except Exception as e:
            print(f"[ERROR] Peak hours analysis error: {e}")
            return {}
    
    def get_environmental_impact(self):
        """Calculate environmental impact metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT SUM(vehicle_count) as total_vehicles, 
                       AVG(congestion_level) as avg_congestion,
                       AVG(speed) as avg_speed
                FROM traffic_updates
                WHERE timestamp > datetime('now', '-24 hours')
            ''')
            result = cur.fetchone()
            conn.close()
            
            if result[0]:
                total_vehicles = result[0]
                avg_congestion = result[1] or 0
                avg_speed = result[2] or 0
                
                # Simplified calculation
                emission_index = (total_vehicles * avg_congestion) / (avg_speed + 1)
                fuel_efficiency = 100 - (avg_congestion * 0.8)
                
                return {
                    'total_vehicles_24h': int(total_vehicles),
                    'avg_congestion': round(avg_congestion, 2),
                    'avg_speed': round(avg_speed, 2),
                    'emission_index': round(emission_index, 2),
                    'fuel_efficiency_score': round(max(0, fuel_efficiency), 2),
                    'estimated_co2_kg': round((total_vehicles * 0.2 * (100 - fuel_efficiency) / 100), 2)
                }
            return {}
        except Exception as e:
            print(f"[ERROR] Environmental impact error: {e}")
            return {}
    
    def get_road_health_score(self):
        """Calculate health score for each road (0-100)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT road, 
                       AVG(congestion_level) as avg_cong,
                       COUNT(*) as data_points,
                       AVG(speed) as avg_speed
                FROM traffic_updates
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY road
            ''')
            rows = cur.fetchall()
            conn.close()
            
            health_scores = {}
            for road, avg_cong, data_points, avg_speed in rows:
                # Score formula: 100 - (congestion impact) - (speed impact)
                score = 100 - (avg_cong * 0.6) - ((50 - (avg_speed or 30)) * 0.8)
                health_scores[road] = {
                    'score': round(max(0, min(100, score)), 2),
                    'status': 'Excellent' if score >= 80 else 'Good' if score >= 60 else 'Fair' if score >= 40 else 'Poor',
                    'avg_congestion': round(avg_cong, 2),
                    'avg_speed': round(avg_speed or 0, 2)
                }
            
            return health_scores
        except Exception as e:
            print(f"[ERROR] Road health score error: {e}")
            return {}


class SmartTrafficController:
    """Intelligent traffic management system"""
    
    def __init__(self, db_path='traffic.db'):
        self.db_path = db_path
        self.analytics = TrafficAnalytics(db_path)
    
    def get_traffic_alerts_auto(self):
        """Automatically generate traffic alerts based on thresholds"""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT road, vehicle_count, congestion_level, speed
                FROM traffic_updates
                WHERE timestamp = (SELECT MAX(timestamp) FROM traffic_updates)
                GROUP BY road
            ''')
            rows = cur.fetchall()
            conn.close()
            
            auto_alerts = []
            for road, vehicle_count, congestion, speed in rows:
                if congestion > 80:
                    auto_alerts.append({
                        'road': road,
                        'alert_type': 'Critical Congestion',
                        'severity': 'critical',
                        'vehicles': vehicle_count,
                        'action': 'Activate alternative routes'
                    })
                elif congestion > 60:
                    auto_alerts.append({
                        'road': road,
                        'alert_type': 'Moderate Congestion',
                        'severity': 'warning',
                        'vehicles': vehicle_count,
                        'action': 'Monitor situation'
                    })
            
            return auto_alerts
        except Exception as e:
            print(f"[ERROR] Auto alerts error: {e}")
            return []
    
    def calculate_optimal_routes(self, source_road, dest_road):
        """Calculate optimal route based on congestion"""
        roads = ["Main Street", "Broadway", "Market Street", "Central Ave", "Sunset Blvd", "5th Avenue", "Park Street", "Bay Street"]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute('''
                SELECT road, AVG(congestion_level) as avg_cong, AVG(speed) as avg_speed
                FROM traffic_updates
                WHERE timestamp > datetime('now', '-1 hour')
                GROUP BY road
            ''')
            road_conditions = {row[0]: {'congestion': row[1], 'speed': row[2]} for row in cur.fetchall()}
            conn.close()
            
            # Simple routing suggestion
            recommendations = []
            for road in roads:
                if road in road_conditions:
                    cond = road_conditions[road]
                    recommendations.append({
                        'road': road,
                        'congestion': round(cond['congestion'], 2),
                        'speed': round(cond['speed'], 2),
                        'estimated_time': round(10 / (cond['speed'] or 30) * 60, 1)  # minutes
                    })
            
            # Sort by congestion (lowest first)
            recommendations.sort(key=lambda x: x['congestion'])
            return recommendations[:3]  # Top 3 best routes
        except Exception as e:
            print(f"[ERROR] Route calculation error: {e}")
            return []
