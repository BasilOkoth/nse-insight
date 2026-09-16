from datetime import date
from pathlib import Path

import pandas as pd

from nse_data import fetch_nse_snapshot, load_history


ROOT = Path(__file__).parent
PATH = ROOT / "data" / "market_history.csv"
SNAPSHOT_PATH = ROOT / "data" / "market_snapshot.csv"

snapshot, as_of = fetch_nse_snapshot()
snapshot.to_csv(SNAPSHOT_PATH, index=False)
new = snapshot[["ticker", "price", "volume"]].copy()
new = new[new["price"] > 0]
new.insert(0, "date", date.today().isoformat())
history = load_history(PATH)
combined = pd.concat([history, new], ignore_index=True)
combined = combined.drop_duplicates(["date", "ticker"], keep="last").sort_values(["date", "ticker"])
combined.to_csv(PATH, index=False)
print(f"Saved {len(new)} securities for {as_of}; history has {len(combined)} rows")
