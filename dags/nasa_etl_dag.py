"""
nasa_etl_dag.py - Apache Airflow DAG
Schedules the NASA NEO ETL pipeline daily at 06:00 UTC.
Tasks: extract -> transform -> load -> check_hazardous -> notify_on_failure
"""
from datetime import datetime, timedelta, date
import sys, os
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.trigger_rule import TriggerRule

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

default_args = {
    "owner": "bhavesh",
    "depends_on_past": False,
    "email": ["bhaveshpatil88@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

def task_extract(**context):
    from extract import fetch_neo_feed
    import json
    execution_date = context["ds"]
    run_date = date.fromisoformat(execution_date)
    start_d = run_date - timedelta(days=1)
    raw_neo = fetch_neo_feed(start_d, run_date)
    total = sum(len(v) for v in raw_neo.values())
    context["ti"].xcom_push(key="raw_neo", value=raw_neo)
    context["ti"].xcom_push(key="total_raw", value=total)
    print(f"Extracted {total} NEO records for {start_d} to {run_date}.")

def task_transform(**context):
    from transform import flatten_neo_data, save_to_csv
    raw_neo = context["ti"].xcom_pull(key="raw_neo", task_ids="extract")
    if not raw_neo: raise ValueError("No data received from extract task.")
    asteroids_df, approaches_df = flatten_neo_data(raw_neo)
    save_to_csv(asteroids_df, approaches_df)
    context["ti"].xcom_push(key="asteroids_json", value=asteroids_df.to_json())
    context["ti"].xcom_push(key="approaches_json", value=approaches_df.to_json())
    print(f"Transformed: {len(asteroids_df)} asteroids, {len(approaches_df)} approaches.")

def task_load(**context):
    from load import run_load
    import pandas as pd
    from io import StringIO
    asteroids_df = pd.read_json(StringIO(context["ti"].xcom_pull(key="asteroids_json", task_ids="transform")))
    approaches_df = pd.read_json(StringIO(context["ti"].xcom_pull(key="approaches_json", task_ids="transform")))
    approaches_df["close_approach_date"] = pd.to_datetime(approaches_df["close_approach_date"], unit="ms")
    result = run_load(asteroids_df, approaches_df)
    print(f"Loaded -> Asteroids: {result['asteroids']} | Approaches: {result['close_approaches']}")

def task_check_hazardous(**context):
    import psycopg2, os
    from datetime import date, timedelta
    conn = psycopg2.connect(host=os.getenv("POSTGRES_HOST","localhost"), dbname=os.getenv("POSTGRES_DB","nasa_bi"),
        user=os.getenv("POSTGRES_USER","nasa_user"), password=os.getenv("POSTGRES_PASSWORD",""))
    yesterday = date.today() - timedelta(days=1)
    with conn.cursor() as cur:
        cur.execute("""SELECT a.name, ca.miss_distance_lunar, ca.velocity_kph, ca.risk_score
            FROM close_approaches ca JOIN asteroids a USING (asteroid_id)
            WHERE a.is_potentially_hazardous = TRUE AND ca.close_approach_date = %s AND ca.miss_distance_lunar < 10
            ORDER BY ca.miss_distance_lunar ASC""", (yesterday,))
        alerts = cur.fetchall()
    conn.close()
    if alerts:
        for name, lunar, vel, risk in alerts:
            print(f"ALERT: {name} - {lunar:.2f} LD - {vel:,.0f} km/h - Risk: {risk:.1f}")

with DAG(
    dag_id="nasa_neo_etl_pipeline",
    default_args=default_args,
    description="Daily ETL pipeline for NASA Near-Earth Object data",
    schedule_interval="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["nasa", "bi", "etl", "space"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=task_extract, provide_context=True)
    transform = PythonOperator(task_id="transform", python_callable=task_transform, provide_context=True)
    load = PythonOperator(task_id="load", python_callable=task_load, provide_context=True)
    check_hazardous = PythonOperator(task_id="check_hazardous", python_callable=task_check_hazardous, provide_context=True)
    notify_failure = EmailOperator(
        task_id="notify_on_failure", to=["bhaveshpatil88@gmail.com"],
        subject="[NASA BI] Pipeline FAILED on {{ ds }}",
        html_content="<h3>NASA NEO ETL Pipeline Failed</h3><p>Run date: <b>{{ ds }}</b></p>",
        trigger_rule=TriggerRule.ONE_FAILED)
    extract >> transform >> load >> check_hazardous >> notify_failure
