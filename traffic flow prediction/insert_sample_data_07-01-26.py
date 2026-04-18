import sqlite3
from datetime import datetime, timedelta
import random

# Connect to the database
conn = sqlite3.connect('traffic.db')
cursor = conn.cursor()

# Generate 24 hours of traffic data
start_time = datetime(2025, 11, 19, 0, 0)
for i in range(24):
    timestamp = start_time + timedelta(hours=i)
    # simulate base traffic + morning/evening peaks
    vehicle_count = random.randint(10, 30)
    if 7 <= timestamp.hour <= 9:   # morning peak
        vehicle_count += 30
    if 17 <= timestamp.hour <= 19: # evening peak
        vehicle_count += 40
    cursor.execute(
        "INSERT INTO traffic_data (timestamp, vehicle_count) VALUES (?, ?)",
        (timestamp.strftime("%Y-%m-%d %H:%M:%S"), vehicle_count)
    )

conn.commit()
conn.close()
print("Sample traffic data inserted into traffic_data table.")
