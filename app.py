from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis_engine import WEIGHTS, analyze, portfolio_suggestion
from nse_data import add_market_metrics, fetch_nse_snapshot, load_history, merge_fundamentals


ROOT = Path(__file__).parent
DEMO = ROOT / "data" / "demo_nse_data.csv"
TEMPLATE = ROOT / "data" / "nse_input_template.csv"
HISTORY = ROOT / "data" / "market_history.csv"
FUNDAMENTALS = ROOT / "data" / "fundamentals.csv"
SNAPSHOT = ROOT / "data" / "market_snapshot.csv"

st.set_page_config(page_title="NSE Insight", page_icon="📈", layout="wide")
st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1400px;}
  [data-testid="stMetric"] {background:#111827; border:1px solid #263244; padding:16px; border-radius:14px;}
  .signal {padding:12px 16px;border-radius:12px;background:#0f172a;border-left:5px solid #22c55e;margin-bottom:10px;}
  .muted {color:#94a3b8;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.title("NSE Insight")
st.caption("Private, evidence-led analysis for Nairobi Securities Exchange shares · End-of-day investing")

with st.sidebar:
    st.header("Data")
    source = st.radio("Choose data source", ["Automatic NSE data", "Demo dataset", "Upload my CSV/Excel"], index=0)
    uploaded = None
    if source == "Upload my CSV/Excel":
        uploaded = st.file_uploader("Upload completed template", type=["csv", "xlsx"])
        st.download_button("Download input template", TEMPLATE.read_bytes(), "nse_input_template.csv", "text/csv")
    amount = st.number_input("Amount available (KES)", min_value=1_000, value=100_000, step=5_000)
    max_positions = st.slider("Maximum positions", 2, 8, 5)
    st.divider()
    st.warning("Decision-support only. Verify current prices, announcements and your personal risk before trading.")

if source == "Automatic NSE data":
    @st.cache_data(ttl=3600, show_spinner="Fetching the latest official NSE market statistics…")
    def current_market():
        return fetch_nse_snapshot()

    refresh = st.sidebar.button("Refresh directly from NSE")
    try:
        if refresh or not SNAPSHOT.exists():
            snapshot, market_date = current_market()
        else:
            snapshot = pd.read_csv(SNAPSHOT)
            market_date = str(snapshot["as_of"].iloc[0]) if "as_of" in snapshot else "latest recorded session"
        market = add_market_metrics(snapshot, load_history(HISTORY))
        raw = merge_fundamentals(market, FUNDAMENTALS)
        st.success(f"Official NSE market statistics loaded · {market_date}")
        st.caption("The bundled snapshot is refreshed by GitHub Actions after trading. Use ‘Refresh directly from NSE’ for an immediate check.")
        if raw.get("data_completeness_pct", pd.Series(dtype=float)).notna().sum() == 0:
            st.warning("Prices are current, but verified company fundamentals have not yet been added to data/fundamentals.csv. The system will withhold buy signals rather than invent evidence.")
    except Exception as exc:
        st.error(f"The official NSE source is temporarily unavailable: {exc}")
        st.info("Select Demo dataset to inspect the interface, or try refreshing later.")
        st.stop()
elif source == "Demo dataset":
    raw = pd.read_csv(DEMO)
    st.info("Demo mode uses illustrative figures—not current recommendations. Upload verified data before making a decision.")
elif uploaded is not None:
    raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
else:
    st.stop()

try:
    results = analyze(raw)
except Exception as exc:
    st.error(f"Could not analyze the file: {exc}")
    st.stop()

buy_count = results["signal"].isin(["STRONG BUY CANDIDATE", "BUY CANDIDATE"]).sum()
top_score = results["overall_score"].max()
median_liquidity = results["liquidity_score"].median()
avg_complete = results["data_completeness_pct"].mean()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Buy candidates", int(buy_count))
c2.metric("Highest score", f"{top_score:.1f}/100")
c3.metric("Median liquidity", f"{median_liquidity:.0f}/100")
c4.metric("Data completeness", f"{avg_complete:.0f}%")

tabs = st.tabs(["Rankings", "Stock review", "Portfolio idea", "Methodology", "Data guide"])

with tabs[0]:
    st.subheader("Balanced opportunity ranking")
    display_cols = ["ticker", "company", "sector", "price", "signal", "overall_score", "quality_score", "value_score", "dividend_score", "growth_score", "momentum_score", "liquidity_score", "risk_score"]
    st.dataframe(results[display_cols], use_container_width=True, hide_index=True,
                 column_config={"overall_score": st.column_config.ProgressColumn("Overall", min_value=0, max_value=100)})
    fig = px.scatter(results, x="risk_score", y="overall_score", size="avg_daily_value_kes", color="signal",
                     hover_name="ticker", hover_data=["company", "price"], title="Opportunity versus risk-quality score")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("Export full analysis", results.to_csv(index=False).encode(), "nse_analysis.csv", "text/csv")

with tabs[1]:
    ticker = st.selectbox("Select a stock", results["ticker"].tolist())
    r = results.loc[results["ticker"] == ticker].iloc[0]
    st.markdown(f"<div class='signal'><b>{r['signal']}</b> · {r['company']} ({r['ticker']}) · Score {r['overall_score']}/100</div>", unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("Latest price", f"KES {r['price']:,.2f}")
    b.metric("Entry zone", f"{r['suggested_entry_low']:,.2f}–{r['suggested_entry_high']:,.2f}")
    c.metric("Review below", f"KES {r['review_below']:,.2f}")
    d.metric("Data completeness", f"{r['data_completeness_pct']:.0f}%")
    left, right = st.columns(2)
    with left:
        st.success("**Supporting evidence**\n\n" + "\n\n".join(f"• {x}" for x in r["positives"].split("; ")))
    with right:
        st.error("**Risks and checks**\n\n" + "\n\n".join(f"• {x}" for x in r["risks"].split("; ")))
    score_cols = [f"{k}_score" for k in WEIGHTS]
    radar = pd.DataFrame({"factor": [k.title() for k in WEIGHTS], "score": [r[c] for c in score_cols]})
    st.plotly_chart(px.bar(radar, x="score", y="factor", orientation="h", range_x=[0,100], title="Factor scores"), use_container_width=True)

with tabs[2]:
    st.subheader(f"Illustrative allocation for KES {amount:,.0f}")
    allocation = portfolio_suggestion(results, amount, max_positions)
    if allocation.empty:
        st.warning("No stock passes the evidence, liquidity and score thresholds. The model suggests holding cash.")
    else:
        st.dataframe(allocation, use_container_width=True, hide_index=True)
        st.caption("The model deliberately retains a cash buffer and caps concentration. This is not an instruction to execute trades.")

with tabs[3]:
    st.subheader("Transparent balanced model")
    weights_df = pd.DataFrame({"factor": [k.title() for k in WEIGHTS], "weight_pct": [v*100 for v in WEIGHTS.values()]})
    st.plotly_chart(px.bar(weights_df, x="factor", y="weight_pct", text="weight_pct", title="Model weights"), use_container_width=True)
    st.markdown("""
The engine emphasizes financial quality, value and dividends. Growth and momentum help identify improving opportunities, while liquidity and downside risk prevent attractive-looking but difficult-to-trade shares from ranking too highly.

**Hard safeguards:** incomplete data cannot receive a normal buy signal; governance flags override the score; very illiquid shares are excluded from portfolio suggestions; and the engine can recommend holding cash.
""")

with tabs[4]:
    st.subheader("Using free data responsibly")
    st.markdown("""
1. The dashboard retrieves the official NSE market-statistics tables automatically and caches them for one hour.
2. The included GitHub Action records one closing snapshot each weekday, allowing momentum, volatility and liquidity measures to develop over time.
3. Maintain `data/fundamentals.csv` from audited annual reports and the most recent interim results. These figures change much less frequently than prices.
4. Check corporate actions and issuer announcements for dividends, rights issues, warnings or governance events.
5. Set `governance_flag` to `1` whenever a material issue needs manual investigation.
6. Each fundamentals row includes its financial period and source URL so recommendations remain auditable.

Do not treat the bundled demonstration data as current market information.
""")
