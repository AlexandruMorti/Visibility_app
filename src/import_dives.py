import sqlite3
import pandas as pd

df = pd.read_csv("dive_log.csv")

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO dives (date_time, site_name, visibility_m, notes)
        VALUES (?, ?, ?, ?)
    """, (row["date_time"], row["site_name"], row["visibility_m"], row["notes"]))

conn.commit()
conn.close()

print("Dives imported successfully.")