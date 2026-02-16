#!/usr/bin/env python3
"""
Export training data from dive logs and Stormglass database.
Combines dive visibility measurements with environmental conditions.
"""
import os
import json
import sys
import argparse
import csv
from datetime import datetime, timedelta
try:
    from . import database_client
except ImportError:
    import database_client

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(APP_ROOT), "data")
DIVE_FILE = os.path.join(DATA_DIR, "dives.json")


def load_dives():
    """Load dive data from JSON file."""
    try:
        with open(DIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def get_closest_stormglass_data(lat, lon, timestamp_str):
    """
    Find the closest Stormglass data record for a given location and time.
    Searches within +/- 6 hours of the dive time.
    """
    conn = database_client.get_db_connection()
    cursor = conn.cursor()
    
    # Parse the dive timestamp
    try:
        dive_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except:
        return None
    
    # Search within +/- 6 hours
    start_time = (dive_time - timedelta(hours=6)).isoformat()
    end_time = (dive_time + timedelta(hours=6)).isoformat()
    
    # Find the closest record by location and time
    cursor.execute("""
        SELECT * FROM stormglass_data
        WHERE lat = ? AND lon = ?
        AND timestamp BETWEEN ? AND ?
        ORDER BY ABS(julianday(timestamp) - julianday(?))
        LIMIT 1
    """, (lat, lon, start_time, end_time, dive_time.isoformat()))
    
    record = cursor.fetchone()
    conn.close()
    return record


def export_training_data(output_file):
    """
    Export training data by combining dives with Stormglass data.
    Only exports dives that have visibility measurements.
    Uses estimated values when Stormglass data is not available.
    """
    dives = load_dives()
    
    # Filter dives that have visibility data
    dives_with_visibility = [
        d for d in dives 
        if d.get('visibility') is not None and d.get('visibility') != ''
    ]
    
    if not dives_with_visibility:
        print("No dives with visibility measurements found.")
        return 0
    
    print(f"Found {len(dives_with_visibility)} dives with visibility data.")
    
    training_data = []
    estimated_count = 0
    
    for dive in dives_with_visibility:
        lat = dive.get('lat')
        lon = dive.get('lon')
        date = dive.get('date')
        visibility = dive.get('visibility')
        
        if not all([lat, lon, date, visibility]):
            continue
        
        # Convert visibility to float
        try:
            vis_value = float(visibility)
        except (ValueError, TypeError):
            continue
        
        # Try to find matching Stormglass data
        sg_record = get_closest_stormglass_data(lat, lon, date)
        
        if sg_record:
            # Use actual Stormglass data
            wind_speed = sg_record['wind_speed'] or 5.0
            tide = sg_record['tide_height'] or 0.0
            turbidity = 1.0 + 0.15 * max(0, wind_speed - 5.0) + (0.5 if tide < 0 else 0)
            turbidity = min(10.0, max(0.2, turbidity))
            chlorophyll = sg_record['chlorophyll'] or 0.5
            
            row = {
                'swell_height': sg_record['swell_height'] or 1.0,
                'swell_period': sg_record['swell_period'] or 10.0,
                'wind_speed': wind_speed,
                'wind_dir': sg_record['wind_direction'] or 180.0,
                'tide_height': tide,
                'turbidity': turbidity,
                'chlorophyll': chlorophyll,
                'visibility': vis_value
            }
            training_data.append(row)
        else:
            # Use estimated values based on dive conditions
            print(f"  Using estimated values for dive at {lat:.4f}, {lon:.4f} on {date}")
            estimated_count += 1
            
            # Use dive's own measurements if available, otherwise use defaults
            water_temp = dive.get('water_temp') if dive.get('water_temp') else 12.0
            tide_height = dive.get('tide_height') if dive.get('tide_height') else 0.0
            
            # Estimate conditions based on visibility
            # Good visibility (>8m) suggests calm conditions
            # Poor visibility (<5m) suggests rough conditions
            if vis_value >= 8:
                # Calm conditions
                swell_height = 0.5
                wind_speed = 3.0
                turbidity = 0.5
                chlorophyll = 0.3  # Low algae
            elif vis_value >= 5:
                # Moderate conditions
                swell_height = 1.0
                wind_speed = 5.0
                turbidity = 1.5
                chlorophyll = 0.8  # Moderate algae
            else:
                # Rough conditions
                swell_height = 1.5
                wind_speed = 8.0
                turbidity = 3.0
                chlorophyll = 2.0  # High algae/plankton
            
            row = {
                'swell_height': swell_height,
                'swell_period': 10.0,
                'wind_speed': wind_speed,
                'wind_dir': 180.0,  # Default neutral direction
                'tide_height': tide_height,
                'turbidity': turbidity,
                'chlorophyll': chlorophyll,
                'visibility': vis_value
            }
            training_data.append(row)
    
    if not training_data:
        print("No training data could be generated.")
        return 0
    
    if estimated_count > 0:
        print(f"  Note: {estimated_count} of {len(training_data)} records use estimated conditions")
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['swell_height', 'swell_period', 'wind_speed', 'wind_dir', 'tide_height', 'turbidity', 'chlorophyll', 'visibility']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(training_data)
    
    print(f"Exported {len(training_data)} training records to {output_file}")
    return len(training_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export training data from dive logs")
    parser.add_argument(
        "--out",
        type=str,
        default=os.path.join(DATA_DIR, "dive_training_data.csv"),
        help="Output CSV file path"
    )
    args = parser.parse_args()
    
    count = export_training_data(args.out)
    if count > 0:
        print(f"\nTo train the model with this data, run:")
        print(f"  python src/train_model.py --data {args.out} --out model/dive_visibility_model.pkl")
    sys.exit(0 if count > 0 else 1)
