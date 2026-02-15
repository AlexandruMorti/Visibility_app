import sqlite3

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE conditions
ADD COLUMN tide_height REAL;
""")

conn.commit()
conn.close()

print("Tide height column added.")