# NASA Asteroid Risk Intelligence — BI Pipeline

**Course:** MADSC301 — Business Intelligence | EU Business School Munich  
**Student:** Bhavesh Patil  
**Lecturer:** Hachem Sfar  
**Term:** Term 3, AY 2025/26  

---

## What This Is

NASA publishes a live feed of every asteroid that passes near Earth — how big it is, how fast it's moving, how close it'll get. That data is publicly available but raw, nested, and not particularly useful on its own.

This project turns that raw feed into something you can actually act on. It pulls data from the NASA NeoWs API, cleans and enriches it with computed risk metrics, loads it into a structured PostgreSQL database, and serves it through a live Grafana dashboard — automatically, every day.

The pipeline is fully automated via Apache Airflow. Running it manually once is enough to populate the dashboard; after that, it runs itself.

---

## What I Built

A complete ETL pipeline with four stages:

**1. Extract** — Calls the NASA NeoWs REST API in 7-day chunks (the API's max per request), handles pagination and rate limiting, and returns raw JSON.

**2. Transform** — Flattens the deeply nested JSON into two clean tables. Engineers two new features that NASA doesn't provide:
- **Risk Score (0–100):** combines miss distance (60% weight) and approach velocity (40% weight) into a single composite metric
- **Size Category:** classifies each asteroid from Micro (<50m) to Giant (>1km)

**3. Load** — Upserts into PostgreSQL using `ON CONFLICT DO UPDATE`. Running the pipeline twice doesn't duplicate data — it just refreshes it. This is the property that makes scheduled automation safe.

**4. Visualise** — A 12-panel Grafana dashboard showing live stats, risk distributions, hazard classifications, and the top 20 highest-risk approaches ranked by the computed score.

---

## Results From the Live Pipeline

After running the pipeline on the current 30-day window:

- **40 asteroids** tracked in the current period
- **2 classified as Potentially Hazardous** by NASA
- **Max risk score: 80.7 / 100** — one asteroid is both fast and close
- **Closest approach: 3.7 Lunar Distances** (~1.4 million km from Earth)
- **Most common size class: Micro (<50m)**, which accounts for ~60% of tracked objects

---

## Architecture

```
NASA NeoWs API
      │
      ▼
src/extract.py      ← HTTP requests, 7-day chunks, rate limiting
      │
      ▼
src/transform.py    ← JSON flattening, null handling, risk score, size category
      │
      ▼
src/load.py         ← PostgreSQL upserts, star schema
      │
      ├──▶ Grafana Dashboard (localhost:3000)
      └──▶ Jupyter Notebook (exploratory analysis + ML)

Orchestration: Apache Airflow DAG → daily at 06:00 UTC
```

---

## Database Schema

Two tables — one for the asteroids themselves, one for each close approach event.

### `asteroids` (dimension)

| Column | Type | Description |
|---|---|---|
| asteroid_id | VARCHAR PK | NASA's unique identifier (e.g. `3542519`) |
| name | TEXT | Designation or name (e.g. `2021 QF`) |
| absolute_magnitude_h | FLOAT | Intrinsic brightness — lower = physically larger |
| est_diameter_avg_km | FLOAT | Average of min/max diameter estimates |
| size_category | VARCHAR | Micro / Small / Medium / Large / Giant |
| is_potentially_hazardous | BOOLEAN | >140m AND passes within 0.05 AU of Earth |
| is_sentry_object | BOOLEAN | On NASA's Sentry impact-monitoring watchlist |

### `close_approaches` (fact)

| Column | Type | Description |
|---|---|---|
| asteroid_id | FK → asteroids | The asteroid making this approach |
| close_approach_date | DATE | Date of the closest point |
| velocity_kph | FLOAT | Speed relative to Earth (km/h) |
| miss_distance_km | FLOAT | Closest distance in kilometres |
| miss_distance_lunar | FLOAT | Distance in Lunar units (1 LD ≈ 384,400 km) |
| risk_score | FLOAT | Computed composite score, 0–100 |

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (or Postgres.app on Mac)
- Grafana (local install via Homebrew: `brew install grafana`)

### 1. Clone and set up

```bash
git clone https://github.com/bhaveshpatil88-debug/madsc301-nasa-asteroid-bi-pipeline.git
cd madsc301-nasa-asteroid-bi-pipeline

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your PostgreSQL connection details
```

### 2. Run the pipeline

```bash
python3 src/pipeline.py
```

That's it. The pipeline extracts the last 30 days, transforms the data, and loads it into PostgreSQL.

To see the coloured step-by-step output during a demo:
```bash
python3 demo_pipeline.py
```

### 3. Open the dashboard

Start Grafana, then open `http://localhost:3000` and import `grafana/nasa_asteroid_dashboard.json`.

Full setup instructions are in [GRAFANA_SETUP.md](GRAFANA_SETUP.md).

### 4. Enable automation (optional)

```bash
docker-compose up -d airflow-init airflow-scheduler airflow-webserver
# Open http://localhost:8080 → enable DAG: nasa_neo_etl_pipeline
```

---

## Project Structure

```
nasa-bi-pipeline/
├── src/
│   ├── extract.py       # NASA API calls, rate limiting, chunking
│   ├── transform.py     # JSON flattening, feature engineering
│   ├── load.py          # PostgreSQL schema creation, upserts
│   └── pipeline.py      # Runs all three in sequence
├── dags/
│   └── nasa_etl_dag.py  # Airflow DAG, daily schedule, email alerts
├── grafana/
│   └── nasa_asteroid_dashboard.json  # 12-panel dashboard, import-ready
├── notebooks/
│   └── analysis.ipynb   # EDA + Random Forest hazard classifier
├── sql/
│   └── schema.sql       # Table definitions, indexes, views
├── demo_pipeline.py     # Coloured terminal output for live demos
├── Dockerfile           # Containerised ETL pipeline
├── docker-compose.yml   # PostgreSQL + Airflow stack
├── requirements.txt
├── .env.example
└── GRAFANA_SETUP.md     # Step-by-step Grafana dashboard setup
```

---

## Design Decisions

**Why a risk score?** NASA provides raw numbers — distance and velocity separately — but not a unified signal. I wanted a single metric a decision-maker could act on, similar to how a credit score combines multiple factors. The 60/40 weighting reflects that proximity is the more critical variable for collision risk.

**Why upserts instead of inserts?** The pipeline runs daily. Without `ON CONFLICT DO UPDATE`, re-running it on the same date range would duplicate every row. Upserts make the pipeline idempotent — safe to run repeatedly with predictable, consistent results.

**Why PostgreSQL instead of a flat file?** Grafana connects natively to PostgreSQL and can run SQL queries against it in real time. A CSV can't do that. The relational model also lets me join asteroids to close approaches and slice the data in ways that would require manual filtering in a spreadsheet.

---

## Bonus Features

- Machine learning: Random Forest classifier for hazard prediction (>90% ROC-AUC on test set) — see the notebook
- Docker: full `Dockerfile` + `docker-compose.yml` for portable deployment
- Airflow: production-style DAG with retries, XCom data passing, and `EmailOperator` failure alerts
- Idempotent pipeline: safe to run multiple times with no side effects

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data source | NASA NeoWs REST API |
| Language | Python 3.11 |
| Data processing | Pandas, NumPy |
| Database | PostgreSQL 15 |
| Orchestration | Apache Airflow 2.8 |
| Visualisation | Grafana 10, Matplotlib, Seaborn |
| Machine learning | scikit-learn (Random Forest) |
| Containerisation | Docker, docker-compose |
| Notebook | Jupyter |

---

## NASA API Reference

- Base URL: `https://api.nasa.gov/neo/rest/v1/feed`
- Free API key: [api.nasa.gov](https://api.nasa.gov/) — 1,000 requests/hour
- DEMO_KEY: 30 requests/hour — sufficient for testing and demos
- Max date range per request: 7 days (enforced by NASA, handled in `extract.py`)
