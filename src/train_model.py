"""Train a baseline or region-specific model and save the pipeline.
Run:
    # Global model
    python src/train_model.py --data data/visibility.csv --out model/visibility_model.pkl

    # UK-specific model (expects a 'region' column with value 'UK')
    python src/train_model.py --data data/visibility_uk.csv --region UK --out model/uk_visibility_model.pkl
"""
import argparse
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score


def train(data_path, out_path, region: str | None = None):
    df = pd.read_csv(data_path)
    if region:
        col = "region"
        if col in df.columns:
            df = df[df[col].str.upper() == str(region).upper()]
            if len(df) == 0:
                raise ValueError(f"No rows found for region '{region}' in {data_path}")
            print(f"Training on region='{region}' subset: {len(df)} rows")
        else:
            print("Warning: 'region' column not found; training on full dataset")
    X = df[["swell_height", "swell_period", "wind_speed", "wind_dir", "tide_height", "turbidity", "chlorophyll"]]
    y = df["visibility"]

    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        RandomForestRegressor(n_estimators=100, random_state=42),
    )

    # Check if we have enough samples for splitting
    if len(X) < 5:
        print(f"Warning: Only {len(X)} samples. Training on all data without test split.")
        pipeline.fit(X, y)
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        joblib.dump(pipeline, out_path)
        
        print(f"Saved model to {out_path}")
        print(f"Note: Add more dive logs with visibility measurements to improve model accuracy.")
    else:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        pipeline.fit(X_train, y_train)

        preds = pipeline.predict(X_test)
        # Compute RMSE without using the 'squared' argument for compatibility
        mse = mean_squared_error(y_test, preds)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_test, preds)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        joblib.dump(pipeline, out_path)

        print(f"Saved model to {out_path}")
        print(f"Test RMSE: {rmse:.3f}, R2: {r2:.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/visibility.csv")
    p.add_argument("--out", default="model/visibility_model.pkl")
    p.add_argument("--region", default=None, help="Optional region filter (e.g., UK)")
    args = p.parse_args()
    # If a region is provided and user didn't override out path, auto-adjust filename
    auto_out = args.out
    if args.region and args.out == "model/visibility_model.pkl":
        auto_out = f"model/{str(args.region).lower()}_visibility_model.pkl"
        print(f"Auto-adjusting output path for region '{args.region}': {auto_out}")
    train(args.data, auto_out, args.region)
