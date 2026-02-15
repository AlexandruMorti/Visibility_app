import sqlite3

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

cursor.execute("""
ALTER TABLE conditions ADD COLUMN tide_phase TEXT;
""")

conn.commit()
conn.close()

print("Added tide_phase column.")