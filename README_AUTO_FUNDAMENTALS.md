NSE INSIGHT — AUTOMATIC FUNDAMENTALS v1

WHAT THIS DOES
--------------
This is the step that stops you manually filling all 70 securities.

The updater:
1. Reads the securities already present in data/market_snapshot.csv.
2. Crawls the Capital Markets Authority (CMA) Annual Report Resource Center.
3. Discovers CMA sector pages and listed-company pages automatically.
4. Fuzzy-matches NSE company names to the CMA archive, with aliases for renamed firms.
5. Finds the latest annual-report PDF exposed by the CMA company page.
6. Extracts text from text-based PDFs with pypdf.
7. Looks for report facts such as:
   - EPS
   - dividend per share
   - ROE
   - revenue
   - profit after tax
   - equity
   - operating profit
   - finance cost
   - reported growth percentages
8. AUTO-ACCEPTS only high-confidence extractions.
9. Sends medium/low-confidence extractions to:
      data/fundamentals_review_queue.csv
10. Writes discovery status for every security to:
      data/fundamental_sources.csv
11. Preserves existing manually verified fundamentals.
12. Calls build_fundamentals.py to recalculate ratios.
13. Runs weekly through GitHub Actions.

WHY THERE IS A REVIEW QUEUE
---------------------------
Annual reports are not standardized enough for safe blind extraction.
A wrong PAT/EPS/dividend is worse than a missing value.

The system therefore automates the repetitive work and only surfaces
ambiguous exceptions. Scanned PDFs or weak matches are not silently treated
as verified evidence.

PRIMARY SOURCE
--------------
https://annualreport.cma.or.ke/

The CMA portal is useful because it already organizes listed companies by
sector and exposes annual-report archives for many issuers.

FILES TO ADD/REPLACE
--------------------
ADD:
  fundamentals/__init__.py
  fundamentals/auto_update.py
  auto_fundamentals.py
  .github/workflows/update_fundamentals.yml
  tests/test_auto_fundamentals.py

REPLACE:
  requirements.txt

DO NOT DELETE
-------------
Keep your existing:
  data/fundamentals_raw.csv
  data/fundamentals.csv
  build_fundamentals.py

Those are the verified evidence base. The auto updater extends them.

FIRST RUN
---------
After uploading the files:

GitHub -> Actions -> Update verified fundamentals -> Run workflow

Or locally:
  pip install -r requirements.txt
  python auto_fundamentals.py

For a safe discovery-only dry run:
  python auto_fundamentals.py --discover-only

OUTPUTS
-------
data/fundamental_sources.csv
data/fundamentals_review_queue.csv
data/fundamentals_raw.csv
data/fundamentals.csv

IMPORTANT
---------
This does not promise that all 70 reports will parse perfectly.
It is specifically designed so failures become visible in the review queue
rather than corrupting investment signals.
