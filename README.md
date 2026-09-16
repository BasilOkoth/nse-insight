# NSE Insight

A private, evidence-led dashboard for analysing Nairobi Securities Exchange shares with free end-of-day data. It automatically retrieves the public NSE market-statistics tables, records daily history through GitHub Actions, and ranks shares using a balanced model weighted toward long-term financial quality, valuation and dividends.

## Features

- Transparent 100-point scoring model
- Strong buy candidate, buy candidate, watch, hold and avoid classifications
- Sector-aware thresholds for banks, insurers and other companies
- Evidence and risk explanations for every result
- Entry-zone and review-level prompts
- Portfolio allocation illustration with liquidity filters and cash buffer
- Governance and missing-data overrides
- CSV/Excel imports and CSV exports
- Demonstration data and reusable input template
- Automatic official NSE market snapshot
- Scheduled GitHub Action for persistent price history
- Render deployment blueprint

## Start on Windows

1. Install Python 3.11 or newer.
2. Extract this project.
3. Open PowerShell inside the extracted `nse-insight` folder.
4. Run:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

The dashboard will open in your browser. It runs locally; the imported portfolio and research data are not sent to a custom server by this project.

## Deploy on Render through GitHub

1. Upload the contents of this folder to a GitHub repository.
2. In GitHub, open **Actions**, enable workflows, and run **Update NSE market history** once.
3. In Render, choose **New → Blueprint**, connect the repository and approve `render.yaml`.
4. Render will install the requirements and start the Streamlit application automatically.

The GitHub Action runs after NSE trading on weekdays and commits both the latest snapshot and accumulated history to the repository. Render therefore loads quickly without relying on its temporary free-tier filesystem. A manual refresh button can check NSE directly.

## Use real data

Current price and volume data are fetched automatically. For verified long-term recommendations, populate `data/fundamentals.csv` from:

- NSE daily equity price lists and market statistics
- Audited annual reports and recent interim results
- Official corporate actions and issuer announcements

The app deliberately withholds buy recommendations when verified fundamentals or sufficient history are absent. It never converts missing evidence into a confident signal. The bundled demonstration companies and figures are fictional and are not market recommendations.

## Model

| Factor | Weight |
|---|---:|
| Financial quality | 25% |
| Valuation | 20% |
| Dividends | 15% |
| Momentum | 15% |
| Growth | 10% |
| Liquidity | 10% |
| Risk quality | 5% |

The model is deterministic and auditable. Missing values receive neutral factor scores, but weak overall completeness blocks a normal recommendation. Governance flags override quantitative scores.

## Important

This software provides private decision support, not guaranteed forecasts or regulated investment advice. Verify current prices, announcements, taxes, fees and suitability before trading. Historical results do not guarantee future returns.
