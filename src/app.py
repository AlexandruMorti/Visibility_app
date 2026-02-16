from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

import json
import uuid
from datetime import datetime
import joblib
import os
import numpy as np
from typing import Optional
try:
    from . import windguru_client  # when running as a package
except Exception:
    import windguru_client  # when running src/app.py directly
try:
    from . import weather_client
except Exception:
    import weather_client
try:
    from . import stormglass_client
except Exception:
    import stormglass_client
try:
    from . import database_client
except Exception:
    import database_client

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(os.path.dirname(APP_ROOT), "model")
# Use dive visibility model (underwater) instead of atmospheric visibility
GLOBAL_MODEL_PATH = os.path.join(MODEL_DIR, "dive_visibility_model.pkl")
REGIONAL_MODELS = {
    # UK model will use the global dive model if uk_dive_visibility_model.pkl doesn't exist
    "UK": os.path.join(MODEL_DIR, "dive_visibility_model.pkl"),
}

# Simple storage for dives
DATA_DIR = os.path.join(os.path.dirname(APP_ROOT), "data")
DIVE_FILE = os.path.join(DATA_DIR, "dives.json")

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(APP_ROOT), "templates"),
    static_folder=os.path.join(os.path.dirname(APP_ROOT), "static"),
)


def _ensure_data_file():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(DIVE_FILE):
            with open(DIVE_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
    except Exception:
        pass


def load_dives():
    _ensure_data_file()
    try:
        with open(DIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_dives(dives):
    _ensure_data_file()
    with open(DIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(dives, f, ensure_ascii=False, indent=2)

# Load available models at startup (global + known regional)
models: dict[str, object] = {}
if os.path.exists(GLOBAL_MODEL_PATH):
    models["GLOBAL"] = joblib.load(GLOBAL_MODEL_PATH)
for region, path in REGIONAL_MODELS.items():
    if os.path.exists(path):
        models[region.upper()] = joblib.load(path)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/app")
def index():
    return render_template("index.html")


@app.route("/weather_page")
def weather_page():
    return render_template("weather.html")


@app.route("/dives_page")
def dives_page():
    return render_template("dives.html")


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json() or {}
    region = str(data.get("region", "GLOBAL")).upper()
    model = models.get(region) or models.get("GLOBAL")
    if model is None:
        return jsonify({"error": "Model not found. Train the model first: see README."}), 500
    
    # Check if lat/lon are provided to fetch Stormglass data
    lat = data.get("lat")
    lon = data.get("lon")
    stormglass_data = None
    chlorophyll = None
    data_source = "manual"
    
    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
            # Fetch Stormglass weather/tide data for this location
            raw_sg_data = stormglass_client.get_weather_and_tide(lat, lon)
            stormglass_data = raw_sg_data["hours"][0]
            
            # Try to fetch bio/chlorophyll data
            try:
                bio_data = stormglass_client.get_bio_data(lat, lon)
                if bio_data and bio_data.get("hours"):
                    chlorophyll_val = bio_data["hours"][0].get("chlorophyll", {}).get("sg")
                    if chlorophyll_val is not None:
                        chlorophyll = float(chlorophyll_val)
                        # Update database with chlorophyll value
                        timestamp = stormglass_data.get("time")
                        if timestamp:
                            database_client.update_chlorophyll(lat, lon, timestamp, chlorophyll)
            except Exception as e:
                print(f"Warning: Could not fetch chlorophyll data: {e}")
            
            data_source = "hybrid"
        except Exception as e:
            # If Stormglass fetch fails, continue with manual input only
            print(f"Warning: Could not fetch Stormglass data: {e}")
            pass
    
    try:
        # Convert wind speed provided in knots to meters/second for the model
        KNOT_TO_MS = 0.514444
        
        # If Stormglass data available, use it as defaults, allow user overrides
        if stormglass_data:
            swell_height = float(data.get("swell_height") or stormglass_data["swellHeight"]["sg"])
            swell_period = float(data.get("swell_period") or stormglass_data["swellPeriod"]["sg"])
            
            # Wind speed: Stormglass provides in m/s, user provides in knots
            if data.get("wind_speed"):
                wind_speed_knots = float(data["wind_speed"])
                wind_speed_ms = wind_speed_knots * KNOT_TO_MS
            else:
                wind_speed_ms = float(stormglass_data["windSpeed"]["sg"])
            
            wind_dir = float(data.get("wind_dir") or stormglass_data["windDirection"]["sg"])
            tide_height = float(data.get("tide_height") or stormglass_data["seaLevel"]["sg"])
            
            # Chlorophyll: use user value or fetched value
            if data.get("chlorophyll"):
                chlorophyll_val = float(data["chlorophyll"])
            elif chlorophyll is not None:
                chlorophyll_val = chlorophyll
            elif stormglass_data.get("chlorophyll", {}).get("sg") is not None:
                chlorophyll_val = float(stormglass_data["chlorophyll"]["sg"])
            else:
                chlorophyll_val = 0.5  # Default moderate chlorophyll level (mg/m³)
            
            # Turbidity: use user value or estimate from conditions
            if data.get("turbidity"):
                turbidity = float(data["turbidity"])
            else:
                turbidity = 1.0 + 0.15 * max(0, wind_speed_ms - 5.0) + (1 if tide_height < 0 else 0)
                turbidity = min(10.0, max(0.2, turbidity))
        else:
            # Pure manual input
            wind_speed_knots = float(data["wind_speed"])
            wind_speed_ms = wind_speed_knots * KNOT_TO_MS
            swell_height = float(data["swell_height"])
            swell_period = float(data["swell_period"])
            wind_dir = float(data.get("wind_dir", 0.0))
            tide_height = float(data["tide_height"])
            turbidity = float(data.get("turbidity", 1.0))
            chlorophyll_val = float(data.get("chlorophyll", 0.5))
        
        features = [
            swell_height,
            swell_period,
            wind_speed_ms,
            wind_dir,
            tide_height,
            turbidity,
            chlorophyll_val,
        ]
    except Exception as e:
        return jsonify({"error": f"Invalid input: {e}"}), 400

    X = np.array(features).reshape(1, -1)
    pred = model.predict(X)[0]
    
    response = {
        "visibility_m": float(pred),
        "region": region,
        "data_source": data_source,
        "features": {
            "swell_height": swell_height,
            "swell_period": swell_period,
            "wind_speed_ms": wind_speed_ms,
            "wind_dir": wind_dir,
            "tide_height": tide_height,
            "turbidity": turbidity,
            "chlorophyll": chlorophyll_val,
        }
    }
    
    return jsonify(response)


@app.route("/predict_windguru", methods=["POST"])
def predict_windguru():
    # Accept JSON: { "url": "https://..." , "region": "UK" }
    # Or offline test: { "data": { ...windguru-like fields... }, "region": "UK" }
    payload = request.get_json() or {}
    url = payload.get("url") or os.environ.get("WINDGURU_JSON_URL")
    region = str(payload.get("region", "GLOBAL")).upper()
    model = models.get(region) or models.get("GLOBAL")
    if model is None:
        return jsonify({"error": "Model not found. Train the model first: see README."}), 500
    raw = None
    mapped = None
    if payload.get("data"):
        # Use provided JSON object directly (offline/testing mode)
        try:
            raw = payload["data"]
            mapped = windguru_client.map_features(raw)
        except Exception as e:
            return jsonify({"error": f"Failed to parse provided data: {e}"}), 400
    else:
        if not url:
            return jsonify({"error": "Missing 'url' to fetch Windguru JSON. Provide in request or set WINDGURU_JSON_URL env."}), 400
        try:
            raw = windguru_client.fetch_windguru_json(url)
            mapped = windguru_client.map_features(raw)
        except Exception as e:
            return jsonify({"error": f"Failed to fetch/map Windguru data: {e}"}), 502

    # Fill defaults if missing
    def dval(x: Optional[float], default: float) -> float:
        return float(default if x is None else x)

    swell_height = dval(mapped.get("swell_height"), 1.0)
    swell_period = dval(mapped.get("swell_period"), 10.0)
    wind_speed = dval(mapped.get("wind_speed"), 5.0)  # already m/s
    wind_dir = dval(mapped.get("wind_dir"), 180.0)
    tide_height = dval(mapped.get("tide_height"), 0.0)
    turbidity = dval(mapped.get("turbidity"), 1.0)
    chlorophyll = dval(mapped.get("chlorophyll"), 0.5)

    X = np.array([[
        swell_height,
        swell_period,
        wind_speed,
        wind_dir,
        tide_height,
        turbidity,
        chlorophyll,
    ]])
    pred = model.predict(X)[0]
    return jsonify({
        "visibility_m": float(pred),
        "region": region,
        "source": "windguru",
        "features": {
            "swell_height": swell_height,
            "swell_period": swell_period,
            "wind_speed_ms": wind_speed,
            "wind_dir": wind_dir,
            "tide_height": tide_height,
            "turbidity": turbidity,
            "chlorophyll": chlorophyll,
        },
        "raw": raw,
    })


@app.route("/weather", methods=["POST"])
def weather():
    # Accept JSON: { "lat": <float>, "lon": <float> }
    payload = request.get_json() or {}
    try:
        lat = float(payload.get("lat"))
        lon = float(payload.get("lon"))
    except Exception:
        return jsonify({"error": "Missing or invalid 'lat'/'lon'"}), 400

    try:
        data = weather_client.get_current_weather(lat, lon)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch weather: {e}"}), 502

    return jsonify({
        "source": "open-meteo",
        "lat": lat,
        "lon": lon,
        "time": data.get("time"),
        "temperature_2m": data.get("temperature_2m"),
        "wind_speed_knots": data.get("wind_speed_knots"),
        "wind_speed_ms": data.get("wind_speed_ms"),
        "wind_direction_deg": data.get("wind_direction_10m"),
        "raw": data.get("raw"),
    })


@app.route("/predict_stormglass", methods=["POST"])
def predict_stormglass():
    payload = request.get_json() or {}
    try:
        lat = float(payload.get("lat"))
        lon = float(payload.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "Missing or invalid 'lat'/'lon'"}), 400

    region = str(payload.get("region", "GLOBAL")).upper()
    model = models.get(region) or models.get("GLOBAL")
    if model is None:
        return jsonify({"error": "Model not found. Train the model first: see README."}), 500

    try:
        raw_data = stormglass_client.get_weather_and_tide(lat, lon)
        # First hour of data
        sg_data = raw_data["hours"][0]

        # Stormglass provides wind speed in m/s, which is what the model expects
        wind_speed_ms = float(sg_data["windSpeed"]["sg"])
        swell_height = float(sg_data["swellHeight"]["sg"])
        swell_period = float(sg_data["swellPeriod"]["sg"])
        wind_dir = float(sg_data["windDirection"]["sg"])
        # seaLevel is tide height
        tide_height = float(sg_data["seaLevel"]["sg"])
        
        # Estimate turbidity from wind and tide
        turbidity = 1.0 + 0.15 * max(0, wind_speed_ms - 5.0) + (1 if tide_height < 0 else 0)
        turbidity = min(10.0, max(0.2, turbidity))
        
        # Use default chlorophyll if not available
        chlorophyll = 0.5

        features = [
            swell_height,
            swell_period,
            wind_speed_ms,
            wind_dir,
            tide_height,
            turbidity,
            chlorophyll,
        ]
        X = np.array(features).reshape(1, -1)
        prediction = model.predict(X)[0]

        return jsonify({
            "visibility_m": float(prediction),
            "region": region,
            "source": "stormglass",
            "features": {
                "swell_height": swell_height,
                "swell_period": swell_period,
                "wind_speed_ms": wind_speed_ms,
                "wind_dir": wind_dir,
                "tide_height": tide_height,
                "turbidity": turbidity,
                "chlorophyll": chlorophyll,
            },
            "raw": sg_data,
        })

    except Exception as e:
        return jsonify({"error": f"Failed to get prediction from Stormglass: {e}"}), 502


@app.route("/dives", methods=["GET"])
def get_dives():
    dives = load_dives()
    return jsonify(dives)


@app.route("/dives", methods=["POST"])
def add_dive():
    payload = request.get_json() or {}
    try:
        lat = float(payload.get("lat"))
        lon = float(payload.get("lon"))
    except Exception:
        return jsonify({"error": "Missing or invalid 'lat'/'lon'"}), 400

    # Optional fields
    date = payload.get("date") or datetime.utcnow().isoformat()
    depth = payload.get("depth")
    notes = payload.get("notes") or ""
    tide_height = payload.get("tide_height")
    breath_hold_time = payload.get("breath_hold_time")
    visibility = payload.get("visibility")
    water_temp = payload.get("water_temp")
    outside_temp = payload.get("outside_temp")

    dive = {
        "id": str(uuid.uuid4()),
        "lat": lat,
        "lon": lon,
        "date": date,
        "depth": depth,
        "notes": notes,
        "tide_height": tide_height,
        "breath_hold_time": breath_hold_time,
        "visibility": visibility,
        "water_temp": water_temp,
        "outside_temp": outside_temp,
        "created_at": datetime.utcnow().isoformat(),
    }

    dives = load_dives()
    dives.append(dive)
    save_dives(dives)
    return jsonify(dive), 201


@app.route("/dives/<dive_id>", methods=["PUT"])
def update_dive(dive_id):
    payload = request.get_json() or {}
    dives = load_dives()
    
    # Find the dive to update
    dive_index = None
    for i, d in enumerate(dives):
        if d.get("id") == dive_id:
            dive_index = i
            break
    
    if dive_index is None:
        return jsonify({"error": "Dive not found"}), 404
    
    # Update fields if provided
    dive = dives[dive_index]
    if "lat" in payload:
        try:
            dive["lat"] = float(payload["lat"])
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid lat"}), 400
    if "lon" in payload:
        try:
            dive["lon"] = float(payload["lon"])
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid lon"}), 400
    if "date" in payload:
        dive["date"] = payload["date"]
    if "depth" in payload:
        dive["depth"] = payload["depth"]
    if "notes" in payload:
        dive["notes"] = payload["notes"]
    if "tide_height" in payload:
        dive["tide_height"] = payload["tide_height"]
    if "breath_hold_time" in payload:
        dive["breath_hold_time"] = payload["breath_hold_time"]
    if "visibility" in payload:
        dive["visibility"] = payload["visibility"]
    if "water_temp" in payload:
        dive["water_temp"] = payload["water_temp"]
    if "outside_temp" in payload:
        dive["outside_temp"] = payload["outside_temp"]
    
    dive["updated_at"] = datetime.utcnow().isoformat()
    
    dives[dive_index] = dive
    save_dives(dives)
    return jsonify(dive), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port, debug=True)
