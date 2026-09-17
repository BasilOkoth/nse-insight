# NSE Insight — Premium Decision Intelligence Upgrade

This package is a complete interface and decision-support upgrade for the existing `BasilOkoth/nse-insight` project.

## What changes

- Premium visual system: deep navy surfaces, glass panels, gradients, motion, hover lighting, polished typography, responsive mobile navigation.
- Dynamic experience: animated counters, scroll reveals, live screener search, sortable screener columns, density toggle, theme toggle, refresh animation.
- Plain-English stock research brief for non-finance users.
- Evidence confidence on every company.
- “Why it stands out”, “Why you may wait”, “What must go right” and “What breaks the thesis”.
- KES investment illustration per stock.
- New premium Stock A vs Stock B comparison page.
- Premium portfolio and methodology pages.

## Upload these paths to GitHub

Replace existing files where they exist and add the two new files.

### New
- `market/decision_support.py`
- `templates/market/compare.html`
- `static/js/app.js`

### Replace
- `market/views.py`
- `market/urls.py`
- `templates/base.html`
- `templates/market/dashboard.html`
- `templates/market/stocks.html`
- `templates/market/stock_detail.html`
- `templates/market/portfolio.html`
- `templates/market/methodology.html`
- `static/css/app.css`
- `tests/test_django_views.py`

After committing to `main`, Render should redeploy. Because `render.yaml` already runs `collectstatic`, the new CSS and JavaScript will be collected automatically.

## New page

`/compare/`

Use it to select any two stocks and see an evidence-backed, plain-language comparison.

## Important

The interface deliberately says “model case” rather than presenting a guaranteed or personalised trading instruction. The goal is to explain the evidence deeply enough that a non-finance user can understand why one company currently looks stronger or weaker than another.
