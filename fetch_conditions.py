from wsgiref import headers
import requests
import pandas as pd
import sqlite3
import os
import json

LAT = 49.22
LON = -2.13
STORMGLASS_KEY = "a4a56df8-0796-11f1-8129-0242ac120004-a4a56eac-0796-11f1-8129-0242ac120004"


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


# ---------------------------------------------------------
# MAIN get_conditions()
# ---------------------------------------------------------
def get_conditions(dt):
    dt_rounded = dt.round("h")
    dt_iso = dt_rounded.strftime("%Y-%m-%dT%H:00")
    dt_unix = int(dt_rounded.timestamp())

    # ---------------------------------------------------------
    # 1. WIND + WAVES (Open-Meteo)
    # ---------------------------------------------------------
    marine_url = "https://marine-api.open-meteo.com/v1/marine"
    marine_params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "wave_height,wave_period,wind_speed_10m,wind_direction_10m",
        "start_date": dt_rounded.strftime("%Y-%m-%d"),
        "end_date": dt_rounded.strftime("%Y-%m-%d")
    }

    marine = requests.get(marine_url, params=marine_params).json()

    # Find nearest timestamp
    times = marine["hourly"]["time"]
    if dt_iso in times:
        idx = times.index(dt_iso)
    else:
        time_series = pd.to_datetime(times)
        idx = (abs(time_series - dt_rounded)).argmin()

    # Wave height (m → ft)
    wave_height_m = marine["hourly"]["wave_height"][idx]
    wave_height_ft = wave_height_m * 3.28084 if wave_height_m is not None else None

    # Wind speed (m/s → knots)
    wind_speed_ms = marine["hourly"]["wind_speed_10m"][idx]
    wind_speed_knots = wind_speed_ms * 1.94384 if wind_speed_ms is not None else None

    wind_dir = marine["hourly"]["wind_direction_10m"][idx]
    wave_period = marine["hourly"]["wave_period"][idx]

    # ---------------------------------------------------------
    # 2. TIDE (Stormglass, cached)
    # ---------------------------------------------------------
    tide_data = get_tide_data_cached(dt_rounded)

    tide_height = None
    tide_phase = None

    # Handle API errors or rate limits
    if "errors" in tide_data:
        print("Stormglass error:", tide_data["errors"])
        return {
            "wind_speed": wind_speed_knots,
            "wind_dir": wind_dir,
            "wave_height": wave_height_ft,
            "wave_period": wave_period,
            "tide_height": None,
            "tide_phase": None
        }

    if "data" in tide_data and len(tide_data["data"]) > 0:
        heights = [entry["sg"] for entry in tide_data["data"]]
        times_sg = [entry["time"] for entry in tide_data["data"]]

        # Convert to datetime
        times_sg_dt = pd.to_datetime(times_sg)

        # Strip timezone if present
        if times_sg_dt.tz is not None:
            times_sg_dt = times_sg_dt.tz_convert(None)

        # Find closest tide time
        idx_tide = (abs(times_sg_dt - dt_rounded)).argmin()
        tide_height = heights[idx_tide]

        # Tide phase
        if 1 <= idx_tide < len(heights) - 1:
            before = heights[idx_tide - 1]
            after = heights[idx_tide + 1]

            if after > before:
                tide_phase = "rising"
            elif after < before:
                tide_phase = "falling"
            else:
                tide_phase = "slack"

    # ---------------------------------------------------------
    # 3. RETURN CLEAN STRUCTURED DATA
    # ---------------------------------------------------------
    return {
        "wind_speed": wind_speed_knots,
        "wind_dir": wind_dir,
        "wave_height": wave_height_ft,
        "wave_period": wave_period,
        "tide_height": tide_height,
        "tide_phase": tide_phase
    }


def update_conditions():
    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    dives = pd.read_sql_query("SELECT * FROM dives", conn)
    dives["date_time"] = pd.to_datetime(dives["date_time"])

    for _, row in dives.iterrows():
        cond = get_conditions(row["date_time"])

        cursor.execute("""
    INSERT INTO conditions (dive_id, wind_speed, wind_dir, wave_height, wave_period, tide_height, tide_phase)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        row["id"],
        cond["wind_speed"],
        cond["wind_dir"],
        cond["wave_height"],
        cond["wave_period"],
        cond["tide_height"],
        cond["tide_phase"]
    ))


    conn.commit()
    conn.close()
    print("Conditions updated successfully.")

if __name__ == "__main__":
    update_conditions()