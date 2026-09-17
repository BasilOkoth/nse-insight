from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "data" / "fundamentals_raw.csv"
OUTPUT_PATH = ROOT / "data" / "fundamentals.csv"
SNAPSHOT_PATH = ROOT / "data" / "market_snapshot.csv"

KEY_METRICS = [
    "pe_ratio",
    "price_to_book",
    "roe_pct",
    "net_margin_pct",
    "interest_cover",
    "dividend_yield_pct",
    "dividend_years",
    "payout_ratio_pct",
    "earnings_growth_pct",
    "revenue_growth_pct",
]

OUTPUT_COLUMNS = [
    "ticker",
    "pe_ratio",
    "price_to_book",
    "roe_pct",
    "net_margin_pct",
    "interest_cover",
    "dividend_yield_pct",
    "dividend_years",
    "payout_ratio_pct",
    "earnings_growth_pct",
    "revenue_growth_pct",
    "data_completeness_pct",
    "governance_flag",
    "financial_period",
    "source_name",
    "source_type",
    "source_url",
    "verified_on",
]


def _num(series):
    return pd.to_numeric(series, errors="coerce")


def _safe_div(numerator, denominator):
    n = _num(numerator)
    d = _num(denominator)
    return n.div(d.where(d != 0))


def _https_url(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        parsed = urlparse(text)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def _load_prices() -> pd.DataFrame:
    if not SNAPSHOT_PATH.exists():
        raise FileNotFoundError(
            "data/market_snapshot.csv is missing. Refresh NSE prices before building fundamentals."
        )
    prices = pd.read_csv(SNAPSHOT_PATH, usecols=["ticker", "price"])
    prices["ticker"] = prices["ticker"].astype(str).str.strip()
    prices["price"] = _num(prices["price"])
    return prices.drop_duplicates("ticker", keep="last")


def _load_raw() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(
            "data/fundamentals_raw.csv is missing. Add verified report data first."
        )
    raw = pd.read_csv(RAW_PATH)
    if raw.empty:
        return raw

    required = {"ticker", "financial_period", "source_url"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(
            "fundamentals_raw.csv is missing required columns: "
            + ", ".join(sorted(missing))
        )

    raw["ticker"] = raw["ticker"].astype(str).str.strip()
    raw["financial_period"] = raw["financial_period"].astype(str).str.strip()
    raw["source_url"] = raw["source_url"].fillna("").astype(str).str.strip()

    bad_sources = raw.loc[~raw["source_url"].map(_https_url), "ticker"].tolist()
    if bad_sources:
        raise ValueError(
            "Every fundamentals row must have an HTTPS source_url. Invalid rows: "
            + ", ".join(bad_sources[:12])
        )

    if "verified_on" not in raw:
        raw["verified_on"] = date.today().isoformat()
    raw["verified_on"] = raw["verified_on"].fillna(date.today().isoformat())

    return raw


def build_fundamentals() -> pd.DataFrame:
    raw = _load_raw()

    if raw.empty:
        empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
        empty.to_csv(OUTPUT_PATH, index=False)
        print("No verified fundamentals rows found; wrote an empty fundamentals.csv.")
        return empty

    prices = _load_prices()
    work = raw.merge(prices, on="ticker", how="left", validate="many_to_one")

    # Accept either directly reported ratios OR raw report values.
    # Direct values always take precedence.
    for col in [
        "eps",
        "book_value_per_share",
        "roe_pct",
        "net_margin_pct",
        "interest_cover",
        "dividend_per_share",
        "dividend_years",
        "earnings_growth_pct",
        "revenue_growth_pct",
        "payout_ratio_pct",
        "governance_flag",
        "profit_after_tax",
        "prior_profit_after_tax",
        "revenue",
        "prior_revenue",
        "total_equity",
        "prior_total_equity",
        "ebit",
        "finance_cost",
    ]:
        if col not in work:
            work[col] = pd.NA

    # Derived report ratios. These use values from the same report/unit scale,
    # so KES vs KES '000 does not matter for percentage ratios.
    avg_equity = (_num(work["total_equity"]) + _num(work["prior_total_equity"])) / 2
    derived_roe = _safe_div(work["profit_after_tax"], avg_equity) * 100
    derived_margin = _safe_div(work["profit_after_tax"], work["revenue"]) * 100
    derived_cover = _safe_div(work["ebit"], work["finance_cost"])
    derived_earnings_growth = (
        _safe_div(
            _num(work["profit_after_tax"]) - _num(work["prior_profit_after_tax"]),
            _num(work["prior_profit_after_tax"]).abs(),
        )
        * 100
    )
    derived_revenue_growth = (
        _safe_div(
            _num(work["revenue"]) - _num(work["prior_revenue"]),
            _num(work["prior_revenue"]).abs(),
        )
        * 100
    )

    work["roe_pct"] = _num(work["roe_pct"]).fillna(derived_roe)
    work["net_margin_pct"] = _num(work["net_margin_pct"]).fillna(derived_margin)
    work["interest_cover"] = _num(work["interest_cover"]).fillna(derived_cover)
    work["earnings_growth_pct"] = _num(work["earnings_growth_pct"]).fillna(
        derived_earnings_growth
    )
    work["revenue_growth_pct"] = _num(work["revenue_growth_pct"]).fillna(
        derived_revenue_growth
    )

    # Market-dependent ratios are recalculated every time from the latest
    # saved NSE market snapshot, so they stay current without rewriting report data.
    work["pe_ratio"] = _safe_div(work["price"], work["eps"])
    work.loc[_num(work["eps"]) <= 0, "pe_ratio"] = pd.NA

    work["price_to_book"] = _safe_div(work["price"], work["book_value_per_share"])
    work.loc[_num(work["book_value_per_share"]) <= 0, "price_to_book"] = pd.NA

    work["dividend_yield_pct"] = (
        _safe_div(work["dividend_per_share"], work["price"]) * 100
    )

    derived_payout = _safe_div(work["dividend_per_share"], work["eps"]) * 100
    work["payout_ratio_pct"] = _num(work["payout_ratio_pct"]).fillna(derived_payout)

    work["dividend_years"] = _num(work["dividend_years"])
    work["governance_flag"] = _num(work["governance_flag"]).fillna(0).astype(int)

    # Completeness is evidence-driven, not manually guessed.
    work["data_completeness_pct"] = (
        work[KEY_METRICS].notna().mean(axis=1) * 100
    ).round(0)

    for col in ["source_name", "source_type"]:
        if col not in work:
            work[col] = ""
        work[col] = work[col].fillna("").astype(str)

    out = work[OUTPUT_COLUMNS].copy()
    out = out.sort_values(["ticker", "financial_period"]).drop_duplicates(
        "ticker", keep="last"
    )

    out.to_csv(OUTPUT_PATH, index=False)

    print(
        f"Built {len(out)} verified fundamentals rows. "
        f"Average evidence completeness: {out['data_completeness_pct'].mean():.0f}%"
    )
    return out


if __name__ == "__main__":
    build_fundamentals()
