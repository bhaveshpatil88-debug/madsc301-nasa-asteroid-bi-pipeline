"""
demo_pipeline.py — Live Demo Script
====================================
Designed for the MADSC301 BI Final presentation.
Run this 2-3 times during your live demo — it works every time
because the database uses ON CONFLICT DO UPDATE (upserts).

Usage:
    python3 demo_pipeline.py

What it shows:
    Step 1 — EXTRACT:   Calls NASA API, shows how many asteroids were found
    Step 2 — TRANSFORM: Cleans data, shows before/after comparison
    Step 3 — LOAD:      Inserts into PostgreSQL, shows record counts
    Step 4 — ANALYSE:   Prints business insights + saves charts
"""

import os, sys, time, textwrap
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Pretty printing helpers ───────────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
ORANGE = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def header(text):
    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}")

def step(n, text):
    print(f"\n{BOLD}{ORANGE}[STEP {n}]{RESET} {BOLD}{text}{RESET}")
    time.sleep(0.4)

def ok(text):
    print(f"  {GREEN}✓{RESET}  {text}")

def info(text):
    print(f"  {DIM}→  {text}{RESET}")

def separator():
    print(f"\n{DIM}{'─'*60}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
def run():
    # ── Banner ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{CYAN}")
    print("  ╔═════════════════════════════════════════════════╗")
    print("  ║   🚀  NASA ASTEROID RISK — BI PIPELINE  🚀      ║")
    print("  ║       MADSC301 | EU Business School Munich       ║")
    print("  ╚═════════════════════════════════════════════════╝")
    print(RESET)
    print(f"  {DIM}Run date: {date.today()}  |  Student: Bhavesh Patil{RESET}\n")
    time.sleep(0.5)

    # ── STEP 1: EXTRACT ───────────────────────────────────────────────────────
    header("STEP 1 — EXTRACT  (src/extract.py)")
    step(1, "Calling NASA NeoWs API...")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    from extract import fetch_neo_feed

    end_date   = date.today()
    start_date = end_date - timedelta(days=29)

    info(f"Endpoint : https://api.nasa.gov/neo/rest/v1/feed")
    info(f"Date range: {start_date}  →  {end_date}  (30 days)")
    info(f"API key  : {os.getenv('NASA_API_KEY', 'DEMO_KEY')[:8]}...")

    raw_neo = fetch_neo_feed(start_date, end_date)
    total_raw = sum(len(v) for v in raw_neo.values())

    separator()
    ok(f"Extracted {BOLD}{total_raw}{RESET} raw asteroid records across {len(raw_neo)} days")
    for day, neos in sorted(raw_neo.items()):
        hazardous = sum(1 for n in neos if n.get('is_potentially_hazardous_asteroid'))
        print(f"     {DIM}{day}  →  {len(neos):2d} asteroids  "
              f"({ORANGE}{hazardous} hazardous{DIM}){RESET}")

    # ── STEP 2: TRANSFORM ─────────────────────────────────────────────────────
    header("STEP 2 — TRANSFORM  (src/transform.py)")
    step(2, "Cleaning & engineering features with Pandas...")

    from transform import flatten_neo_data

    asteroids_df, approaches_df = flatten_neo_data(raw_neo)

    separator()
    ok(f"Asteroids (unique):   {BOLD}{len(asteroids_df)}{RESET} records")
    ok(f"Close approaches:     {BOLD}{len(approaches_df)}{RESET} Earth-approach events")
    ok(f"Potentially Hazardous:{BOLD}{asteroids_df.is_potentially_hazardous.sum()}{RESET} "
       f"({asteroids_df.is_potentially_hazardous.mean()*100:.1f}%)")

    print(f"\n  {DIM}Size categories:{RESET}")
    for cat, cnt in asteroids_df['size_category'].value_counts().items():
        bar = '█' * min(cnt, 30)
        print(f"   {DIM}{cat:<22}{RESET} {CYAN}{bar}{RESET} {cnt}")

    print(f"\n  {DIM}Risk score range: "
          f"{approaches_df.risk_score.min():.1f}  →  "
          f"{approaches_df.risk_score.max():.1f}  (top 3 highest risk):{RESET}")
    top3 = approaches_df.nlargest(3, 'risk_score')[
        ['asteroid_id', 'close_approach_date', 'miss_distance_lunar', 'velocity_kph', 'risk_score']
    ]
    for _, row in top3.iterrows():
        print(f"   {ORANGE}● {RESET}ID {row.asteroid_id}  |  "
              f"{str(row.close_approach_date)[:10]}  |  "
              f"{row.miss_distance_lunar:.1f} LD  |  "
              f"{row.velocity_kph:,.0f} km/h  |  "
              f"{RED}Risk: {row.risk_score:.1f}{RESET}")

    # Save CSV
    from transform import save_to_csv
    save_to_csv(asteroids_df, approaches_df)
    ok("Saved processed CSVs to data/processed/")

    # ── STEP 3: LOAD ──────────────────────────────────────────────────────────
    header("STEP 3 — LOAD  (src/load.py)")
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
        ok("Second run would update existing rows — no duplicates!")
    except Exception as e:
        print(f"\n  {RED}DB connection skipped: {e}{RESET}")
        print(f"  {DIM}(Make sure PostgreSQL is running: docker-compose up -d postgres){RESET}")

    # ── STEP 4: ANALYSE ───────────────────────────────────────────────────────
    header("STEP 4 — ANALYSE  (notebooks/analysis.ipynb)")
    step(4, "Generating visualisations with Matplotlib...")

    _generate_charts(asteroids_df, approaches_df)

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    header("PIPELINE COMPLETE")
    print(f"""
  {BOLD}Summary{RESET}
  ───────────────────────────────────────────────
  Date range    :  {start_date}  →  {end_date}
  Raw extracted :  {total_raw} asteroid records
  After cleaning:  {len(asteroids_df)} unique asteroids, {len(approaches_df)} approaches
  Hazardous     :  {asteroids_df.is_potentially_hazardous.sum()} ({asteroids_df.is_potentially_hazardous.mean()*100:.1f}%)
  Charts saved  :  data/processed/
  Orchestration :  Apache Airflow DAG (daily 06:00 UTC)
  ───────────────────────────────────────────────
  {DIM}Run this script again → same result (idempotent upserts){RESET}
    """)


def _generate_charts(asteroids_df, approaches_df):
    """Generate and save the 4 key visualisations."""
    try:
        import matplotlib
        matplotlib.use('Agg')   # Non-interactive backend (no display needed)
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import seaborn as sns
        import numpy as np

        plt.style.use('dark_background')
        CLR_TEAL   = '#00B4D8'
        CLR_ORANGE = '#FF6B35'
        CLR_GREEN  = '#00C896'
        os.makedirs('data/processed', exist_ok=True)

        # Chart 1 — Daily NEO count
        fig, ax = plt.subplots(figsize=(10, 4))
        daily = approaches_df.groupby('close_approach_date').size().reset_index(name='count')
        ax.fill_between(range(len(daily)), daily['count'], alpha=0.3, color=CLR_TEAL)
        ax.plot(range(len(daily)), daily['count'], color=CLR_TEAL, lw=2, marker='o', ms=6)
        ax.set_xticks(range(len(daily)))
        ax.set_xticklabels([str(d)[:10] for d in daily['close_approach_date']], rotation=30, ha='right', fontsize=9)
        ax.set_title('Daily Near-Earth Object Approaches', fontsize=14, fontweight='bold', color='white', pad=12)
        ax.set_ylabel('Number of Asteroids', color='#8BAFC7')
        ax.tick_params(colors='#8BAFC7')
        for spine in ax.spines.values(): spine.set_color('#1A4A8A')
        plt.tight_layout()
        plt.savefig('data/processed/chart1_daily_trend.png', dpi=150, bbox_inches='tight')
        plt.close()
        ok("Chart 1 saved: Daily NEO Trend")

        # Chart 2 — Hazard pie
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        haz = asteroids_df['is_potentially_hazardous'].value_counts()
        ax1.pie(haz, labels=['Non-Hazardous', 'Potentially Hazardous'],
                autopct='%1.1f%%', colors=[CLR_TEAL, CLR_ORANGE],
                startangle=90, wedgeprops={'edgecolor': '#0B1F3A', 'linewidth': 2})
        ax1.set_title('Hazard Classification', fontsize=13, fontweight='bold', color='white')

        # Size histogram by hazard
        for haz_val, color, label in [(False, CLR_TEAL, 'Non-Hazardous'), (True, CLR_ORANGE, 'Potentially Hazardous')]:
            subset = asteroids_df[asteroids_df['is_potentially_hazardous'] == haz_val]['est_diameter_avg_km']
            ax2.hist(subset, bins=20, alpha=0.65, color=color, label=label)
        ax2.set_title('Size by Hazard Status', fontsize=13, fontweight='bold', color='white')
        ax2.set_xlabel('Avg Diameter (km)', color='#8BAFC7')
        ax2.legend(fontsize=9)
        ax2.set_xlim(0, 1.5)
        ax2.tick_params(colors='#8BAFC7')
        for spine in ax2.spines.values(): spine.set_color('#1A4A8A')
        plt.tight_layout()
        plt.savefig('data/processed/chart2_hazard.png', dpi=150, bbox_inches='tight')
        plt.close()
        ok("Chart 2 saved: Hazard Classification")

        # Chart 3 — Risk scatter
        fig, ax = plt.subplots(figsize=(10, 5))
        combined = approaches_df.merge(asteroids_df, on='asteroid_id', how='left')
        sc = ax.scatter(
            combined['miss_distance_km'] / 1e6,
            combined['velocity_kph'] / 1000,
            c=combined['risk_score'], cmap='RdYlGn_r',
            s=combined['est_diameter_avg_km'].clip(upper=0.8) * 250 + 20,
            alpha=0.75, edgecolors='white', linewidth=0.4,
        )
        plt.colorbar(sc, ax=ax, label='Risk Score (0–100)')
        haz_pts = combined[combined['is_potentially_hazardous'] == True]
        ax.scatter(haz_pts['miss_distance_km']/1e6, haz_pts['velocity_kph']/1000,
                   s=120, color='red', marker='*', zorder=5, label='Potentially Hazardous')
        ax.set_xlabel('Miss Distance (Million km)', color='#8BAFC7')
        ax.set_ylabel('Velocity (Thousand km/h)', color='#8BAFC7')
        ax.set_title('Asteroid Risk Map — Miss Distance vs Velocity', fontsize=13, fontweight='bold', color='white')
        ax.legend(fontsize=10)
        ax.tick_params(colors='#8BAFC7')
        for spine in ax.spines.values(): spine.set_color('#1A4A8A')
        plt.tight_layout()
        plt.savefig('data/processed/chart3_risk_scatter.png', dpi=150, bbox_inches='tight')
        plt.close()
        ok("Chart 3 saved: Risk Map Scatter")

        # Chart 4 — Size distribution
        size_order = ['Micro (<50m)', 'Small (50–140m)', 'Medium (140–500m)', 'Large (500m–1km)', 'Giant (>1km)']
        size_counts = asteroids_df['size_category'].value_counts().reindex(size_order, fill_value=0)
        fig, ax = plt.subplots(figsize=(9, 4))
        colors = [CLR_TEAL, '#1565C0', CLR_ORANGE, CLR_GREEN, '#A855F7']
        bars = ax.barh(size_counts.index, size_counts.values, color=colors, edgecolor='none')
        ax.bar_label(bars, padding=5, fontsize=11, color='white')
        ax.set_title('Asteroid Size Distribution', fontsize=13, fontweight='bold', color='white')
        ax.set_xlabel('Count', color='#8BAFC7')
        ax.invert_yaxis()
        ax.tick_params(colors='#8BAFC7')
        for spine in ax.spines.values(): spine.set_color('#1A4A8A')
        plt.tight_layout()
        plt.savefig('data/processed/chart4_size_dist.png', dpi=150, bbox_inches='tight')
        plt.close()
        ok("Chart 4 saved: Size Distribution")

        print(f"\n  \033[92mAll charts saved to data/processed/ — open them to show your audience!\033[0m")

    except ImportError as e:
        print(f"  {DIM}(Charts skipped — run: pip3 install matplotlib seaborn){RESET}")


if __name__ == '__main__':
    run()
