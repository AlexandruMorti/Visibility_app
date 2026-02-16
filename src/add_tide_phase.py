import sqlite3
from config import DB_PATH
conn = sqlite3.connect(DB_PATH)


conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE conditions ADD COLUMN tide_phase TEXT;
""")

conn.commit()
conn.close()

print("Added tide_phase column.")