import sqlite3

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

# Table for your dive logs
cursor.execute("""
CREATE TABLE IF NOT EXISTS dives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_time TEXT NOT NULL,
    site_name TEXT,
    visibility_m REAL NOT NULL,
    notes TEXT
);
""")

# Table for environmental conditions
cursor.execute("""
CREATE TABLE IF NOT EXISTS conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dive_id INTEGER NOT NULL,
    wind_speed REAL,
    wind_dir REAL,
    wave_height REAL,
    wave_period REAL,
    FOREIGN KEY (dive_id) REFERENCES dives(id)
);
""")

conn.commit()
conn.close()

print("Database created successfully.")