# Visibility App (refactor)

Lightweight Flask app predicting underwater visibility using pre-trained models and weather/tide data.

Quick start

1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\\Scripts\\activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. (Optional) Override default DB path with environment variable

```bash
set VISIBILITY_DB_PATH=c:\\path\\to\\data\\visibility.db  # Windows
export VISIBILITY_DB_PATH=/path/to/data/visibility.db     # macOS/Linux
```

4. Run the app

```bash
python src/app.py
```

The app initializes the SQLite DB automatically on first import.

API examples

- Predict (manual):

```bash
curl -X POST http://127.0.0.1:5000/predict -H "Content-Type: application/json" -d '{"swell_height":1.0,"swell_period":10.0,"wind_speed":10.0,"wind_dir":180,"tide_height":0.0,"turbidity":1.0,"chlorophyll":0.5}'
```

Notes

- Use `VISIBILITY_DB_PATH` to control where the SQLite file is stored.
- Provide `WINDGURU_JSON_URL` or `WINDGURU_JSON_URL` env/relevant inputs for external fetch endpoints.
Visibility Prediction App

Overview
- Small prototype to predict water visibility (meters) from environmental features: swell, wind, tide, etc.

Quickstart

1) Create a virtualenv and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) Generate synthetic data and train model

```bash
# Global dataset and model
python src/data_generator.py --out data/visibility.csv --n 2000 --region GLOBAL
python src/train_model.py --data data/visibility.csv --out model/visibility_model.pkl

# UK-specific dataset and model
python src/data_generator.py --out data/visibility_uk.csv --n 2000 --region UK
python src/train_model.py --data data/visibility_uk.csv --region UK --out model/uk_visibility_model.pkl
```

3) Run the Flask app

```bash
# Default on port 5000
python src/app.py

# If port 5000 is busy, choose a different port
PORT=5001 python src/app.py
```

Open http://127.0.0.1:PORT (e.g., 5000 or 5001) and try predictions from the UI.
Use the Region dropdown (Global/UK) to route predictions to the relevant model. If a regional model is missing, the app falls back to the global model.

Notes
- Wind speed in the UI and API is now provided in knots; the server converts to m/s internally for the model.

Windguru integration
- Set an environment variable `WINDGURU_JSON_URL` to a JSON endpoint that returns Windguru-style data (or provide `{"url": "..."}` in the request body). Corporate networks may require `HTTP_PROXY`, `HTTPS_PROXY`, and `SSL_CERT_FILE`.
- Expected JSON keys include: `wind_speed_knots`, `wind_dir_deg`, `swell_height_m`, `swell_period_s`, `tide_height_m`, `turbidity`. Missing values are filled with sensible defaults.
- Example request:
```bash
curl -sS -X POST http://127.0.0.1:5000/predict_windguru \
	-H "Content-Type: application/json" \
	-d '{"region":"UK","url":"https://example.com/windguru.json"}'
```

Offline/testing mode (no external URL)
Real-time weather
- POST to `/weather` with `lat` and `lon` to get current conditions (Open-Meteo): wind (knots + m/s), wind direction, temperature, timestamp.
```bash
curl -sS -X POST http://127.0.0.1:5001/weather \
	-H "Content-Type: application/json" \
	-d '{"lat":51.5074, "lon":-0.1278}'
```
- Corporate networks may require `HTTP_PROXY`, `HTTPS_PROXY`, and `SSL_CERT_FILE` env vars for outbound requests.
- SSL verification options:
	- Provide a CA bundle path via `REQUESTS_CA_BUNDLE` (preferred) or `SSL_CERT_FILE` and restart the app.
	- For testing only, disable verification with `WEATHER_VERIFY=false` (not recommended for production).
```bash
export SSL_CERT_FILE=/Users/337897789/Certs/Cert-RBC.pem  # or REQUESTS_CA_BUNDLE
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
export HTTP_PROXY='http://<user>:<pass>@<proxy>:<port>'
export HTTPS_PROXY="$HTTP_PROXY"
HOST=127.0.0.1 PORT=5001 python src/app.py
```

UI presets
- On the homepage weather card, use the quick preset buttons to populate coordinates:
	- Jersey (49.2138, -2.1358)
	- Brighton (50.8225, -0.1372)
	- Cornwall/Newquay (50.4154, -5.0903)
	- Isle of Skye/Portree (57.4129, -6.1983)

Fetch weather + Predict
- Use the "Fetch weather + Predict" button to pull current wind (knots/direction) for the selected coordinates and automatically call `/predict` using the current form inputs (region, swell, tide, turbidity). The server converts knots to m/s internally.
 - Enable "Auto turbidity from wind" to estimate turbidity from wind (converted to m/s) and tide sign (adds a small boost when tide is negative). The app updates the turbidity field before prediction.
```bash
curl -sS -X POST http://127.0.0.1:5000/predict_windguru \
	-H "Content-Type: application/json" \
	-d '{
				"region":"UK",
				"data": {
					"wind_speed_knots": 15,
					"wind_dir_deg": 220,
					"swell_height_m": 1.2,
					"swell_period_s": 9,
					"tide_height_m": 0.1,
					"turbidity": 1.0
				}
			}'
```

Files
- `src/data_generator.py`: creates synthetic dataset
- `src/train_model.py`: trains and saves a model pipeline
- `src/app.py`: Flask API + UI

Next steps
- Replace synthetic data with real observations
- Improve features and model selection; add more regional models as needed
- Add CI and unit tests
