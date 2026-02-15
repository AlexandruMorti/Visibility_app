from flask import Flask, render_template, request, redirect, url_for
import numpy as np
import joblib
import sqlite3
import pandas as pd
from datetime import datetime

app = Flask(__name__)
model = joblib.load("visibility_model.pkl")

@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None

    if request.method == "POST":
        wind_speed = float(request.form["wind_speed"])
        wind_dir = float(request.form["wind_dir"])
        wave_height = float(request.form["wave_height"])
        wave_period = float(request.form["wave_period"])

        # Convert wind direction to sin/cos
        dir_rad = np.deg2rad(wind_dir)
        wind_dir_sin = np.sin(dir_rad)
        wind_dir_cos = np.cos(dir_rad)

        X = np.array([[wind_speed, wave_height, wave_period, wind_dir_sin, wind_dir_cos]])
        prediction = model.predict(X)[0]

    return render_template("index.html", title="Predict Visibility", prediction=prediction)

@app.route("/dashboard")
def dashboard():
    import sqlite3
    import pandas as pd
    import plotly.express as px

    conn = sqlite3.connect("visibility.db")
    df = pd.read_sql_query("""
    SELECT 
        dives.date_time,
        dives.site_name,
        dives.visibility_m,
        dives.max_depth_m,
        dives.breath_hold_s,
        conditions.wind_speed,
        conditions.wind_dir,
        conditions.wave_height,
        conditions.wave_period,
        conditions.tide_height,
        conditions.tide_phase
    FROM dives
    JOIN conditions ON dives.id = conditions.dive_id
    ORDER BY dives.date_time ASC
""", conn)

    conn.close()

    df["date_time"] = pd.to_datetime(df["date_time"])

    fig_phase = px.box(
    df,
    x="tide_phase",
    y="visibility_m",
    color="tide_phase",
    title="Visibility vs Tide Phase"
)

    fig_depth = px.scatter(
    df,
    x="max_depth_m",
    y="visibility_m",
    color="site_name",
    title="Visibility vs Max Depth"
)
    fig_breath = px.scatter(
    df,
    x="breath_hold_s",
    y="visibility_m",
    color="site_name",
    title="Visibility vs Breath Hold (seconds)"
)


    # Line chart: visibility over time
    fig_visibility = px.line(
        df,
        x="date_time",
        y="visibility_m",
        color="site_name",
        title="Visibility Over Time"
    )

    # Scatter: visibility vs wave height
    fig_wave = px.scatter(
        df,
        x="wave_height",
        y="visibility_m",
        color="site_name",
        trendline="ols",
        title="Visibility vs Wave Height (ft)"
    )

    # Scatter: visibility vs wind speed
    fig_wind = px.scatter(
        df,
        x="wind_speed",
        y="visibility_m",
        color="site_name",
        trendline="ols",
        title="Visibility vs Wind Speed (knots)"
    )

    # Tide height over time
    fig_tide = px.line(
        df,
        x="date_time",
        y="tide_height",
        color="site_name",
        title="Tide Height Over Time (m)"
    )

    return render_template(
    "dashboard.html",
    title="Dashboard",
    visibility_plot=fig_visibility.to_html(full_html=False),
    wave_plot=fig_wave.to_html(full_html=False),
    wind_plot=fig_wind.to_html(full_html=False),
    tide_plot=fig_tide.to_html(full_html=False),
    phase_plot=fig_phase.to_html(full_html=False),
    depth_plot=fig_depth.to_html(full_html=False),
    breath_plot=fig_breath.to_html(full_html=False)
)


@app.route("/map")
def map_view():
    import sqlite3
    import pandas as pd

    conn = sqlite3.connect("visibility.db")
    conn.row_factory = sqlite3.Row

    df = pd.read_sql_query("""
        SELECT 
            dives.id,
            dives.date_time,
            dives.site_name,
            dives.visibility_m,
            dives.max_depth_m,
            dives.breath_hold_s,
            sites.lat,
            sites.lon,
            conditions.tide_phase,
            conditions.tide_height
        FROM dives
        JOIN sites ON dives.site_name = sites.site_name
        LEFT JOIN conditions ON dives.id = conditions.dive_id
        ORDER BY dives.date_time DESC
    """, conn)

    conn.close()

    return render_template("map.html", dives=df.to_dict(orient="records"))
@app.route("/add_dive", methods=["POST"])
def add_dive():
    site_name = request.form["site_name"]
    lat = float(request.form["lat"])
    lon = float(request.form["lon"])
    visibility = float(request.form["visibility"])
    notes = request.form["notes"]
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    max_depth = request.form.get("max_depth_m")
    breath_hold = request.form.get("breath_hold_s")


    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    # Ensure site exists in sites table
    cursor.execute("""
        INSERT OR IGNORE INTO sites (site_name, lat, lon)
        VALUES (?, ?, ?)
    """, (site_name, lat, lon))

    # Insert dive
    cursor.execute("""
        INSERT INTO dives (date_time, site_name, visibility_m, max_depth_m, breath_hold_s)
        VALUES (?, ?, ?, ?, ?)
    """, (date_time, site_name, visibility, max_depth, breath_hold))


    dive_id = cursor.lastrowid

    conn.commit()
    conn.close()

    # Fetch conditions for this dive
    from fetch_conditions import get_conditions
    cond = get_conditions(pd.to_datetime(date_time))

    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO conditions (dive_id, wind_speed, wind_dir, wave_height, wave_period, tide_height)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        dive_id,
        cond["wind_speed"],
        cond["wind_dir"],
        cond["wave_height"],
        cond["wave_period"],
        cond["tide_height"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("map_view"))

@app.route("/delete_dive/<int:dive_id>", methods=["POST"])
def delete_dive(dive_id):
    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    # Delete conditions first (foreign key)
    cursor.execute("DELETE FROM conditions WHERE dive_id = ?", (dive_id,))

    # Delete the dive
    cursor.execute("DELETE FROM dives WHERE id = ?", (dive_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("map_view"))

@app.route("/edit_dive/<int:dive_id>", methods=["GET"])
def edit_dive(dive_id):
    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT dives.id, dives.date_time, dives.site_name, dives.visibility_m, dives.notes,
               sites.lat, sites.lon
        FROM dives
        JOIN sites ON dives.site_name = sites.site_name
        WHERE dives.id = ?
    """, (dive_id,))
    
    dive = cursor.fetchone()
    conn.close()

    if not dive:
        return "Dive not found", 404

    dive_data = {
        "id": dive[0],
        "date_time": dive[1],
        "site_name": dive[2],
        "visibility_m": dive[3],
        "notes": dive[4],
        "lat": dive[5],
        "lon": dive[6]
    }

    return render_template("edit_dive.html", dive=dive_data, title="Edit Dive")

@app.route("/update_dive/<int:dive_id>", methods=["POST"])
def update_dive(dive_id):
    site_name = request.form["site_name"]
    visibility = float(request.form["visibility"])
    notes = request.form["notes"]

    conn = sqlite3.connect("visibility.db")
    cursor = conn.cursor()

    # Update dive
    cursor.execute("""
        UPDATE dives
        SET site_name = ?, visibility_m = ?, notes = ?
        WHERE id = ?
    """, (site_name, visibility, notes, dive_id))

    conn.commit()
    conn.close()

    return redirect(url_for("map_view"))

if __name__ == "__main__":
    app.run(debug=True)