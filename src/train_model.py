#!/usr/bin/env python3
"""
Train a baseline or region-specific model and save the pipeline.

Examples:
    # Global model
    python src/train_model.py --data data/visibility.csv --out model/visibility_model.pkl

    # UK-specific model (expects a 'region' column with value 'UK')
    python src/train_model.py --data data/visibility_uk.csv --region UK --out model/uk_visibility_model.pkl
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Optional, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


DEFAULT_FEATURES = [
    "swell_height",
    "swell_period",
    "wind_speed",
    "wind_dir",
    "tide_height",
    "turbidity",
    "chlorophyll",
]


def ensure_out_dir(path: str) -> None:
    """Create output directory if needed. If path has no directory, use current dir."""
    dirpath = os.path.dirname(path) or "."
    os.makedirs(dirpath, exist_ok=True)


def validate_columns(df: pd.DataFrame, required: Sequence[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in data: {missing}")


def train(data_path: str, out_path: str, region: Optional[str] = None, features: Optional[Sequence[str]] = None) -> None:
    features = list(features or DEFAULT_FEATURES)

    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    if region:
        if "region" in df.columns:
            df = df[df["region"].astype(str).str.upper() == str(region).upper()]
            if df.shape[0] == 0:
                raise ValueError(f"No rows found for region '{region}' in {data_path}")
            print(f"Training on region='{region}' subset: {len(df)} rows")
        else:
            print("Warning: 'region' column not found; training on full dataset")

    # Validate target
    if "visibility" not in df.columns:
        raise ValueError("Target column 'visibility' not found in the dataset")

    # Validate features
    validate_columns(df, features)

    X = df[list(features)].copy()
    y = df["visibility"].copy()

    # Build pipeline
    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        RandomForestRegressor(n_estimators=100, random_state=42),
    )

    ensure_out_dir(out_path)

    # If too few samples, train on all data and warn
    if len(X) < 5:
        print(f"Warning: Only {len(X)} samples. Training on all data without test split.")
        pipeline.fit(X, y)
        joblib.dump(pipeline, out_path)
        # Save metadata (feature list)
        meta_path = os.path.splitext(out_path)[0] + ".meta.json"
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump({"features": features, "n_samples": int(len(X)), "region": region}, fh, indent=2)
        print(f"Saved model to {out_path}")
        print(f"Saved metadata to {meta_path}")
        print("Note: Add more dive logs with visibility measurements to improve model accuracy.")
        return

    # Standard train/test flow
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    rmse = float(np.sqrt(mse))
    r2 = r2_score(y_test, preds)

    joblib.dump(pipeline, out_path)
    meta_path = os.path.splitext(out_path)[0] + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"features": features, "n_samples": int(len(X)), "region": region, "rmse": rmse, "r2": r2}, fh, indent=2)

    print(f"Saved model to {out_path}")
    print(f"Saved metadata to {meta_path}")
    print(f"Test RMSE: {rmse:.3f}, R2: {r2:.3f}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train visibility model")
    p.add_argument("--data", default="data/visibility.csv", help="Path to CSV data")
    p.add_argument("--out", default="model/visibility_model.pkl", help="Output path for the trained model (pkl)")
    p.add_argument("--region", default=None, help="Optional region filter (e.g., UK)")
    p.add_argument("--features", default=None, help="Comma-separated feature names to use (overrides defaults)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    features = None
    if args.features:
        features = [f.strip() for f in args.features.split(",") if f.strip()]
    # Auto-adjust output filename for region if user left default
    out_path = args.out
    if args.region and args.out == "model/visibility_model.pkl":
        out_path = f"model/{str(args.region).lower()}_visibility_model.pkl"
        print(f"Auto-adjusting output path for region '{args.region}': {out_path}")

    train(args.data, out_path, args.region, features)