"""Synthetic data generator for water visibility prediction
Run:
    python src/data_generator.py --out data/visibility.csv --n 2000
    # Generate UK-specific distribution
    python src/data_generator.py --out data/visibility_uk.csv --n 2000 --region UK
"""
import argparse
import numpy as np
import pandas as pd


def generate_data(n=1000, seed=42, region="GLOBAL"):
    rng = np.random.default_rng(seed)
    region = str(region).upper()
    # Environmental features (adjust simple ranges for UK coastal waters)
    if region == "UK":
        swell_height = rng.uniform(0.0, 2.5, n)          # meters
        swell_period = rng.uniform(5.0, 14.0, n)         # seconds
        wind_speed = rng.uniform(0.0, 22.0, n)           # m/s
        wind_dir = rng.uniform(0.0, 360.0, n)            # degrees
        tide_height = rng.uniform(-2.0, 2.0, n)          # meters
    else:
        swell_height = rng.uniform(0.0, 3.0, n)          # meters
        swell_period = rng.uniform(4.0, 18.0, n)         # seconds
        wind_speed = rng.uniform(0.0, 25.0, n)           # m/s
        wind_dir = rng.uniform(0.0, 360.0, n)            # degrees
        tide_height = rng.uniform(-1.5, 2.5, n)          # meters

    # Derive turbidity (higher when wind strong or negative tide stirring sediments)
    turbidity = 1.0 + 0.15 * np.maximum(0, wind_speed - 5.0) + 0.5 * (tide_height < 0)
    turbidity += rng.normal(0, 0.2, n)
    turbidity = np.clip(turbidity, 0.2, 10.0)

    # Generate visibility (meters) with an underlying physical-inspired formula + noise
    base_visibility = 30.0
    visibility = (
        base_visibility
        - 6.0 * turbidity
        - 3.0 * swell_height
        + 0.4 * swell_period
        - 0.1 * wind_speed
        - 0.8 * tide_height
    )
    visibility += rng.normal(0, 2.0, n)  # measurement noise
    visibility = np.clip(visibility, 0.5, 60.0)

    df = pd.DataFrame({
        "swell_height": swell_height,
        "swell_period": swell_period,
        "wind_speed": wind_speed,
        "wind_dir": wind_dir,
        "tide_height": tide_height,
        "turbidity": turbidity,
        "visibility": visibility,
    })
    df["region"] = region
    return df


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="data/visibility.csv")
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--region", default="GLOBAL", help="Region label (e.g., GLOBAL or UK)")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    df = generate_data(args.n, seed=args.seed, region=args.region)
    # ensure folder
    import os
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out} (region={args.region})")
