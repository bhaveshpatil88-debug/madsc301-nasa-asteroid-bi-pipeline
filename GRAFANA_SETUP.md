# Grafana Dashboard Setup
## NASA Asteroid Risk Intelligence | MADSC301 | Bhavesh Patil

The dashboard is pre-built and ready to import. This guide covers setting up a local Grafana instance and connecting it to the PostgreSQL database that the pipeline populates.

**Time to set up:** ~10 minutes (once)  
**What you'll end up with:** A 12-panel live dashboard that auto-refreshes from your local database

---

## Prerequisites

You need:
- Grafana installed locally (`brew install grafana` on Mac)
- PostgreSQL running with the `nasa_bi` database populated (run `python3 src/pipeline.py` first)

---

## Step 1 — Start Grafana

```bash
brew services start grafana
```

Open `http://localhost:3000` in Chrome.

Login: `admin` / `admin`

Grafana will prompt you to change the password — you can skip this for local development.

---

## Step 2 — Add PostgreSQL as a Data Source

1. Click the **☰ menu** (top left) → **Connections** → **Data sources**
2. Click **Add new data source**
3. Search for **PostgreSQL** and select it
4. Fill in the connection details:

| Field | Value |
|---|---|
| Host | `localhost:2026` |
| Database | `nasa_bi` |
| User | `macbook` |
| Password | *(leave blank)* |
| TLS/SSL Mode | `disable` |

5. Click **Save & test**

You should see: **"Database Connection OK"**

If it fails, check that Postgres.app is running (look for the elephant icon in your Mac menu bar).

---

## Step 3 — Import the Dashboard

1. Click **☰ menu** → **Dashboards** → **New** → **Import**
2. Click **Upload dashboard JSON file**
3. Navigate to `grafana/nasa_asteroid_dashboard.json` in this project folder and select it
4. On the next screen, choose your PostgreSQL data source from the dropdown
5. Click **Import**

The dashboard loads with all 12 panels populated from your live database.

---

## Dashboard Panels

| Panel | Type | What It Shows |
|---|---|---|
| Total Asteroids Tracked | Stat | Count of unique asteroids in the current window |
| Potentially Hazardous | Stat | PHAs — >140m and within 0.05 AU |
| Max Risk Score | Stat | Highest composite risk score (0–100) |
| Closest Approach | Stat | Minimum lunar distance recorded |
| Sentry Watch Objects | Stat | Asteroids on NASA's impact-risk watchlist |
| Daily NEO Count | Time series | Asteroid activity trend by day |
| Hazard Classification | Donut chart | Hazardous vs. non-hazardous breakdown |
| Size Distribution | Bar chart | How many fall into each size category |
| Avg Risk by Size Category | Bar chart | Which size class carries the highest risk |
| NEO Count by Size & Hazard | Grouped bar | Size × hazard status cross-breakdown |
| Top 20 Risk Approaches | Table | Ranked by risk score, with hazard badge |

---

## Keeping the Dashboard Updated

The pipeline is idempotent — run it as many times as you want:

```bash
source .venv/bin/activate
python3 src/pipeline.py
```

Each run fetches the latest NASA data, updates existing records in PostgreSQL, and the dashboard reflects the changes on next refresh.

To set up automated daily runs, enable the Airflow DAG (see `dags/nasa_etl_dag.py`).

---

## Troubleshooting

**Dashboard shows "No data"**  
Run `python3 src/pipeline.py` to load data into the database, then refresh the dashboard. Also check the time range — set it to "Last 30 days".

**"Database Connection OK" but panels are empty**  
Check that the database and user match exactly what's in your `.env` file.

**Connection refused on port 2026**  
Postgres.app is not running. Open the app from Applications and click Start.

**Grafana won't open at localhost:3000**  
Run `brew services restart grafana` and wait 10 seconds before refreshing.
