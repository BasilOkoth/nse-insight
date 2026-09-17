from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "data" / "fundamentals_raw.csv"
OUTPUT_PATH = ROOT / "data" / "fundamentals.csv"
SNAPSHOT_PATH = ROOT / "data" / "market_snapshot.csv"

KEY_METRICS = [
    "pe_ratio","price_to_book","roe_pct","net_margin_pct","interest_cover",
    "dividend_yield_pct","dividend_years","payout_ratio_pct",
    "earnings_growth_pct","revenue_growth_pct",
]
OUTPUT_COLUMNS = [
    "ticker","pe_ratio","price_to_book","roe_pct","net_margin_pct","interest_cover",
    "dividend_yield_pct","dividend_years","payout_ratio_pct","earnings_growth_pct",
    "revenue_growth_pct","data_completeness_pct","governance_flag","financial_period",
    "source_name","source_type","source_url","verified_on",
]

def _num(s):
    return pd.to_numeric(s, errors="coerce")

def _safe_div(a,b):
    a=_num(a); b=_num(b)
    return a.div(b.where(b != 0))

def _valid_https(v):
    try:
        p=urlparse(str(v or "").strip())
        return p.scheme=="https" and bool(p.netloc)
    except ValueError:
        return False

def build_fundamentals():
    raw=pd.read_csv(RAW_PATH)
    if raw.empty:
        pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(OUTPUT_PATH,index=False)
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    if not raw["source_url"].map(_valid_https).all():
        bad=raw.loc[~raw["source_url"].map(_valid_https),"ticker"].tolist()
        raise ValueError("Every row requires a valid HTTPS source_url: "+", ".join(bad))

    prices=pd.read_csv(SNAPSHOT_PATH,usecols=["ticker","price"])
    prices["ticker"]=prices["ticker"].astype(str).str.strip()
    work=raw.copy()
    work["ticker"]=work["ticker"].astype(str).str.strip()
    work=work.merge(prices.drop_duplicates("ticker"),on="ticker",how="left")

    numeric_cols=[
        "eps","book_value_per_share","profit_after_tax","prior_profit_after_tax",
        "revenue","prior_revenue","total_equity","prior_total_equity","ebit","finance_cost",
        "roe_pct","net_margin_pct","interest_cover","dividend_per_share","dividend_years",
        "payout_ratio_pct","earnings_growth_pct","revenue_growth_pct","governance_flag",
    ]
    for col in numeric_cols:
        if col not in work:
            work[col]=pd.NA
        work[col]=_num(work[col])

    avg_equity=(work["total_equity"]+work["prior_total_equity"])/2
    work["roe_pct"]=work["roe_pct"].fillna(_safe_div(work["profit_after_tax"],avg_equity)*100)
    work["net_margin_pct"]=work["net_margin_pct"].fillna(_safe_div(work["profit_after_tax"],work["revenue"])*100)
    work["interest_cover"]=work["interest_cover"].fillna(_safe_div(work["ebit"],work["finance_cost"]))
    work["earnings_growth_pct"]=work["earnings_growth_pct"].fillna(
        _safe_div(work["profit_after_tax"]-work["prior_profit_after_tax"],work["prior_profit_after_tax"].abs())*100
    )
    work["revenue_growth_pct"]=work["revenue_growth_pct"].fillna(
        _safe_div(work["revenue"]-work["prior_revenue"],work["prior_revenue"].abs())*100
    )

    work["pe_ratio"]=_safe_div(work["price"],work["eps"])
    work.loc[work["eps"]<=0,"pe_ratio"]=pd.NA
    work["price_to_book"]=_safe_div(work["price"],work["book_value_per_share"])
    work.loc[work["book_value_per_share"]<=0,"price_to_book"]=pd.NA
    work["dividend_yield_pct"]=_safe_div(work["dividend_per_share"],work["price"])*100
    work["payout_ratio_pct"]=work["payout_ratio_pct"].fillna(
        _safe_div(work["dividend_per_share"],work["eps"])*100
    )

    work["governance_flag"]=work["governance_flag"].fillna(0).astype(int)
    work["data_completeness_pct"]=(work[KEY_METRICS].notna().mean(axis=1)*100).round(0)

    out=work[OUTPUT_COLUMNS].sort_values(["ticker","financial_period"]).drop_duplicates("ticker",keep="last")
    out.to_csv(OUTPUT_PATH,index=False)
    print(f"Built {len(out)} verified fundamentals records; average completeness {out['data_completeness_pct'].mean():.0f}%")
    return out

if __name__=="__main__":
    build_fundamentals()
