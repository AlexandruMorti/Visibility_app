import os
import requests
from datetime import datetime, timezone
import json
try:
    from . import database_client
except ImportError:
    import database_client

API_KEY = os.environ.get("STORMGLASS_API_KEY")
API_ROOT = "https://api.stormglass.io/v2"
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.path.dirname(APP_ROOT), "data", "stormglass_cache")


def get_weather_and_tide(lat: float, lon: float):
    """
    Fetches weather and tide data from Stormglass.io, with daily caching.
    See: https://documentation.stormglass.io/
    """
    if not API_KEY:
        record = database_client.get_latest_stormglass_data(lat, lon)
        if record:
            # Convert the sqlite3.Row object to a dict that mimics the API response
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
                    "chlorophyll": {"sg": record.get("chlorophyll")},
                }],
                "meta": {
                    "source": "database-fallback"
                }
            }
        else:
            raise ValueError("STORMGLASS_API_KEY not set and no fallback data available in the database.")

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    # Sanitize lat/lon for filename
    lat_str = f"{lat:.2f}".replace(".", "_")
    lon_str = f"{lon:.2f}".replace(".", "_")
    cache_file = os.path.join(CACHE_DIR, f"sg_cache_{lat_str}_{lon_str}_{date_str}.json")

    os.makedirs(CACHE_DIR, exist_ok=True)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Also save to DB for long-term storage
                database_client.save_stormglass_data(lat, lon, data)
                return data
        except (json.JSONDecodeError, IOError):
            # Invalid cache file, proceed to fetch
            pass

    start_time = now.isoformat()
    params = [
        "airTemperature", "cloudCover", "rain", "swellDirection",
        "swellHeight", "swellPeriod", "waterTemperature", "waveDirection",
        "waveHeight", "wavePeriod", "windSpeed", "windDirection", "seaLevel"
    ]

    headers = {"Authorization": API_KEY}
    url = f"{API_ROOT}/weather/point"
    res = requests.get(
        url,
        params={
            "lat": lat,
            "lng": lon,
            "params": ",".join(params),
            "start": start_time,
            "end": start_time,
            "source": "sg",
        },
        headers=headers,
        proxies={},  # Bypass proxy - use empty dict to force direct connection
        verify=False,  # Insecure: bypass SSL certificate validation
    )
    res.raise_for_status()
    data = res.json()

    # Save to cache
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Also save to DB for long-term storage
    database_client.save_stormglass_data(lat, lon, data)

    return data


def get_bio_data(lat: float, lon: float):
    """
    Fetches biological/chlorophyll data from Stormglass.io bio endpoint.
    See: https://documentation.stormglass.io/
    """
    if not API_KEY:
        record = database_client.get_latest_stormglass_data(lat, lon)
        if record and record.get("chlorophyll") is not None:
            return {
                "hours": [{
                    "time": record["timestamp"],
                    "chlorophyll": {"sg": record["chlorophyll"]},
                }],
                "meta": {
                    "source": "database-fallback"
                }
            }
        else:
            # Return None if no data available - chlorophyll is optional
            return None

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    lat_str = f"{lat:.2f}".replace(".", "_")
    lon_str = f"{lon:.2f}".replace(".", "_")
    cache_file = os.path.join(CACHE_DIR, f"sg_bio_cache_{lat_str}_{lon_str}_{date_str}.json")

    os.makedirs(CACHE_DIR, exist_ok=True)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except (json.JSONDecodeError, IOError):
            pass

    start_time = now.isoformat()
    headers = {"Authorization": API_KEY}
    url = f"{API_ROOT}/bio/point"
    
    try:
        res = requests.get(
            url,
            params={
                "lat": lat,
                "lng": lon,
                "params": "chlorophyll",
                "start": start_time,
                "end": start_time,
                "source": "sg",
            },
            headers=headers,
            proxies={},
            verify=False,
        )
        res.raise_for_status()
        data = res.json()

        # Save to cache
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        return data
    except Exception as e:
        # Bio endpoint might not be available for all locations/subscriptions
        print(f"Warning: Could not fetch bio data: {e}")
        return None
