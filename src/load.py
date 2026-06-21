"""
load.py - Data Loading into PostgreSQL
Upserts with ON CONFLICT DO UPDATE for idempotent pipeline runs.
"""
import os, logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "nasa_bi"),
        user=os.getenv("POSTGRES_USER", "nasa_user"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )

def create_schema(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS asteroids (
        asteroid_id             VARCHAR(20) PRIMARY KEY,
        name                    TEXT,
        absolute_magnitude_h    FLOAT,
        est_diameter_min_km     FLOAT,
        est_diameter_max_km     FLOAT,
        est_diameter_avg_km     FLOAT,
        size_category           VARCHAR(30),
        is_potentially_hazardous BOOLEAN DEFAULT FALSE,
        is_sentry_object        BOOLEAN DEFAULT FALSE,
        nasa_jpl_url            TEXT,
        created_at              TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS close_approaches (
        id                  SERIAL PRIMARY KEY,
        asteroid_id         VARCHAR(20) REFERENCES asteroids(asteroid_id),
        close_approach_date DATE NOT NULL,
        orbiting_body       VARCHAR(20),
        velocity_kph        FLOAT,
        velocity_kps        FLOAT,
        miss_distance_km    FLOAT,
        miss_distance_lunar FLOAT,
        miss_distance_au    FLOAT,
        risk_score          FLOAT,
        week_of_year        INT,
        ingested_at         TIMESTAMP DEFAULT NOW(),
        UNIQUE (asteroid_id, close_approach_date)
    );
    CREATE INDEX IF NOT EXISTS idx_approaches_date ON close_approaches (close_approach_date);
    CREATE INDEX IF NOT EXISTS idx_approaches_hazardous ON asteroids (is_potentially_hazardous);
    """
    with conn.cursor() as cur: cur.execute(ddl)
    conn.commit()

def load_asteroids(conn, df):
    if df.empty: return 0
    cols = ["asteroid_id","name","absolute_magnitude_h","est_diameter_min_km","est_diameter_max_km",
            "est_diameter_avg_km","size_category","is_potentially_hazardous","is_sentry_object","nasa_jpl_url"]
    records = [tuple(row[c] for c in cols) for _, row in df[cols].iterrows()]
    sql = f"INSERT INTO asteroids ({', '.join(cols)}) VALUES %s ON CONFLICT (asteroid_id) DO UPDATE SET name=EXCLUDED.name, est_diameter_avg_km=EXCLUDED.est_diameter_avg_km, size_category=EXCLUDED.size_category, is_potentially_hazardous=EXCLUDED.is_potentially_hazardous"
    with conn.cursor() as cur: execute_values(cur, sql, records)
    conn.commit()
    return len(records)

def load_close_approaches(conn, df):
    if df.empty: return 0
    cols = ["asteroid_id","close_approach_date","orbiting_body","velocity_kph","velocity_kps",
            "miss_distance_km","miss_distance_lunar","miss_distance_au","risk_score","week_of_year"]
    df = df.copy()
    df["close_approach_date"] = df["close_approach_date"].dt.date
    records = [tuple(row[c] for c in cols) for _, row in df[cols].iterrows()]
    sql = f"INSERT INTO close_approaches ({', '.join(cols)}) VALUES %s ON CONFLICT (asteroid_id, close_approach_date) DO UPDATE SET velocity_kph=EXCLUDED.velocity_kph, miss_distance_km=EXCLUDED.miss_distance_km, miss_distance_lunar=EXCLUDED.miss_distance_lunar, risk_score=EXCLUDED.risk_score"
    with conn.cursor() as cur: execute_values(cur, sql, records)
    conn.commit()
    return len(records)

def run_load(asteroids_df, approaches_df):
    conn = get_connection()
    try:
        create_schema(conn)
        n_a = load_asteroids(conn, asteroids_df)
        n_c = load_close_approaches(conn, approaches_df)
        return {"asteroids": n_a, "close_approaches": n_c}
    finally:
        conn.close()
