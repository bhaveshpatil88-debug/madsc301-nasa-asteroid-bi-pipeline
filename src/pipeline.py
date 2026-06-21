"""
pipeline.py — Full ETL Pipeline Runner
Ties Extract -> Transform -> Load together.
"""
import logging, sys
from datetime import date, timedelta
from extract import fetch_neo_feed
from transform import flatten_neo_data, save_to_csv
from load import run_load

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("pipeline.log")])
logger = logging.getLogger(__name__)

def run_pipeline(start_date=None, end_date=None):
    if end_date is None: end_date = date.today()
    if start_date is None: start_date = end_date - timedelta(days=6)
    logger.info(f"=== NASA BI Pipeline START: {start_date} -> {end_date} ===")
    raw_neo = fetch_neo_feed(start_date, end_date)
    total_raw = sum(len(v) for v in raw_neo.values())
    logger.info(f"  Extracted {total_raw} raw records.")
    asteroids_df, approaches_df = flatten_neo_data(raw_neo)
    save_to_csv(asteroids_df, approaches_df)
    result = run_load(asteroids_df, approaches_df)
    logger.info(f"  Loaded -> Asteroids: {result['asteroids']} | Approaches: {result['close_approaches']}")
    logger.info("=== NASA BI Pipeline COMPLETE ===")
    return {"start_date": str(start_date), "end_date": str(end_date),
            "raw_extracted": total_raw, "asteroids": len(asteroids_df),
            "close_approaches": len(approaches_df), "db_result": result}

if __name__ == "__main__":
    summary = run_pipeline()
    print("\nPipeline Summary:")
    for k, v in summary.items(): print(f"  {k}: {v}")
