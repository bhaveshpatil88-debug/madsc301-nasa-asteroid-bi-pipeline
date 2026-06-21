#!/bin/bash
# NASA BI Pipeline - Setup
# Run: chmod +x setup_demo.sh && ./setup_demo.sh
set -e
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install --upgrade pip -q
pip install requests pandas numpy python-dotenv psycopg2-binary matplotlib seaborn scikit-learn jupyter notebook -q
[ ! -f ".env" ] && cp .env.example .env
mkdir -p data/processed
python3 -c "import requests, pandas, numpy, matplotlib, dotenv; print('All imports OK')"
echo "Setup complete! Run: source .venv/bin/activate && python3 demo_pipeline.py"
