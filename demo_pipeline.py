"""
demo_pipeline.py -- Live Demo Script for MADSC301 Presentation
Run 2-3 times during demo to show idempotent upserts.
Usage: python3 demo_pipeline.py
"""
import os, sys, time
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv()

CYAN="[96m"; GREEN="[92m"; ORANGE="[93m"; RED="[91m"
BOLD="[1m"; RESET="[0m"; DIM="[2m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")

def step(n, text): print(f"\n{BOLD}{ORANGE}[STEP {n}]{RESET} {BOLD}{text}{RESET}"); time.sleep(0.4)
def ok(text): print(f"  {GREEN}ok{RESET}  {text}")
def info(text): print(f"  {DIM}->  {text}{RESET}")
def separator(): print(f"\n{DIM}{'-'*60}{RESET}")

def run():
    print(f"\n{BOLD}{CYAN}")
    print("  +==================================================+")
    print("  |   NASA ASTEROID RISK -- BI PIPELINE             |")
    print("  |       MADSC301 | EU Business School Munich       |")
    print("  +==================================================+")
    print(RESET)
    print(f"  {DIM}Run date: {date.today()}  |  Student: Bhavesh Patil{RESET}\n")
    time.sleep(0.5)

    header("STEP 1 -- EXTRACT  (src/extract.py)")
    step(1, "Calling NASA NeoWs API...")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from extract import fetch_neo_feed
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    info(f"Endpoint : https://api.nasa.gov/neo/rest/v1/feed")
    info(f"Date range: {start_date}  ->  {end_date}  (7 days)")
    info(f"API key  : {os.getenv('NASA_API_KEY', 'DEMO_KEY')[:8]}...")
    raw_neo = fetch_neo_feed(start_date, end_date)
    total_raw = sum(len(v) for v in raw_neo.values())
    separator()
    ok(f"Extracted {BOLD}{total_raw}{RESET} raw asteroid records across {len(raw_neo)} days")
    for day, neos in sorted(raw_neo.items()):
        hazardous = sum(1 for n in neos if n.get('is_potentially_hazardous_asteroid'))
        print(f"     {DIM}{day}  ->  {len(neos):2d} asteroids  ({ORANGE}{hazardous} hazardous{DIM}){RESET}")

    header("STEP 2 -- TRANSFORM  (src/transform.py)")
    step(2, "Cleaning & engineering features with Pandas...")
    from transform import flatten_neo_data, save_to_csv
    asteroids_df, approaches_df = flatten_neo_data(raw_neo)
    separator()
    ok(f"Asteroids (unique):    {BOLD}{len(asteroids_df)}{RESET} records")
    ok(f"Close approaches:      {BOLD}{len(approaches_df)}{RESET} Earth-approach events")
    ok(f"Potentially Hazardous: {BOLD}{asteroids_df.is_potentially_hazardous.sum()}{RESET} ({asteroids_df.is_potentially_hazardous.mean()*100:.1f}%)")
    print(f"\n  {DIM}Size categories:{RESET}")
    for cat, cnt in asteroids_df['size_category'].value_counts().items():
        bar = chr(9608) * min(cnt, 30)
        print(f"   {DIM}{cat:<22}{RESET} {CYAN}{bar}{RESET} {cnt}")
    print(f"\n  {DIM}Risk score range: {approaches_df.risk_score.min():.1f}  ->  {approaches_df.risk_score.max():.1f}{RESET}")
    save_to_csv(asteroids_df, approaches_df)
    ok("Saved processed CSVs to data/processed/")

    header("STEP 3 -- LOAD  (src/load.py)")
    step(3, "Upserting into PostgreSQL...")
    info("Host    : " + os.getenv('POSTGRES_HOST', 'localhost'))
    info("Database: " + os.getenv('POSTGRES_DB',  'nasa_bi'))
    info("Schema  : asteroids (dimension) + close_approaches (fact)")
    try:
        from load import run_load
        result = run_load(asteroids_df, approaches_df)
        separator()
        ok(f"Upserted {BOLD}{result['asteroids']}{RESET} asteroid records   (ON CONFLICT DO UPDATE)")
        ok(f"Upserted {BOLD}{result['close_approaches']}{RESET} close-approach records")
        ok("Second run updates existing rows -- no duplicates (idempotent)!")
    except Exception as e:
        print(f"\n  {RED}DB: {e}{RESET}")

    header("STEP 4 -- ANALYSE  (Charts)")
    step(4, "Generating visualisations with Matplotlib...")
    _generate_charts(asteroids_df, approaches_df)

    header("PIPELINE COMPLETE")
    print(f"""
  {BOLD}Summary{RESET}
  --------------------------------------------------
  Date range    : {start_date}  ->  {end_date}
  Raw extracted : {total_raw} asteroid records
  After cleaning: {len(asteroids_df)} unique asteroids, {len(approaches_df)} approaches
  Hazardous     : {asteroids_df.is_potentially_hazardous.sum()} ({asteroids_df.is_potentially_hazardous.mean()*100:.1f}%)
  Charts        : data/processed/
  Orchestration : Apache Airflow DAG (daily 06:00 UTC)
  --------------------------------------------------
  {DIM}Run again -> same result (idempotent upserts){RESET}
    """)

