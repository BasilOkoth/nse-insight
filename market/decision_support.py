from __future__ import annotations

import math
from typing import Any, Dict, List


FACTOR_LABELS = {
    "quality": "Business quality",
    "value": "Valuation",
    "dividend": "Dividend strength",
    "momentum": "Price trend",
    "growth": "Growth",
    "liquidity": "Ease of buying/selling",
    "risk": "Price risk",
}


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
        if math.isnan(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _pct(value: Any, digits: int = 1) -> str:
    number = _num(value)
    return "Not available" if number is None else f"{number:.{digits}f}%"


def _factor_score(stock: Dict[str, Any], factor: str) -> float:
    return _num(stock.get(f"{factor}_score")) or 0.0


def _confidence(stock: Dict[str, Any]) -> Dict[str, str]:
    completeness = _num(stock.get("data_completeness_pct")) or 0.0
    if completeness >= 85:
        return {
            "label": "HIGH",
            "class": "high",
            "plain": "Most of the financial evidence expected by the model is present.",
        }
    if completeness >= 70:
        return {
            "label": "MODERATE",
            "class": "moderate",
            "plain": "There is enough evidence for a useful view, but some important fields are still missing.",
        }
    if completeness >= 55:
        return {
            "label": "LIMITED",
            "class": "limited",
            "plain": "Treat this as a research lead rather than a strong conclusion.",
        }
    return {
        "label": "LOW",
        "class": "low",
        "plain": "There is not enough verified financial evidence for a dependable conclusion.",
    }


def _factor_explanation(stock: Dict[str, Any], factor: str) -> str:
    score = _factor_score(stock, factor)

    if factor == "quality":
        roe = _num(stock.get("roe_pct"))
        margin = _num(stock.get("net_margin_pct"))
        bits = []
        if roe is not None:
            bits.append(f"return on equity is {roe:.1f}%")
        if margin is not None:
            bits.append(f"net margin is {margin:.1f}%")
        if bits:
            return f"Business quality scores {score:.1f}/100 because " + " and ".join(bits) + "."
        return f"Business quality scores {score:.1f}/100 from the verified profitability evidence currently available."

    if factor == "value":
        pe = _num(stock.get("pe_ratio"))
        pb = _num(stock.get("price_to_book"))
        bits = []
        if pe is not None:
            bits.append(f"P/E is {pe:.1f}×")
        if pb is not None:
            bits.append(f"price-to-book is {pb:.2f}×")
        if bits:
            return f"Valuation scores {score:.1f}/100; " + " and ".join(bits) + ". The model rewards cheaper valuations only when the business evidence also holds up."
        return f"Valuation scores {score:.1f}/100, but the underlying valuation multiples are not fully available."

    if factor == "dividend":
        dy = _num(stock.get("dividend_yield_pct"))
        dps = _num(stock.get("dividend_per_share"))
        years = _num(stock.get("dividend_years"))
        bits = []
        if dy is not None:
            bits.append(f"yield is about {dy:.1f}%")
        if dps is not None:
            bits.append(f"dividend per share is KES {dps:.2f}")
        if years is not None:
            bits.append(f"the recorded payment history covers {int(years)} year(s)")
        if bits:
            return f"Dividend strength scores {score:.1f}/100; " + ", ".join(bits) + "."
        return f"Dividend strength scores {score:.1f}/100, but dividend evidence is incomplete."

    if factor == "growth":
        eg = _num(stock.get("earnings_growth_pct"))
        rg = _num(stock.get("revenue_growth_pct"))
        bits = []
        if eg is not None:
            bits.append(f"earnings growth is {eg:.1f}%")
        if rg is not None:
            bits.append(f"revenue growth is {rg:.1f}%")
        if bits:
            return f"Growth scores {score:.1f}/100 because " + " and ".join(bits) + "."
        return f"Growth scores {score:.1f}/100 with limited verified growth data."

    if factor == "momentum":
        r3 = _num(stock.get("return_3m_pct"))
        r12 = _num(stock.get("return_12m_pct"))
        bits = []
        if r3 is not None:
            bits.append(f"3-month return is {r3:.1f}%")
        if r12 is not None:
            bits.append(f"12-month return is {r12:.1f}%")
        if bits:
            return f"Price trend scores {score:.1f}/100; " + " and ".join(bits) + ". This describes price behaviour, not business value."
        return f"Price trend scores {score:.1f}/100."

    if factor == "liquidity":
        adv = _num(stock.get("avg_daily_value_kes"))
        zero = _num(stock.get("zero_volume_days_pct"))
        bits = []
        if adv is not None:
            bits.append(f"average daily traded value is about KES {adv:,.0f}")
        if zero is not None:
            bits.append(f"zero-volume days are {zero:.1f}%")
        if bits:
            return f"Ease of buying and selling scores {score:.1f}/100; " + " and ".join(bits) + "."
        return f"Ease of buying and selling scores {score:.1f}/100."

    vol = _num(stock.get("volatility_pct"))
    draw = _num(stock.get("max_drawdown_pct"))
    bits = []
    if vol is not None:
        bits.append(f"historical volatility is {vol:.1f}%")
    if draw is not None:
        bits.append(f"maximum recorded drawdown is {draw:.1f}%")
    if bits:
        return f"Price risk scores {score:.1f}/100; " + " and ".join(bits) + "."
    return f"Price risk scores {score:.1f}/100."


def decision_brief(stock: Dict[str, Any], example_amount: float = 100000) -> Dict[str, Any]:
    score = _num(stock.get("overall_score")) or 0.0
    completeness = _num(stock.get("data_completeness_pct")) or 0.0
    signal = str(stock.get("signal") or "INSUFFICIENT EVIDENCE")
    confidence = _confidence(stock)

    ranked = sorted(
        ((factor, _factor_score(stock, factor)) for factor in FACTOR_LABELS),
        key=lambda item: item[1],
        reverse=True,
    )
    strongest = ranked[:3]
    weakest = sorted(ranked, key=lambda item: item[1])[:3]

    if completeness < 55:
        stance = "WAIT FOR EVIDENCE"
        tone = "limited"
        headline = "There is not enough verified financial evidence to make a strong case yet."
    elif signal == "STRONG BUY CANDIDATE":
        stance = "VERY ATTRACTIVE MODEL CASE"
        tone = "strong"
        headline = "The evidence currently shows a strong combination of business quality, valuation and supporting market factors."
    elif signal == "BUY CANDIDATE":
        stance = "ATTRACTIVE MODEL CASE"
        tone = "positive"
        headline = "Several important factors are favourable, although the risks still need checking before any decision."
    elif signal == "WATCH":
        stance = "WATCH — NOT COMPELLING YET"
        tone = "watch"
        headline = "The company has strengths, but the total case is not strong enough to treat as a high-priority opportunity."
    elif signal == "AVOID / INVESTIGATE":
        stance = "INVESTIGATE BEFORE CONSIDERING"
        tone = "risk"
        headline = "A governance or material-risk flag overrides the numerical score."
    elif signal == "AVOID":
        stance = "WEAK MODEL CASE"
        tone = "risk"
        headline = "The current evidence does not support an attractive risk-versus-reward case."
    else:
        stance = "NEUTRAL"
        tone = "neutral"
        headline = "The current evidence is mixed rather than clearly attractive or clearly weak."

    why = [
        {
            "factor": FACTOR_LABELS[factor],
            "score": round(value, 1),
            "explanation": _factor_explanation(stock, factor),
        }
        for factor, value in strongest
        if value >= 55
    ]
    if not why:
        why = [{
            "factor": "No dominant strength",
            "score": round(score, 1),
            "explanation": "No major factor currently scores strongly enough to carry the investment case on its own.",
        }]

    reasons_to_wait: List[Dict[str, str]] = []
    for factor, value in weakest:
        if value < 50:
            reasons_to_wait.append({
                "factor": FACTOR_LABELS[factor],
                "explanation": _factor_explanation(stock, factor),
            })
    if completeness < 75:
        reasons_to_wait.append({
            "factor": "Evidence coverage",
            "explanation": f"Only {completeness:.0f}% of the model's expected evidence is currently available. Missing data can materially change the conclusion.",
        })
    if stock.get("governance_flag"):
        reasons_to_wait.append({
            "factor": "Governance / announcement flag",
            "explanation": "A material governance or announcement flag requires manual investigation before relying on the score.",
        })
    if not reasons_to_wait:
        reasons_to_wait.append({
            "factor": "No dominant quantitative warning",
            "explanation": "The model does not show a major numerical red flag, but new company announcements and financial results still need checking.",
        })

    price = _num(stock.get("price")) or 0.0
    dps = _num(stock.get("dividend_per_share"))
    dy = _num(stock.get("dividend_yield_pct"))
    shares = int(example_amount // price) if price > 0 else 0
    invested = shares * price
    if dps is not None:
        annual_dividend = shares * dps
    elif dy is not None:
        annual_dividend = invested * (dy / 100)
    else:
        annual_dividend = None

    what_must_go_right = []
    earnings_growth = _num(stock.get("earnings_growth_pct"))
    revenue_growth = _num(stock.get("revenue_growth_pct"))
    payout = _num(stock.get("payout_ratio_pct"))
    if earnings_growth is not None and earnings_growth > 0:
        what_must_go_right.append("Earnings growth needs to remain positive rather than being a one-off improvement.")
    if revenue_growth is not None and revenue_growth > 0:
        what_must_go_right.append("Revenue growth needs to translate into durable profits and cash generation.")
    if _factor_score(stock, "value") >= 65:
        what_must_go_right.append("The apparently attractive valuation must not be hiding a deterioration in the underlying business.")
    if _factor_score(stock, "dividend") >= 65:
        what_must_go_right.append("The dividend needs to remain supported by earnings and cash flow rather than debt or one-off gains.")
    if not what_must_go_right:
        what_must_go_right.append("Future financial results need to confirm that the current score is improving rather than deteriorating.")

    thesis_breakers = []
    if earnings_growth is not None:
        thesis_breakers.append("A sustained reversal in earnings growth would weaken the case.")
    if payout is not None and payout > 80:
        thesis_breakers.append("A high payout ratio leaves less room for the dividend if profits weaken.")
    if _factor_score(stock, "liquidity") < 55:
        thesis_breakers.append("Poor trading liquidity can make it difficult to enter or exit near the expected price.")
    thesis_breakers.append("A material governance, regulatory, debt, capital-raising or profit-warning announcement should trigger a fresh review.")

    return {
        "stance": stance,
        "tone": tone,
        "headline": headline,
        "score": round(score, 1),
        "confidence": confidence,
        "why": why,
        "reasons_to_wait": reasons_to_wait,
        "what_must_go_right": what_must_go_right,
        "thesis_breakers": thesis_breakers,
        "example": {
            "amount": example_amount,
            "price": price,
            "shares": shares,
            "invested": invested,
            "cash_left": example_amount - invested,
            "annual_dividend": annual_dividend,
            "dividend_yield": dy,
        },
        "key_numbers": [
            {"label": "P/E", "value": "Not available" if _num(stock.get("pe_ratio")) is None else f"{_num(stock.get('pe_ratio')):.1f}×", "plain": "How much investors currently pay for each shilling of reported earnings."},
            {"label": "Price / book", "value": "Not available" if _num(stock.get("price_to_book")) is None else f"{_num(stock.get('price_to_book')):.2f}×", "plain": "Share price compared with the accounting value of shareholders' equity."},
            {"label": "ROE", "value": _pct(stock.get("roe_pct")), "plain": "How effectively shareholders' capital is being turned into profit."},
            {"label": "Dividend yield", "value": _pct(stock.get("dividend_yield_pct")), "plain": "Approximate annual dividend relative to the current share price."},
            {"label": "Earnings growth", "value": _pct(stock.get("earnings_growth_pct")), "plain": "How quickly reported profit is changing."},
            {"label": "Evidence coverage", "value": f"{completeness:.0f}%", "plain": "How much of the evidence expected by the model is actually available."},
        ],
    }


def compare_briefs(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    brief_a = decision_brief(a)
    brief_b = decision_brief(b)
    completeness_a = _num(a.get("data_completeness_pct")) or 0
    completeness_b = _num(b.get("data_completeness_pct")) or 0

    factors = []
    for factor, label in FACTOR_LABELS.items():
        av = _factor_score(a, factor)
        bv = _factor_score(b, factor)
        diff = av - bv
        if abs(diff) >= 5:
            edge = "A" if diff > 0 else "B"
        else:
            edge = "EVEN"
        factors.append({
            "name": label,
            "a": round(av, 1),
            "b": round(bv, 1),
            "edge": edge,
        })

    score_a = _num(a.get("overall_score")) or 0
    score_b = _num(b.get("overall_score")) or 0

    if min(completeness_a, completeness_b) < 55:
        model_edge = "NO FAIR COMPARISON YET"
        summary = "At least one company lacks enough verified fundamental evidence. The apparent score gap could be misleading."
        tone = "limited"
    elif abs(score_a - score_b) < 3:
        model_edge = "TOO CLOSE TO CALL FROM THE SCORE ALONE"
        summary = "The overall scores are close. The useful question is where each company is stronger and what could go wrong."
        tone = "neutral"
    elif score_a > score_b:
        model_edge = f"{a.get('company', 'Stock A')} HAS THE STRONGER MODEL CASE"
        summary = f"Its evidence-backed score is {score_a:.1f} versus {score_b:.1f}. The factor comparison below shows where the advantage comes from."
        tone = "positive"
    else:
        model_edge = f"{b.get('company', 'Stock B')} HAS THE STRONGER MODEL CASE"
        summary = f"Its evidence-backed score is {score_b:.1f} versus {score_a:.1f}. The factor comparison below shows where the advantage comes from."
        tone = "positive"

    return {
        "a": brief_a,
        "b": brief_b,
        "factors": factors,
        "model_edge": model_edge,
        "summary": summary,
        "tone": tone,
    }
