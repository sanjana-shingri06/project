import sqlite3

# Connect to SQLite database (creates traffic.db if it doesn't exist)
conn = sqlite3.connect('traffic.db')
cursor = conn.cursor()

# Create table for traffic counts
cursor.execute('''
CREATE TABLE IF NOT EXISTS traffic_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    vehicle_count INTEGER NOT NULL
)
''')

# Create table for accident/alert events
cursor.execute('''
CREATE TABLE IF NOT EXISTS traffic_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    road TEXT NOT NULL,
    severity TEXT NOT NULL
)
''')

# Commit changes and close connection
conn.commit()
conn.close()

print("Database 'traffic.db' created with tables 'traffic_data' and 'traffic_alerts'.")
