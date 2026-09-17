NSE INSIGHT — ALL 19 VERIFIED FUNDAMENTALS PACK

This is the combined pack so you do not need to upload the earlier 7-company
starter and then a second file.

Companies included (19):
KCB Group, Equity Group, Co-operative Bank, NCBA Group, Stanbic Holdings,
Safaricom, KenGen, Absa Bank Kenya, EABL, Kenya Power, BAT Kenya,
Jubilee Holdings, Diamond Trust Bank Kenya, I&M Group, TotalEnergies
Marketing Kenya, Britam Holdings, Kenya Re, Carbacid Investments, Centum.

FILES
-----
data/fundamentals_raw.csv   -> source facts + provenance for all 19
data/fundamentals.csv       -> already built using the repo's 15-Sep-2026 prices
build_fundamentals.py       -> rebuilds ratios whenever market_snapshot.csv changes
templates/market/dashboard.html -> evidence-aware ranking heading

UPLOAD
------
Upload the contents preserving the same folder paths.

Because fundamentals.csv is already included, the app can use the data
immediately after deploy. On later NSE price refreshes, run:

    python build_fundamentals.py

or rely on the existing refresh integration if already installed.

NOTES
-----
- Missing cells are intentional where a verified value was not captured.
- The scoring model should continue to withhold normal signals where evidence
  completeness is below its threshold.
- Do not fill gaps from unverified finance blogs.
- Monetary statement figures are stored in the units used in the source row;
  ratio calculations only divide like-for-like statement amounts.
