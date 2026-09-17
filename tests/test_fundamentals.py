from pathlib import Path

import pandas as pd

import build_fundamentals as bf


def test_builds_market_dependent_ratios(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()

    raw = pd.DataFrame([{
        "ticker": "TEST",
        "financial_period": "FY2025",
        "source_name": "Test issuer",
        "source_type": "Audited annual report",
        "source_url": "https://example.com/report.pdf",
        "verified_on": "2026-09-17",
        "eps": 10,
        "book_value_per_share": 50,
        "profit_after_tax": 120,
        "prior_profit_after_tax": 100,
        "revenue": 1000,
        "prior_revenue": 900,
        "total_equity": 600,
        "prior_total_equity": 500,
        "ebit": 180,
        "finance_cost": 30,
        "dividend_per_share": 4,
        "dividend_years": 5,
        "governance_flag": 0,
    }])
    raw.to_csv(data / "fundamentals_raw.csv", index=False)
    pd.DataFrame([{"ticker": "TEST", "price": 100}]).to_csv(
        data / "market_snapshot.csv", index=False
    )

    monkeypatch.setattr(bf, "RAW_PATH", data / "fundamentals_raw.csv")
    monkeypatch.setattr(bf, "OUTPUT_PATH", data / "fundamentals.csv")
    monkeypatch.setattr(bf, "SNAPSHOT_PATH", data / "market_snapshot.csv")

    result = bf.build_fundamentals().iloc[0]

    assert result["pe_ratio"] == 10
    assert result["price_to_book"] == 2
    assert round(result["dividend_yield_pct"], 1) == 4.0
    assert round(result["payout_ratio_pct"], 1) == 40.0
    assert result["data_completeness_pct"] >= 80


def test_rejects_unverifiable_source(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()

    pd.DataFrame([{
        "ticker": "TEST",
        "financial_period": "FY2025",
        "source_url": "",
    }]).to_csv(data / "fundamentals_raw.csv", index=False)

    pd.DataFrame([{"ticker": "TEST", "price": 100}]).to_csv(
        data / "market_snapshot.csv", index=False
    )

    monkeypatch.setattr(bf, "RAW_PATH", data / "fundamentals_raw.csv")
    monkeypatch.setattr(bf, "OUTPUT_PATH", data / "fundamentals.csv")
    monkeypatch.setattr(bf, "SNAPSHOT_PATH", data / "market_snapshot.csv")

    try:
        bf.build_fundamentals()
    except ValueError as exc:
        assert "HTTPS source_url" in str(exc)
    else:
        raise AssertionError("Expected an invalid source URL to be rejected")
