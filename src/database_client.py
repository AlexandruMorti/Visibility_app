import sqlite3
import os
from datetime import datetime
from config import DB_PATH
conn = sqlite3.connect(DB_PATH)


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(APP_ROOT), "data", "visibility.db")


def get_db_connection():
    """Establishes a connection to the SQLite database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Initializes the database and creates the stormglass_data table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stormglass_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            timestamp TEXT NOT NULL,
            air_temperature REAL,
            cloud_cover REAL,
            rain REAL,
            swell_direction REAL,
            swell_height REAL,
            swell_period REAL,
            water_temperature REAL,
            wave_direction REAL,
            wave_height REAL,
            wave_period REAL,
            wind_speed REAL,
            wind_direction REAL,
            tide_height REAL,
            chlorophyll REAL,
            UNIQUE(lat, lon, timestamp)
        );
    """)
    
    # Migrate existing database: add new columns if they don't exist
    cursor.execute("PRAGMA table_info(stormglass_data)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    new_columns = {
        "air_temperature": "REAL",
        "cloud_cover": "REAL",
        "rain": "REAL",
        "swell_direction": "REAL",
        "wave_direction": "REAL",
        "wave_height": "REAL",
        "wave_period": "REAL",
        "chlorophyll": "REAL"
    }
    
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE stormglass_data ADD COLUMN {col_name} {col_type}")
    
    conn.commit()
    conn.close()


def save_stormglass_data(lat, lon, data):
    """Saves a single record of stormglass data to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # data['hours'][0] contains the relevant data
    hour_data = data.get("hours", [{}])[0]
    
    params = {
        "lat": lat,
        "lon": lon,
        "timestamp": hour_data.get("time"),
        "air_temperature": hour_data.get("airTemperature", {}).get("sg"),
        "cloud_cover": hour_data.get("cloudCover", {}).get("sg"),
        "rain": hour_data.get("rain", {}).get("sg"),
        "swell_direction": hour_data.get("swellDirection", {}).get("sg"),
        "swell_height": hour_data.get("swellHeight", {}).get("sg"),
        "swell_period": hour_data.get("swellPeriod", {}).get("sg"),
        "water_temperature": hour_data.get("waterTemperature", {}).get("sg"),
        "wave_direction": hour_data.get("waveDirection", {}).get("sg"),
        "wave_height": hour_data.get("waveHeight", {}).get("sg"),
        "wave_period": hour_data.get("wavePeriod", {}).get("sg"),
        "wind_speed": hour_data.get("windSpeed", {}).get("sg"),
        "wind_direction": hour_data.get("windDirection", {}).get("sg"),
        "tide_height": hour_data.get("seaLevel", {}).get("sg"),
        "chlorophyll": hour_data.get("chlorophyll", {}).get("sg"),
    }

    try:
        cursor.execute("""
            INSERT INTO stormglass_data (
                lat, lon, timestamp, air_temperature, cloud_cover, rain, swell_direction,
                swell_height, swell_period, water_temperature, wave_direction, wave_height,
                wave_period, wind_speed, wind_direction, tide_height, chlorophyll
            ) VALUES (
                :lat, :lon, :timestamp, :air_temperature, :cloud_cover, :rain, :swell_direction,
                :swell_height, :swell_period, :water_temperature, :wave_direction, :wave_height,
                :wave_period, :wind_speed, :wind_direction, :tide_height, :chlorophyll
            )
        """, params)
        conn.commit()
    except sqlite3.IntegrityError:
        # This will happen if a record for the same lat, lon, and timestamp already exists.
        # We can ignore it.
        pass
    finally:
        conn.close()

def update_chlorophyll(lat, lon, timestamp, chlorophyll_value):
    """Updates the chlorophyll value for an existing record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE stormglass_data
            SET chlorophyll = ?
            WHERE lat = ? AND lon = ? AND timestamp = ?
        """, (chlorophyll_value, lat, lon, timestamp))
        conn.commit()
    finally:
        conn.close()

def get_latest_stormglass_data(lat, lon):
    """Retrieves the most recent stormglass data record for a given lat/lon."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM stormglass_data
        WHERE lat = ? AND lon = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (lat, lon))
    record = cursor.fetchone()
    conn.close()
    return record

# Initialize the database when this module is loaded
initialize_db()
