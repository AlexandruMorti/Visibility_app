import sqlite3
from config import DB_PATH
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE conditions
ADD COLUMN tide_height REAL;
""")

conn.commit()
conn.close()

print("Tide height column added.")