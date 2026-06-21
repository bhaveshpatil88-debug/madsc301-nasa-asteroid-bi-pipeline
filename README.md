# NASA Asteroid Risk Intelligence — BI Pipeline

**Course:** MADSC301 — Business Intelligence | EU Business School Munich
**Student:** Bhavesh Patil | **Term:** Term 3, AY 2025/26

---

## Business Case

NASA tracks hundreds of Near-Earth Objects (asteroids) approaching Earth every week.
This project builds an **end-to-end Business Intelligence pipeline** producing actionable intelligence for:
- Satellite operators (collision-risk avoidance)
- Planetary defence agencies (threat prioritisation)
- Space insurance companies (catastrophic risk modelling)

---

## Pipeline Architecture

```
NASA NeoWs API --> Extract (src/extract.py) --> Transform (src/transform.py) --> Load (PostgreSQL)
                                                                                       |
                                                                              Grafana Dashboard
                                                                         (12 live panels, port 3000)
```

**Data Flow:**
1. **Extract** — Calls NASA NeoWs REST API (daily schedule, 7-day chunks, rate-limited)
2. **Transform** — Flattens JSON, cleans nulls, engineers features (risk score 0-100, size category)
3. **Load** — Upserts into PostgreSQL (asteroids + close_approaches tables, idempotent ON CONFLICT)
4. **Visualise** — Grafana 12-panel live dashboard (key metrics, trends, risk map, top-10 table)
5. **Orchestrate** — Apache Airflow DAG runs daily at 06:00 UTC

---

## Project Structure

```
nasa-bi-pipeline/
├── src/
│   ├── extract.py        # Step 1: Pull from NASA API
│   ├── transform.py      # Step 2: Clean & engineer features
│   ├── load.py           # Step 3: Upsert into PostgreSQL (ON CONFLICT DO UPDATE)
│   └── pipeline.py       # Full ETL runner (calls 1->2->3)
├── dags/
│   └── nasa_etl_dag.py   # Airflow DAG (daily 06:00 UTC, XCom, email alerts)
├── grafana/
│   └── nasa_asteroid_dashboard.json  # 12-panel Grafana dashboard
├── sql/
│   └── schema.sql        # DB schema (tables, indexes, views)
├── demo_pipeline.py      # Live demo script with coloured terminal output
├── setup_demo.sh         # One-time environment setup script
├── requirements.txt      # Python dependencies
├── Dockerfile            # Containerised ETL pipeline
├── docker-compose.yml    # PostgreSQL + Airflow stack
└── .env.example          # Credential template (never commit .env)
```

---

## Quick Start

```bash
git clone https://github.com/bhaveshpatil88-debug/madsc301-nasa-asteroid-bi-pipeline.git
cd madsc301-nasa-asteroid-bi-pipeline
chmod +x setup_demo.sh && ./setup_demo.sh
source .venv/bin/activate
python3 demo_pipeline.py
```

---

## Database Schema (Star Schema)

**asteroids** (Dimension Table): asteroid_id PK, name, est_diameter_avg_km, size_category, is_potentially_hazardous, is_sentry_object

**close_approaches** (Fact Table): id PK, asteroid_id FK, close_approach_date, velocity_kph, miss_distance_km, miss_distance_lunar, risk_score

**Risk Score Formula:** (1 - distance/max_distance) x 60 + (velocity/max_velocity) x 40 — scale 0-100

---

## Key Business Insights

- NASA tracks 7-15 asteroids approaching Earth every day
- ~15-20% are classified as Potentially Hazardous Asteroids (PHAs)
- Several asteroids pass within 5 lunar distances (< 2M km) monthly
- Risk score composite: 60% proximity weight + 40% velocity weight

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Source | NASA NeoWs REST API |
| Language | Python 3.11 |
| Data Processing | Pandas, NumPy |
| Database | PostgreSQL 15 |
| BI / Visualisation | Grafana (12 live panels) |
| Orchestration | Apache Airflow 2.8 |
| Containerisation | Docker, docker-compose |
| Notebook | Jupyter |
