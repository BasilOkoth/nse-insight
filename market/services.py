from functools import lru_cache
import json
from pathlib import Path
import pandas as pd
from analysis_engine import analyze
from nse_data import add_market_metrics, fetch_nse_snapshot, load_history, merge_fundamentals

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "market_snapshot.csv"
HISTORY = ROOT / "data" / "market_history.csv"
FUNDAMENTALS = ROOT / "data" / "fundamentals.csv"

@lru_cache(maxsize=2)
def get_market(version: int = 0):
    snapshot = pd.read_csv(SNAPSHOT) if SNAPSHOT.exists() else fetch_nse_snapshot()[0]
    market = add_market_metrics(snapshot, load_history(HISTORY))
    results = analyze(merge_fundamentals(market, FUNDAMENTALS))
    as_of = str(snapshot["as_of"].iloc[0]) if "as_of" in snapshot and not snapshot.empty else "Latest session"
    return results, as_of

def refresh_from_nse():
    snapshot, as_of = fetch_nse_snapshot()
    snapshot.to_csv(SNAPSHOT, index=False)
    get_market.cache_clear()
    return snapshot, as_of

def records(df):
    return json.loads(df.to_json(orient="records"))
