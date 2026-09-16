from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


SECTOR_RULES = {
    "Banking": {"pe_good": 6.5, "pb_good": 1.2, "roe_good": 18.0},
    "Insurance": {"pe_good": 8.0, "pb_good": 1.1, "roe_good": 15.0},
    "Other": {"pe_good": 11.0, "pb_good": 1.8, "roe_good": 16.0},
}

WEIGHTS = {
    "quality": 0.25,
    "value": 0.20,
    "dividend": 0.15,
    "momentum": 0.15,
    "growth": 0.10,
    "liquidity": 0.10,
    "risk": 0.05,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    if pd.isna(value):
        return 50.0
    return float(max(low, min(high, value)))


def _linear(value: float, bad: float, good: float) -> float:
    if pd.isna(value):
        return 50.0
    if good == bad:
        return 50.0
    return _clamp((value - bad) / (good - bad) * 100)


def _inverse(value: float, good: float, bad: float) -> float:
    return 100.0 - _linear(value, good, bad)


def score_row(row: pd.Series) -> Dict[str, float]:
    sector = row.get("sector", "Other")
    rules = SECTOR_RULES.get(sector, SECTOR_RULES["Other"])

    quality = np.mean([
        _linear(row.get("roe_pct"), 5, rules["roe_good"]),
        _linear(row.get("net_margin_pct"), 3, 20),
        _linear(row.get("interest_cover"), 1, 6),
    ])
    value = np.mean([
        _inverse(row.get("pe_ratio"), rules["pe_good"], rules["pe_good"] * 3),
        _inverse(row.get("price_to_book"), rules["pb_good"], rules["pb_good"] * 3),
    ])
    dividend = np.mean([
        _linear(row.get("dividend_yield_pct"), 1, 8),
        _linear(row.get("dividend_years"), 0, 5),
        _inverse(row.get("payout_ratio_pct"), 45, 110),
    ])
    momentum = np.mean([
        _linear(row.get("return_3m_pct"), -15, 20),
        _linear(row.get("return_12m_pct"), -25, 35),
    ])
    growth = np.mean([
        _linear(row.get("earnings_growth_pct"), -15, 25),
        _linear(row.get("revenue_growth_pct"), -10, 20),
    ])
    liquidity = np.mean([
        _linear(np.log10(max(float(row.get("avg_daily_value_kes", 0)), 1)), 4, 7.5),
        _inverse(row.get("zero_volume_days_pct"), 2, 45),
    ])
    risk = np.mean([
        _inverse(row.get("volatility_pct"), 12, 55),
        _inverse(row.get("max_drawdown_pct"), 12, 55),
    ])

    scores = {
        "quality": _clamp(quality), "value": _clamp(value),
        "dividend": _clamp(dividend), "momentum": _clamp(momentum),
        "growth": _clamp(growth), "liquidity": _clamp(liquidity),
        "risk": _clamp(risk),
    }
    total = sum(scores[key] * WEIGHTS[key] for key in WEIGHTS)

    warnings = 0
    if row.get("avg_daily_value_kes", 0) < 100_000: warnings += 1
    if row.get("earnings_growth_pct", 0) < -20: warnings += 1
    if row.get("governance_flag", 0): warnings += 2
    if row.get("data_completeness_pct", 100) < 65: warnings += 1
    total -= warnings * 7
    scores["overall"] = _clamp(total)
    return scores


def classify(score: float, completeness: float, governance_flag: int = 0) -> str:
    if completeness < 55:
        return "INSUFFICIENT EVIDENCE"
    if governance_flag:
        return "AVOID / INVESTIGATE"
    if score >= 78:
        return "STRONG BUY CANDIDATE"
    if score >= 68:
        return "BUY CANDIDATE"
    if score >= 58:
        return "WATCH"
    if score >= 47:
        return "HOLD / NEUTRAL"
    return "AVOID"


def explain(row: pd.Series) -> Tuple[List[str], List[str]]:
    positives, risks = [], []
    if row["quality_score"] >= 65: positives.append("Strong profitability and financial quality")
    if row["value_score"] >= 65: positives.append("Attractive valuation relative to sector thresholds")
    if row["dividend_score"] >= 65: positives.append("Supportive dividend yield and payment record")
    if row["growth_score"] >= 65: positives.append("Improving earnings or revenue growth")
    if row["momentum_score"] >= 65: positives.append("Positive medium-term price momentum")
    if row["liquidity_score"] < 45: risks.append("Low liquidity may make entry or exit difficult")
    if row["risk_score"] < 45: risks.append("Elevated volatility or historical drawdown")
    if row.get("payout_ratio_pct", 0) > 100: risks.append("Dividend payout may not be sustainable")
    if row.get("earnings_growth_pct", 0) < 0: risks.append("Latest earnings growth is negative")
    if row.get("governance_flag", 0): risks.append("Governance or material-announcement flag requires review")
    if row.get("data_completeness_pct", 100) < 75: risks.append("Recommendation uses incomplete data")
    if not positives: positives.append("No major positive factor is strong enough yet")
    if not risks: risks.append("No major quantitative warning; review announcements manually")
    return positives, risks


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    required = {"ticker", "company", "sector", "price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    numeric = [
        "price", "pe_ratio", "price_to_book", "roe_pct", "net_margin_pct",
        "interest_cover", "dividend_yield_pct", "dividend_years",
        "payout_ratio_pct", "return_3m_pct", "return_12m_pct",
        "earnings_growth_pct", "revenue_growth_pct", "avg_daily_value_kes",
        "zero_volume_days_pct", "volatility_pct", "max_drawdown_pct",
        "data_completeness_pct", "governance_flag",
    ]
    work = df.copy()
    for col in numeric:
        if col not in work: work[col] = np.nan
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work["data_completeness_pct"] = work["data_completeness_pct"].fillna(
        work[numeric[:-2]].notna().mean(axis=1) * 100
    )
    work["governance_flag"] = work["governance_flag"].fillna(0).astype(int)

    score_records = [score_row(row) for _, row in work.iterrows()]
    scores = pd.DataFrame(score_records, index=work.index)
    for key in WEIGHTS:
        work[f"{key}_score"] = scores[key].round(1)
    work["overall_score"] = scores["overall"].round(1)
    work["signal"] = work.apply(
        lambda r: classify(r["overall_score"], r["data_completeness_pct"], r["governance_flag"]), axis=1
    )
    reasons = work.apply(explain, axis=1)
    work["positives"] = reasons.map(lambda x: "; ".join(x[0]))
    work["risks"] = reasons.map(lambda x: "; ".join(x[1]))
    work["suggested_entry_low"] = (work["price"] * 0.95).round(2)
    work["suggested_entry_high"] = (work["price"] * 1.01).round(2)
    work["review_below"] = (work["price"] * 0.85).round(2)
    return work.sort_values(["overall_score", "liquidity_score"], ascending=False).reset_index(drop=True)


def portfolio_suggestion(analyzed: pd.DataFrame, amount: float, max_positions: int = 5) -> pd.DataFrame:
    candidates = analyzed[
        analyzed["signal"].isin(["STRONG BUY CANDIDATE", "BUY CANDIDATE"])
        & (analyzed["liquidity_score"] >= 45)
        & (analyzed["data_completeness_pct"] >= 70)
    ].head(max_positions).copy()
    if candidates.empty:
        return pd.DataFrame(columns=["ticker", "company", "allocation_pct", "allocation_kes", "shares", "cash_left_kes"])
    raw = candidates["overall_score"] - 55
    weights = raw / raw.sum() * 0.80  # keep a 20% cash buffer
    weights = weights.clip(upper=0.30)
    weights = weights / weights.sum() * min(0.80, weights.sum())
    candidates["allocation_pct"] = (weights * 100).round(1)
    candidates["allocation_kes"] = (weights * amount).round(0)
    candidates["shares"] = np.floor(candidates["allocation_kes"] / candidates["price"]).astype(int)
    invested = (candidates["shares"] * candidates["price"]).sum()
    candidates["cash_left_kes"] = round(amount - invested, 2)
    return candidates[["ticker", "company", "signal", "overall_score", "allocation_pct", "allocation_kes", "shares", "cash_left_kes"]]

