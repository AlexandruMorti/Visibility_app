import sqlite3
import os
from datetime import datetime
try:
    from . import config as config
except Exception:
    import config as config

# Use DB path from config (allow environment override)
DB_PATH = config.DB_PATH


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

    # Ensure dives table exists and has required columns
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dives (
            id TEXT PRIMARY KEY,
            lat REAL,
            lon REAL,
            date TEXT,
            depth REAL,
            notes TEXT,
            tide_height REAL,
            breath_hold_time REAL,
            visibility REAL,
            water_temp REAL,
            outside_temp REAL,
            created_at TEXT,
            updated_at TEXT
        );
    """)

    # Add any missing columns to the dives table (safe migration)
    cursor.execute("PRAGMA table_info(dives)")
    existing = {row[1] for row in cursor.fetchall()}
    required_columns = {
        'id': 'TEXT',
        'lat': 'REAL',
        'lon': 'REAL',
        'date': 'TEXT',
        'depth': 'REAL',
        'notes': 'TEXT',
        'tide_height': 'REAL',
        'breath_hold_time': 'REAL',
        'visibility': 'REAL',
        'water_temp': 'REAL',
        'outside_temp': 'REAL',
        'created_at': 'TEXT',
        'updated_at': 'TEXT',
    }
    for col, coltype in required_columns.items():
        if col not in existing:
            try:
                cursor.execute(f"ALTER TABLE dives ADD COLUMN {col} {coltype}")
            except Exception:
                # best-effort migration; continue on failure
                pass

    conn.commit()
    conn.close()

    # Attempt to migrate existing JSON dives into the DB (if present)
    try:
        migrate_dives_from_json()
    except Exception:
        pass


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
        # Ignore duplicate entries for the same lat/lon/timestamp
        pass
    finally:
        conn.close()


def _row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def get_all_dives():
    """Return all dives as a list of dicts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dives ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def insert_dive(dive: dict):
    """Insert a dive dict into the dives table. Expects keys matching the columns.
    If `id` is missing one will be generated by the caller (app.py creates UUIDs).
    Returns the inserted dive as dict.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Inspect table to know which columns are NOT NULL so we can supply defaults
    conn_pr = get_db_connection()
    cur_pr = conn_pr.cursor()
    cur_pr.execute("PRAGMA table_info(dives)")
    table_info = cur_pr.fetchall()
    conn_pr.close()
    notnull_cols = {row[1] for row in table_info if row[3] == 1}
    col_types = {row[1]: row[2].upper() for row in table_info}

    # Build insert dynamically: if id is None, let DB assign integer PK
    cols = []
    placeholders = []
    params = {}
    # Handle legacy NOT NULL columns from older schema (e.g. date_time, visibility_m)
    legacy_defaults = {}
    col_names = {row[1] for row in table_info}
    if 'date_time' in col_names:
        # prefer explicit date, else created_at
        legacy_defaults['date_time'] = dive.get('date') or dive.get('created_at') or ''
    if 'visibility_m' in col_names:
        legacy_defaults['visibility_m'] = dive.get('visibility') or dive.get('visibility_m') or 0
    if 'site_name' in col_names:
        legacy_defaults['site_name'] = dive.get('site_name') or ''
    if 'max_depth_m' in col_names:
        legacy_defaults['max_depth_m'] = dive.get('depth') or 0
    if 'breath_hold_s' in col_names:
        legacy_defaults['breath_hold_s'] = dive.get('breath_hold_time') or dive.get('breath_hold_s') or 0
    expected_cols = ('id','lat','lon','date','depth','notes','tide_height','breath_hold_time','visibility','water_temp','outside_temp','created_at','updated_at')
    extra_cols = [c for c in col_names if c not in expected_cols]
    for col in list(expected_cols) + extra_cols:
        val = dive.get(col)
        if val is None and col == 'id':
            # skip id to let DB auto-assign integer PK when not provided
            continue
        # If column is NOT NULL but value is missing, supply a sensible default
        if val is None and col in notnull_cols:
            if col in ('date','created_at','updated_at'):
                from datetime import datetime as _dt
                val = _dt.utcnow().isoformat()
            elif col == 'site_name':
                val = ''
            else:
                # numeric default
                val = 0
        # Fill legacy columns if present
        if col in legacy_defaults and (val is None or val == 0 or val == ''):
            val = legacy_defaults[col]
        cols.append(col)
        placeholders.append(':'+col)
        params[col] = val
    # Handle id column type mismatch: if DB id is INTEGER but provided id is non-numeric, omit it
    if 'id' in params:
        id_type = col_types.get('id', '')
        provided_id = params.get('id')
        if id_type.startswith('INT') and provided_id is not None:
            try:
                int(provided_id)
            except Exception:
                # remove id from insert
                try:
                    idx = cols.index('id')
                    cols.pop(idx)
                    placeholders.pop(idx)
                    params.pop('id', None)
                except ValueError:
                    pass

    sql = f"INSERT INTO dives ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    # remember whether we will insert an `id` column
    id_will_be_inserted = 'id' in cols
    cursor.execute(sql, params)
    conn.commit()
    # Fetch the inserted row: prefer selecting by the inserted id if we included it,
    # otherwise use lastrowid to find the row.
    if id_will_be_inserted and dive.get('id'):
        key = dive.get('id')
        cursor.execute('SELECT * FROM dives WHERE id = ?', (key,))
    else:
        lr = cursor.lastrowid
        cursor.execute('SELECT * FROM dives WHERE ROWID = ?', (lr,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_dict(row)
    


def update_dive_record(dive_id: str, fields: dict):
    """Update fields for a dive identified by dive_id. Returns updated record or None."""
    if not fields:
        return None
    allowed = {"lat","lon","date","depth","notes","tide_height","breath_hold_time","visibility","water_temp","outside_temp","updated_at"}
    set_clause = []
    params = []
    for k, v in fields.items():
        if k in allowed:
            set_clause.append(f"{k} = ?")
            params.append(v)
    if not set_clause:
        return None
    params.append(dive_id)
    sql = f"UPDATE dives SET {', '.join(set_clause)} WHERE id = ?"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()
    cursor.execute('SELECT * FROM dives WHERE id = ?', (dive_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_dict(row)


def migrate_dives_from_json():
    """If data/dives.json exists, import entries into the DB (skips duplicates)."""
    try:
        from pathlib import Path
        import json as _json
        base = Path(__file__).resolve().parent
        json_path = base.parent / 'data' / 'dives.json'
        if not json_path.exists():
            return
        with open(json_path, 'r', encoding='utf-8') as f:
            arr = _json.load(f)
        conn = get_db_connection()
        cursor = conn.cursor()
        for d in arr:
            did = d.get('id')
            if not did:
                continue
            cursor.execute('SELECT 1 FROM dives WHERE id = ?', (did,))
            if cursor.fetchone():
                continue
            cursor.execute("""
                INSERT INTO dives (id, lat, lon, date, depth, notes, tide_height,
                    breath_hold_time, visibility, water_temp, outside_temp, created_at, updated_at)
                VALUES (:id, :lat, :lon, :date, :depth, :notes, :tide_height,
                    :breath_hold_time, :visibility, :water_temp, :outside_temp, :created_at, :updated_at)
            """, d)
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

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

def save_dive(lat, lon, visibility, notes=""):
    # Use DB-backed insert helper to ensure schema alignment
    from datetime import datetime as _dt
    dive = {
        'id': None,
        'lat': lat,
        'lon': lon,
        'date': _dt.utcnow().isoformat(),
        'depth': None,
        'notes': notes,
        'tide_height': None,
        'breath_hold_time': None,
        'visibility': visibility,
        'water_temp': None,
        'outside_temp': None,
        'created_at': _dt.utcnow().isoformat(),
        'updated_at': None,
    }
    # If caller didn't provide an id, insert_dive will expect one; generate a uuid here
    import uuid as _uuid
    dive['id'] = str(_uuid.uuid4())
    return insert_dive(dive)


# (get_all_dives is defined earlier and returns records as dicts)


# Initialize the database when this module is loaded
initialize_db()
