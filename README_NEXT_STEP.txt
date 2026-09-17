NSE INSIGHT — VERIFIED FUNDAMENTALS ENGINE v1

WHAT THIS PATCH DOES
--------------------
1. Adds data/fundamentals_raw.csv as the evidence input.
2. Adds build_fundamentals.py.
3. Recalculates market-dependent ratios from the latest NSE price:
   - P/E
   - price-to-book
   - dividend yield
4. Derives report ratios when raw report values are supplied:
   - ROE
   - net margin
   - interest cover
   - earnings growth
   - revenue growth
   - payout ratio
5. Computes evidence completeness automatically.
6. Rejects fundamentals rows without an HTTPS source URL.
7. Preserves the source name, source type, financial period and verification date.
8. Shows the evidence source on the stock-detail page.
9. Rebuilds market-dependent fundamentals after an NSE price refresh.
10. Includes tests.

IMPORTANT
---------
This version deliberately DOES NOT invent or scrape unverified company figures.
The next data step is to populate fundamentals_raw.csv from audited annual
reports, interim results and official issuer/NSE publications.

INSTALL
-------
Replace/add these repository files:

ADD:
- build_fundamentals.py
- data/fundamentals_raw.csv
- tests/test_fundamentals.py

REPLACE:
- market/services.py
- nse_data.py
- templates/market/stock_detail.html
- templates/market/methodology.html

Then run locally or in GitHub Actions:
    python build_fundamentals.py

When data/fundamentals_raw.csv has verified rows, the script writes:
    data/fundamentals.csv

No new Python package is required.
