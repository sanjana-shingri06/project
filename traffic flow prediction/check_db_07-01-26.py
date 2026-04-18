import sqlite3

conn = sqlite3.connect('traffic.db')
cursor = conn.cursor()

# Check all rows in traffic_data
cursor.execute("SELECT * FROM traffic_data")
rows = cursor.fetchall()
print("Rows in traffic_data:", rows)

conn.close()
