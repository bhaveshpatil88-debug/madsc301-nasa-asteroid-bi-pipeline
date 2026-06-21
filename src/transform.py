"""
transform.py - Data Cleaning & Feature Engineering
Produces: asteroids (dimension table) + close_approaches (fact table)
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

def flatten_neo_data(raw_neo_dict: dict) -> tuple:
    asteroid_rows, approach_rows = [], []
    for date_str, neo_list in raw_neo_dict.items():
        for neo in neo_list:
            diam = neo.get("estimated_diameter", {})
            km = diam.get("kilometers", {})
            asteroid_rows.append({
                "asteroid_id": neo.get("id"),
                "name": neo.get("name", "").strip("()").strip(),
                "absolute_magnitude_h": neo.get("absolute_magnitude_h"),
                "est_diameter_min_km": km.get("estimated_diameter_min"),
                "est_diameter_max_km": km.get("estimated_diameter_max"),
                "is_potentially_hazardous": neo.get("is_potentially_hazardous_asteroid", False),
                "is_sentry_object": neo.get("is_sentry_object", False),
                "nasa_jpl_url": neo.get("nasa_jpl_url"),
            })
            for approach in neo.get("close_approach_data", []):
                vel = approach.get("relative_velocity", {})
                dist = approach.get("miss_distance", {})
                approach_rows.append({
                    "asteroid_id": neo.get("id"),
                    "close_approach_date": approach.get("close_approach_date"),
                    "orbiting_body": approach.get("orbiting_body"),
                    "velocity_kph": float(vel.get("kilometers_per_hour", 0)),
                    "velocity_kps": float(vel.get("kilometers_per_second", 0)),
                    "miss_distance_km": float(dist.get("kilometers", 0)),
                    "miss_distance_lunar": float(dist.get("lunar", 0)),
                    "miss_distance_au": float(dist.get("astronomical", 0)),
                })
    asteroids_df = pd.DataFrame(asteroid_rows)
    approaches_df = pd.DataFrame(approach_rows)
    return _clean_asteroids(asteroids_df), _clean_approaches(approaches_df)

def _clean_asteroids(df):
    if df.empty: return df
    df = df.drop_duplicates(subset=["asteroid_id"])
    df["est_diameter_avg_km"] = (df["est_diameter_min_km"] + df["est_diameter_max_km"]) / 2
    df["size_category"] = pd.cut(df["est_diameter_avg_km"],
        bins=[0, 0.05, 0.14, 0.5, 1.0, np.inf],
        labels=["Micro (<50m)", "Small (50-140m)", "Medium (140-500m)", "Large (500m-1km)", "Giant (>1km)"],
        right=False).astype(str)
    df["is_potentially_hazardous"] = df["is_potentially_hazardous"].astype(bool)
    df["is_sentry_object"] = df["is_sentry_object"].astype(bool)
    return df.reset_index(drop=True)

def _clean_approaches(df):
    if df.empty: return df
    df["close_approach_date"] = pd.to_datetime(df["close_approach_date"], errors="coerce")
    df = df.dropna(subset=["asteroid_id", "close_approach_date", "miss_distance_km"])
    df = df[df["orbiting_body"] == "Earth"].copy()
    max_dist = df["miss_distance_km"].max() or 1
    max_vel = df["velocity_kph"].max() or 1
    df["risk_score"] = ((1 - df["miss_distance_km"] / max_dist) * 60 + (df["velocity_kph"] / max_vel) * 40).round(2)
    df["week_of_year"] = df["close_approach_date"].dt.isocalendar().week.astype(int)
    return df.reset_index(drop=True)

def save_to_csv(asteroids_df, approaches_df, output_dir="data/processed"):
    import os
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    asteroids_df.to_csv(f"{output_dir}/asteroids_{ts}.csv", index=False)
    approaches_df.to_csv(f"{output_dir}/close_approaches_{ts}.csv", index=False)
