from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup


NSE_STATS_URL = "https://www.nse.co.ke/market-statistics/"
NSE_AJAX_URL = "https://www.nse.co.ke/wp-admin/admin-ajax.php"
SECTORS = {
    "agric": "Agricultural", "auto": "Automobiles", "bank": "Banking",
    "comm": "Commercial", "const": "Construction", "energy": "Energy",
    "insr": "Insurance", "invest": "Investment", "investse": "Investment Services",
    "manu": "Manufacturing", "tele": "Telecommunication", "real": "Real Estate",
    "exchange": "ETF",
}
HEADERS = {"User-Agent": "NSE-Insight/1.0 (private research dashboard)"}


def _number(value):
    return pd.to_numeric(str(value).replace(",", "").replace("-", "0"), errors="coerce")


def fetch_nse_snapshot(timeout: int = 25) -> Tuple[pd.DataFrame, str]:
    """Fetch the publicly displayed NSE market-statistics tables.

    This is intentionally low-frequency, cached by the app, and intended for a
    private decision-support dashboard. It does not reproduce an order book.
    """
    session = requests.Session()
    page = session.get(NSE_STATS_URL, headers=HEADERS, timeout=timeout)
    page.raise_for_status()
    nonce_match = re.search(r'ajaxnonce":"([^"]+)', page.text)
    if not nonce_match:
        raise RuntimeError("NSE page did not expose the expected request token")
    nonce = nonce_match.group(1)
    date_match = re.search(r"Statistics as of\s*([^<]+)", page.text, re.I)
    as_of = date_match.group(1).strip() if date_match else datetime.now().date().isoformat()

    def fetch_sector(code, sector):
        response = requests.post(
            NSE_AJAX_URL,
            data={"action": "display_prices", "security": nonce, "sector": code},
            headers={**HEADERS, "Referer": NSE_STATS_URL}, timeout=timeout,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        if table is None:
            return None
        parsed = pd.read_html(StringIO(str(table)))[0]
        parsed.columns = [str(c).strip().lower().replace(" ", "_").replace("(%)", "pct") for c in parsed.columns]
        parsed = parsed.rename(columns={
            "last_traded_price": "price", "change_pct": "daily_change_pct",
            "isin_code": "isin", "volume": "volume", "company": "company",
        })
        parsed["sector"] = sector
        return parsed

    frames = []
    with ThreadPoolExecutor(max_workers=len(SECTORS)) as pool:
        futures = {pool.submit(fetch_sector, code, sector): code for code, sector in SECTORS.items()}
        for future in as_completed(futures):
            try:
                frame = future.result()
                if frame is not None:
                    frames.append(frame)
            except requests.RequestException:
                continue

    if not frames:
        raise RuntimeError("No equity tables were returned by NSE")
    data = pd.concat(frames, ignore_index=True)
    for col in ["price", "daily_change_pct", "volume"]:
        data[col] = data[col].map(_number)
    data = data.dropna(subset=["company", "price"]).drop_duplicates("isin")
    data["ticker"] = data["isin"]
    data["as_of"] = as_of
    return data[["ticker", "isin", "company", "sector", "price", "volume", "daily_change_pct", "as_of"]], as_of


def load_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date", "ticker", "price", "volume"])
    return pd.read_csv(path)


def add_market_metrics(snapshot: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    work = snapshot.copy()
    if history.empty:
        work["return_3m_pct"] = pd.NA
        work["return_12m_pct"] = pd.NA
        work["volatility_pct"] = pd.NA
        work["max_drawdown_pct"] = pd.NA
        work["avg_daily_value_kes"] = work["price"] * work["volume"]
        work["zero_volume_days_pct"] = pd.NA
        return work

    h = history.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h["price"] = pd.to_numeric(h["price"], errors="coerce")
    h["volume"] = pd.to_numeric(h["volume"], errors="coerce").fillna(0)
    h = h.dropna(subset=["date", "price"]).sort_values("date")

    records = []
    for ticker, group in h.groupby("ticker"):
        group = group[group["price"] > 0].sort_values("date").tail(260)
        if group.empty:
            continue
        latest = group["price"].iloc[-1]
        daily_returns = group["price"].pct_change().dropna()
        rolling_peak = group["price"].cummax()
        drawdown = (group["price"] / rolling_peak - 1).min()
        records.append({
            "ticker": ticker,
            "return_3m_pct": (latest / group["price"].iloc[-min(63, len(group))] - 1) * 100,
            "return_12m_pct": (latest / group["price"].iloc[0] - 1) * 100,
            "volatility_pct": daily_returns.std() * (252 ** 0.5) * 100 if len(daily_returns) > 5 else pd.NA,
            "max_drawdown_pct": abs(drawdown) * 100,
            "avg_daily_value_kes": (group["price"] * group["volume"]).mean(),
            "zero_volume_days_pct": (group["volume"].eq(0).mean() * 100),
        })
    return work.merge(pd.DataFrame(records), on="ticker", how="left")


def merge_fundamentals(market: pd.DataFrame, fundamentals_path: Path) -> pd.DataFrame:
    if not fundamentals_path.exists():
        return market
    fundamentals = pd.read_csv(fundamentals_path)
    return market.merge(fundamentals, on="ticker", how="left", suffixes=("", "_fund"))
