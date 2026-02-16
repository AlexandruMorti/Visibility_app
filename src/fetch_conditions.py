#!/usr/bin/env python3
import json
import os
import sqlite3
import pandas as pd
from datetime import datetime

# If you need Flask only for the web app, don't import Flask here.
# from flask import Flask, request, jsonify, render_template

LAT = 49.22
LON = -2.13
STORMGLASS_KEY = "234"
# STORMGLASS_KEY = "a4a56df8-0796-11f1-8129-0242ac120004-a4a56eac-0796-11f1-8129-0242ac120004"


# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))        # src/
DB_PATH = os.path.join(BASE_DIR, "visibility.db")            # src/visibility.db

print("Using DB:", DB_PATH)

# ---------------------------------------------------------
# CACHED TIDE FETCHER (1 Stormglass call per day)
# ---------------------------------------------------------
def get_tide_data_cached(dt_rounded):
    date_str = dt_rounded.strftime("%Y-%m-%d")
    cache_file = f"cache/tide_{date_str}.json"

    # Create cache folder if missing
    os.makedirs("cache", exist_ok=True)

    # If cached file exists → load it
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    # Otherwise → fetch from Stormglass
    dt_unix = int(dt_rounded.timestamp())

    storm_url = "https://api.stormglass.io/v2/tide/sea-level/point"
    storm_params = {
        "lat": LAT,
        "lng": LON,
        "start": dt_unix - 12*3600,   # 12 hours before
        "end": dt_unix + 12*3600      # 12 hours after
    }

    headers = {"Authorization": STORMGLASS_KEY}

    tide_data = requests.get(storm_url, params=storm_params, headers=headers).json()

    # Save to cache
    with open(cache_file, "w") as f:
        json.dump(tide_data, f)

    return tide_data


# Ensure DB exists and create schema if missing
def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_time TEXT NOT NULL,
        site_name TEXT,
        visibility_m REAL,
        max_depth_m REAL,
        breath_hold_s REAL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        lat REAL,
        lon REAL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dive_id INTEGER,
        wind_speed REAL,
        wind_dir REAL,
        wave_height REAL,
        wave_period REAL,
        tide_height REAL,
        tide_phase TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dive_id) REFERENCES dives(id)
    );
    """)
    conn.commit()

# Replace this stub with your real API call
def get_conditions(dt: datetime):
    # Example stubbed response
    return {
        "wind_speed": 5.0,
        "wind_dir": 180,
        "wave_height": 0.5,
        "wave_period": 6.0,
        "tide_height": 1.2,
        "tide_phase": "rising"
    }

def update_conditions():
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)

        # Show tables for debug
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print("TABLES:", cur.fetchall())

        # If there are no dives, nothing to do
        dives_df = pd.read_sql_query("SELECT * FROM dives", conn)
        if dives_df.empty:
            print("No dives found. Nothing to update.")
            return

        dives_df["date_time"] = pd.to_datetime(dives_df["date_time"])

        for _, row in dives_df.iterrows():
            cond = get_conditions(row["date_time"])

            cur.execute("""
                INSERT INTO conditions
                (dive_id, wind_speed, wind_dir, wave_height, wave_period, tide_height, tide_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["id"]),
                float(cond.get("wind_speed", None)),
                float(cond.get("wind_dir", None)),
                float(cond.get("wave_height", None)),
                float(cond.get("wave_period", None)),
                float(cond.get("tide_height", None)),
                cond.get("tide_phase", None)
            ))
        conn.commit()
        print("Conditions updated.")
    except Exception as e:
        print("Error in update_conditions:", e)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    update_conditions()