def _generate_charts(asteroids_df, approaches_df):
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        CLR_TEAL='#00B4D8'; CLR_ORANGE='#FF6B35'; CLR_GREEN='#00C896'
        plt.style.use('dark_background')
        os.makedirs('data/processed', exist_ok=True)

        fig, ax = plt.subplots(figsize=(10, 4))
        daily = approaches_df.groupby('close_approach_date').size().reset_index(name='count')
        ax.fill_between(range(len(daily)), daily['count'], alpha=0.3, color=CLR_TEAL)
        ax.plot(range(len(daily)), daily['count'], color=CLR_TEAL, lw=2, marker='o', ms=6)
        ax.set_xticks(range(len(daily)))
        ax.set_xticklabels([str(d)[:10] for d in daily['close_approach_date']], rotation=30, ha='right', fontsize=9)
        ax.set_title('Daily Near-Earth Object Approaches', fontsize=14, fontweight='bold', color='white')
        ax.set_ylabel('Number of Asteroids', color='#8BAFC7')
        plt.tight_layout(); plt.savefig('data/processed/chart1_daily_trend.png', dpi=150); plt.close()
        ok("Chart 1 saved: Daily NEO Trend")

        fig, ax = plt.subplots(figsize=(10, 5))
        combined = approaches_df.merge(asteroids_df, on='asteroid_id', how='left')
        sc = ax.scatter(combined['miss_distance_km']/1e6, combined['velocity_kph']/1000,
            c=combined['risk_score'], cmap='RdYlGn_r',
            s=combined['est_diameter_avg_km'].clip(upper=0.8)*250+20, alpha=0.75)
        plt.colorbar(sc, ax=ax, label='Risk Score (0-100)')
        ax.set_xlabel('Miss Distance (Million km)', color='#8BAFC7')
        ax.set_ylabel('Velocity (Thousand km/h)', color='#8BAFC7')
        ax.set_title('Asteroid Risk Map -- Miss Distance vs Velocity', fontsize=13, fontweight='bold')
        plt.tight_layout(); plt.savefig('data/processed/chart2_risk_scatter.png', dpi=150); plt.close()
        ok("Chart 2 saved: Risk Map Scatter")

        size_order = ['Micro (<50m)','Small (50-140m)','Medium (140-500m)','Large (500m-1km)','Giant (>1km)']
        size_counts = asteroids_df['size_category'].value_counts().reindex(size_order, fill_value=0)
        fig, ax = plt.subplots(figsize=(9, 4))
        bars = ax.barh(size_counts.index, size_counts.values,
            color=[CLR_TEAL,'#1565C0',CLR_ORANGE,CLR_GREEN,'#A855F7'], edgecolor='none')
        ax.bar_label(bars, padding=5, fontsize=11, color='white')
        ax.set_title('Asteroid Size Distribution', fontsize=13, fontweight='bold')
        ax.invert_yaxis(); plt.tight_layout()
        plt.savefig('data/processed/chart3_size_dist.png', dpi=150); plt.close()
        ok("Chart 3 saved: Size Distribution")

        print(f"\n  [92mAll charts saved to data/processed/[0m")
    except ImportError:
        print(f"  Charts skipped -- run: pip install matplotlib seaborn")

if __name__ == '__main__':
    run()
