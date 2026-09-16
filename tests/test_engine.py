import pandas as pd

from analysis_engine import analyze, portfolio_suggestion


def test_strong_company_ranks_above_weak_company():
    data = pd.read_csv("data/demo_nse_data.csv")
    result = analyze(data)
    alpha = result.loc[result.ticker == "ALPHA", "overall_score"].iloc[0]
    epsi = result.loc[result.ticker == "EPSI", "overall_score"].iloc[0]
    assert alpha > epsi


def test_governance_flag_blocks_buy_signal():
    data = pd.read_csv("data/demo_nse_data.csv")
    result = analyze(data)
    theta = result.loc[result.ticker == "THETA"].iloc[0]
    assert theta.signal == "AVOID / INVESTIGATE"


def test_portfolio_keeps_cash_buffer():
    data = pd.read_csv("data/demo_nse_data.csv")
    result = analyze(data)
    portfolio = portfolio_suggestion(result, 100_000)
    if not portfolio.empty:
        invested = sum(portfolio.shares * portfolio.merge(result[["ticker", "price"]], on="ticker").price)
        assert invested <= 100_000

