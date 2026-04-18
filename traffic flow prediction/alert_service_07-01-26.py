# alerts_service.py
import random
import time
import pandas as pd
from sqlalchemy import create_engine

# ----------------------------
# Database connection
# ----------------------------
DB_URI = "sqlite:///traffic.db"  # Replace with your DB
engine = create_engine(DB_URI)

# ----------------------------
# Simulated road list
# ----------------------------
roads = ["Highway 1", "Main Street", "2nd Avenue", "City Bridge", "Market Road"]

# ----------------------------
# Function: simulate accident detection
# ----------------------------
def detect_accident():
    """
    Simulate detection of accidents/road closures.
    Replace with real sensor or camera integration in production.
    """
    road = random.choice(roads)
    severity = random.choice(["Minor", "Moderate", "Severe"])
    timestamp = pd.Timestamp.now()
    return {"road": road, "severity": severity, "timestamp": timestamp}

# ----------------------------
# Function: store alert in DB
# ----------------------------
def store_alert(alert):
    df = pd.DataFrame([alert])
    df.to_sql('traffic_alerts', con=engine, if_exists='append', index=False)

# ----------------------------
# Function: send alert
# ----------------------------
def send_alert(alert):
    """
    Replace this with real notifications (push, SMS, digital signage)
    """
    print(f"[ALERT] {alert['timestamp']}: {alert['severity']} accident on {alert['road']}!")
    store_alert(alert)

# ----------------------------
# Main loop: continuous monitoring
# ----------------------------
if __name__ == "__main__":
    print("Starting Traffic Alert Service...")
    try:
        while True:
            # Simulate random events (replace with real detection)
            if random.random() < 0.3:  # 30% chance per iteration
                alert = detect_accident()
                send_alert(alert)
            time.sleep(5)  # wait 5 seconds before next check
    except KeyboardInterrupt:
        print("Traffic Alert Service stopped.")
