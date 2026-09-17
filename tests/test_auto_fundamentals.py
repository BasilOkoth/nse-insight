from fundamentals.auto_update import normalize_company_name, similarity, extract_candidates


def test_name_matching_aliases():
    assert similarity("ABSA Bank Kenya Plc Ord 0.50", "Barclays Bank") >= 50
    assert similarity("IMH Holdings Ltd Ord 1.00", "I&M Holdings") >= 50
    assert similarity("Kenya Commercial Bank Ltd Ord 1.00", "Kenya Commercial Bank") >= 70


def test_extract_candidates_from_financial_highlights():
    text = """
    FINANCIAL HIGHLIGHTS
    Earnings per share 12.50
    Dividend per share 4.00
    Return on equity (%) 18.2
    Revenue growth (%) 9.5
    Earnings growth (%) 14.0

    Revenue 120,000 110,000
    Profit after tax 18,000 15,800
    Total equity 95,000 88,000
    Operating profit 25,000 22,000
    Finance costs 3,000 2,800
    """
    row, confidence, points = extract_candidates(text)
    assert row["eps"] == 12.5
    assert row["dividend_per_share"] == 4.0
    assert row["profit_after_tax"] == 18000.0
    assert row["prior_profit_after_tax"] == 15800.0
    assert row["revenue"] == 120000.0
    assert points >= 10
    assert confidence == "HIGH"
