"""Streamlit dashboard. Run: streamlit run app.py
Optional modules (backtest, whatif, events, stocks, notegen) appear as extra tabs automatically
when their .py file is present in this folder."""
import importlib
import os
import pandas as pd
import plotly.express as px
import streamlit as st
import analysis as an
import data

st.set_page_config(page_title="Gold Tracker India", layout="wide")
st.title("Gold Tracker: Indian Investor View")
st.caption("Global gold → USD/INR → Indian market factors.")

OPTIONAL = ["backtest", "whatif", "events", "stocks", "notegen"]


@st.cache_data(ttl=6 * 3600)
def load():
    """Returns (monthly, stocks, daily, warning). Falls back to practice data if live data is unavailable."""
    if not os.getenv("FRED_API_KEY"):
        import sample_data
        return (*sample_data.generate(), "No FRED_API_KEY found, so this is randomly generated PRACTICE data.")
    try:
        return data.build_monthly(), data.stock_prices(), data.daily_prices(), None
    except Exception as e:  # network or key problem
        import sample_data
        return (*sample_data.generate(), f"Live data failed ({type(e).__name__}: {e}). Showing PRACTICE data.")


df, stocks, daily, warning = load()
if warning:
    st.warning(warning)
ctx = {"df": df, "stocks": stocks, "daily": daily}

mods = []
for name in OPTIONAL:
    try:
        mods.append(importlib.import_module(name))
    except ModuleNotFoundError as e:
        if e.name != name:  # a real missing library, not just an absent optional file
            raise

core = ["Scorecard", "What drives gold", "Rupee bridge", "Why rupee gold moved", "Gold stocks", "Monthly note"]
tabs = st.tabs(core + [m.TITLE for m in mods])
t1, t2, t3, t4, t5, t6 = tabs[:6]

with t1:
    sc = an.scorecard(df)
    counts = sc["Signal"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("Supportive", counts.get("Supportive", 0))
    c2.metric("Neutral", counts.get("Neutral", 0))
    c3.metric("Negative", counts.get("Negative", 0))
    st.dataframe(sc, width="stretch", hide_index=True)
    st.plotly_chart(px.line(df, y="gold_inr_10g", title="Gold in ₹ per 10 g"), width="stretch")

with t2:
    model = an.regression(df)
    st.write(f"**Regression:** monthly gold return vs changes in real yield, dollar and inflation expectations "
             f"(R² = {model.rsquared:.2f}, n = {int(model.nobs)})")
    st.dataframe(pd.DataFrame({"coefficient": model.params.round(4), "p-value": model.pvalues.round(3)}))
    st.plotly_chart(px.line(an.rolling_corr(df), title="24-month rolling correlation with gold"),
                    width="stretch")
    st.caption("Correlations drift over time. That instability is the finding: no single driver works all the time.")

with t3:
    last = df.iloc[-1]
    a, b, c, d = st.columns(4)
    usd = a.number_input("Gold (USD/oz)", value=float(round(last["gold"], 1)))
    fx = b.number_input("USD/INR", value=float(round(last["usdinr"], 2)))
    duty = c.number_input("Import duty %", value=float(last["duty"]) if pd.notna(last["duty"]) else 6.0)
    gst = d.number_input("GST %", value=3.0)
    quote = st.number_input("Indian quote (₹/10 g)", value=float(round(last["gold_inr_10g"] * (1 + duty / 100) * 1.03, 0)))
    r = an.rupee_bridge(usd, fx, duty, gst, quote)
    st.metric("Fair value (₹/10 g)", f"{r['fair_value']:,.0f}", f"{r['premium_pct']:+.1f}% quote vs fair value")

with t4:
    months = st.select_slider("Look-back window (months)", [3, 6, 12, 24], value=12)
    dec = an.decompose(df, months)
    last = dec.iloc[-1]
    st.subheader(f"Rupee gold moved {last['Total']:+.1f}% over {months} months")
    a, b, c = st.columns(3)
    a.metric("From global gold", f"{last['Global gold (USD)']:+.1f} pts")
    b.metric("From the rupee", f"{last['Rupee (USD/INR)']:+.1f} pts")
    c.metric("From import duty", f"{last['Import duty']:+.1f} pts")
    st.plotly_chart(px.bar(dec.drop(columns="Total"), barmode="relative",
                           title=f"{months}-month rupee gold change, split by cause"), width="stretch")
    st.caption("Log percentage points, so the three pieces add up to the total. Duty history comes from data/import_duty.csv.")
    india_cols = [c for c in ["repo", "india_cpi_yoy", "india_real_rate"] if c in df]
    if india_cols:
        st.plotly_chart(px.line(df[india_cols].dropna(how="all"),
                                title="India: repo rate, CPI inflation and real rate"), width="stretch")

with t5:
    st.dataframe(an.gold_beta(stocks, df), width="stretch", hide_index=True)
    st.caption("Beta = how much the stock moved for each 1% move in rupee gold (monthly data).")

with t6:
    st.text_area("Write this month's view (what changed, what matters, your call)", height=200)

for m, t in zip(mods, tabs[6:]):
    with t:
        m.render(st, ctx)
