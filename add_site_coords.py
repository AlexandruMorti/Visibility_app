import sqlite3

conn = sqlite3.connect("visibility.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_name TEXT UNIQUE,
    lat REAL,
    lon REAL
);
""")

# Insert known sites
sites = [
    ("Bouley Bay", 49.2300, -2.0500),
    ("St Catherine", 49.2500, -2.0200)
]

for site in sites:
    cursor.execute("INSERT OR IGNORE INTO sites (site_name, lat, lon) VALUES (?, ?, ?)", site)

conn.commit()
conn.close()

print("Site coordinates added.")