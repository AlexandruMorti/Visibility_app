import os
import json
import time
import requests
from datetime import datetime, timezone, timedelta

# Database import (works in both package and direct-run modes)
try:
    from . import database_client
except ImportError:
    import database_client

# Load API key from config
from config import STORMGLASS_API_KEY as API_KEY

# Stormglass API constants
API_ROOT = "https://api.stormglass.io/v2"
CACHE_DIR = "cache/stormglass"

# Weather parameters for the main endpoint
PARAMS = [
    "airTemperature", "cloudCover", "rain", "swellDirection",
    "swellHeight", "swellPeriod", "waterTemperature", "waveDirection",
    "waveHeight", "wavePeriod", "windSpeed", "windDirection", "seaLevel"
]


# ------------------------------------------------------------
#  FETCH WEATHER + TIDE (with dt)
# ------------------------------------------------------------
def fetch_stormglass(lat: float, lon: float, dt: datetime):
    """
    Fetch Stormglass weather/tide data with:
    - DB fallback
    - Daily file caching
    - Safe SSL
    """
    # 1. DB fallback if no API key
    if not API_KEY:
        record = database_client.get_latest_stormglass_data(lat, lon)
        if record:
            return {
                "hours": [{
                    "time": record["timestamp"],
                    "airTemperature": {"sg": record.get("air_temperature")},
                    "cloudCover": {"sg": record.get("cloud_cover")},
                    "rain": {"sg": record.get("rain")},
                    "swellDirection": {"sg": record.get("swell_direction")},
                    "swellHeight": {"sg": record["swell_height"]},
                    "swellPeriod": {"sg": record["swell_period"]},
                    "waterTemperature": {"sg": record["water_temperature"]},
                    "waveDirection": {"sg": record.get("wave_direction")},
                    "waveHeight": {"sg": record.get("wave_height")},
                    "wavePeriod": {"sg": record.get("wave_period")},
                    "windSpeed": {"sg": record["wind_speed"]},
                    "windDirection": {"sg": record["wind_direction"]},
                    "seaLevel": {"sg": record["tide_height"]},
                }],
                "meta": {"source": "database-fallback"}
            }
        return None

    # 2. Daily cache
    date_str = dt.strftime("%Y-%m-%d")
    lat_str = f"{lat:.2f}".replace(".", "_")
    lon_str = f"{lon:.2f}".replace(".", "_")

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"sg_{lat_str}_{lon_str}_{date_str}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                database_client.save_stormglass_data(lat, lon, data)
                return data
        except Exception:
            pass  # corrupted cache → fetch fresh

    # 3. API request
    url = f"{API_ROOT}/weather/point"
    headers = {"Authorization": API_KEY}

    params = {
        "lat": lat,
        "lng": lon,
        "params": ",".join(PARAMS),
        "start": dt.isoformat(),
        "end": dt.isoformat(),
        "source": "sg",
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print("Stormglass fetch failed:", e)
        return None

    # 4. Save to cache + DB
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    database_client.save_stormglass_data(lat, lon, data)

    return data


# ------------------------------------------------------------
#  FETCH BIO / CHLOROPHYLL
# ------------------------------------------------------------
def get_bio_data(lat: float, lon: float):
    """
    Fetch chlorophyll (bio) data from Stormglass.
    Uses DB fallback and daily caching.
    """
    if not API_KEY:
        record = database_client.get_latest_stormglass_data(lat, lon)
        if record and record.get("chlorophyll") is not None:
            return {
                "hours": [{
                    "time": record["timestamp"],
                    "chlorophyll": {"sg": record["chlorophyll"]},
                }],
                "meta": {"source": "database-fallback"}
            }
        return None

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    lat_str = f"{lat:.2f}".replace(".", "_")
    lon_str = f"{lon:.2f}".replace(".", "_")

    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"sg_bio_{lat_str}_{lon_str}_{date_str}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    url = f"{API_ROOT}/bio/point"
    headers = {"Authorization": API_KEY}

    params = {
        "lat": lat,
        "lng": lon,
        "params": "chlorophyll",
        "start": now.isoformat(),
        "end": now.isoformat(),
        "source": "sg",
    }

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"Warning: Could not fetch bio data: {e}")
        return None

    # Save to cache
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Save to DB
    database_client.save_stormglass_data(lat, lon, data)

    return data