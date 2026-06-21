"""
extract.py - NASA NeoWs API Extraction
"""
import os, time, logging, requests
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
BASE_URL = "https://api.nasa.gov/neo/rest/v1/feed"
MAX_DAYS_PER_REQUEST = 7

def fetch_neo_feed(start_date: date, end_date: date) -> dict:
    """Fetch NEOs between start_date and end_date. Splits into 7-day chunks."""
    all_objects = {}
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=MAX_DAYS_PER_REQUEST - 1), end_date)
        params = {"start_date": current.isoformat(), "end_date": chunk_end.isoformat(), "api_key": NASA_API_KEY}
        logger.info(f"Fetching NEOs from {current} to {chunk_end}...")
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        all_objects.update(data.get("near_earth_objects", {}))
        logger.info(f"  -> Retrieved {data.get('element_count', 0)} objects.")
        current = chunk_end + timedelta(days=1)
        time.sleep(1)  # Respect rate limits (DEMO_KEY: 30 req/hour)
    return all_objects

if __name__ == "__main__":
    today = date.today()
    raw = fetch_neo_feed(today - timedelta(days=6), today)
    print(f"Extracted {sum(len(v) for v in raw.values())} NEO records.")
