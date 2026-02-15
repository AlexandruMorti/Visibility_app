import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# Load dataset
df = pd.read_csv("dives_with_conditions.csv")

# Drop rows with missing values
df = df.dropna(subset=[
    "visibility_m",
    "wind_speed",
    "wind_dir",
    "wave_height",
    "wave_period"
])

# Encode wind direction as sin/cos
df["wind_dir_rad"] = np.deg2rad(df["wind_dir"])
df["wind_dir_sin"] = np.sin(df["wind_dir_rad"])
df["wind_dir_cos"] = np.cos(df["wind_dir_rad"])

# Features and target
features = ["wind_speed", "wave_height", "wave_period", "wind_dir_sin", "wind_dir_cos"]
X = df[features]
y = df["visibility_m"]

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Model
model = RandomForestRegressor(
    n_estimators=300,
    random_state=42
)
model.fit(X_train, y_train)

# Evaluation
y_pred = model.predict(X_test)
print("MAE:", mean_absolute_error(y_test, y_pred))
print("R²:", r2_score(y_test, y_pred))

# Save model
joblib.dump(model, "visibility_model.pkl")
print("Model saved to visibility_model.pkl")