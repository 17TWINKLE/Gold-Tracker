"""Gold ETF, Sovereign Gold Bond (SGB) and physical gold compared, with Nifty 50 for context.
SGB results are a MODEL (gold price plus the 2.5% coupon), not the actual return of any one tranche.
Facts used: SGBs started November 2015, run 8 years with exit from year 5, pay 2.5% a year in two instalments,
and no new tranche has been issued since February 2024. Tax rules changed in 2026, so returns here are pre-tax."""
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

TITLE = "ETF, SGB and gold"
HERE = os.path.dirname(__file__)
# Verify tickers on Yahoo Finance before relying on them.
ETFS = {"Nippon Gold BeES": "GOLDBEES.NS", "SBI Gold ETF": "SBIGETF.NS", "Kotak Gold ETF": "KOTAKGOLD.NS"}
SGB_RATE = 0.025


def close(ticker: str):
    try:
        s = yf.download(ticker, period="max", auto_adjust=True, progress=False)["Close"].squeeze()
    except Exception:
        return None
    if not len(s):
        return None
    if getattr(s.index, "tz", None) is not None:
        s.index = s.index.tz_localize(None)
    s.index = s.index.normalize()
    return s.dropna()


def inr_gold(daily: pd.DataFrame) -> pd.Series:
    """Gold in rupees per 10 g at global parity (no import duty, GST or local premium)."""
    return (daily["gold"] * daily["usdinr"] / 31.1035 * 10).dropna()


def xirr(flows):
    """Annual return from dated cash flows [(date, amount), ...] found by bisection."""
    t0 = flows[0][0]
    yrs = [((d - t0).days / 365.25, a) for d, a in flows]

    def npv(r):
        return sum(a / (1 + r) ** t for t, a in yrs)

    lo, hi = -0.99, 10.0
    if npv(lo) * npv(hi) > 0:
        return float("nan")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def sgb_model(issue, hold_years, price: pd.Series, invest=100000.0):
    """Buy at the gold price on the issue date, collect 2.5% a year in half-yearly coupons, sell at the end."""
    issue = pd.Timestamp(issue)
    end = issue + pd.DateOffset(years=hold_years)
    last = price.index[-1]
    matured = end <= last
    end = min(end, last)
    units = invest / price.asof(issue)
    flows = [(issue, -invest)]
    k = 1
    while issue + pd.DateOffset(months=6 * k) <= end:
        flows.append((issue + pd.DateOffset(months=6 * k), invest * SGB_RATE / 2))
        k += 1
    final = units * price.asof(end)
    flows.append((end, final))
    coupons = invest * SGB_RATE / 2 * (len(flows) - 2)
    return {"xirr": xirr(flows), "price_return": final / invest - 1, "coupons": coupons, "end": end, "matured": matured}


def growth(price, etf, nifty, start, invest, gst, making):
    """Value over time of the same amount put into each option from the same start date."""
    start = pd.Timestamp(start)
    first = max([start] + [s.index[0] for s in (etf, nifty) if s is not None])
    idx = price.index[price.index >= first]
    if len(idx) < 2:
        return None
    p0 = price.asof(idx[0])
    out = pd.DataFrame(index=idx)
    out["Physical gold (after GST and making charge)"] = invest / ((1 + gst / 100) * (1 + making / 100)) * price.reindex(idx) / p0
    coupon_steps = np.floor(((idx - idx[0]).days / 365.25) * 2)
    out["SGB model (price plus coupons)"] = invest * price.reindex(idx) / p0 + invest * SGB_RATE / 2 * coupon_steps
    if etf is not None:
        out["Gold ETF"] = invest * etf.reindex(idx, method="ffill") / etf.asof(idx[0])
    if nifty is not None:
        out["Nifty 50 (price only)"] = invest * nifty.reindex(idx, method="ffill") / nifty.asof(idx[0])
    return out.dropna(how="all")


def summary(g: pd.DataFrame) -> pd.DataFrame:
    years = max((g.index[-1] - g.index[0]).days / 365.25, 1 / 365.25)
    rows = []
    for c in g.columns:
        s = g[c].dropna()
        rows.append({"Option": c, "End value (₹)": round(s.iloc[-1]),
                     "Yearly return %": round(((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100, 1),
                     "Worst fall %": round(((s / s.cummax()) - 1).min() * 100, 1)})
    return pd.DataFrame(rows)


def tracking(etf: pd.Series, price: pd.Series, years=(1, 3, 5)) -> pd.DataFrame:
    rows = []
    end = min(etf.index[-1], price.index[-1])
    for y in years:
        start = end - pd.DateOffset(years=y)
        if start < max(etf.index[0], price.index[0]):
            continue
        e = (etf.asof(end) / etf.asof(start)) ** (1 / y) - 1
        p = (price.asof(end) / price.asof(start)) ** (1 / y) - 1
        rows.append({"Period": f"{y} years", "ETF % a year": round(e * 100, 2), "Gold at global parity % a year": round(p * 100, 2),
                     "Difference": round((e - p) * 100, 2)})
    return pd.DataFrame(rows)


def actual_series() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(HERE, "data", "sgb_series.csv"), parse_dates=["issue_date", "redeem_date"])
    rows = []
    for _, r in df.iterrows():
        flows = [(r["issue_date"], -r["issue_price"])]
        k = 1
        while r["issue_date"] + pd.DateOffset(months=6 * k) <= r["redeem_date"]:
            flows.append((r["issue_date"] + pd.DateOffset(months=6 * k), r["issue_price"] * SGB_RATE / 2))
            k += 1
        flows.append((r["redeem_date"], r["redeem_price"]))
        rows.append({"Series": r["series"], "Price gain %": round((r["redeem_price"] / r["issue_price"] - 1) * 100, 1),
                     "Yearly return incl. coupons %": round(xirr(flows) * 100, 1)})
    return pd.DataFrame(rows)


def render(st, ctx):
    price = inr_gold(ctx["daily"])
    st.write("The same money put into physical gold, a gold ETF, a Sovereign Gold Bond (modelled) and the Nifty 50.")
    a, b, c, d = st.columns(4)
    start = a.date_input("Start date", value=pd.Timestamp("2015-12-01"), min_value=price.index[0].date(),
                         max_value=price.index[-1].date())
    invest = b.number_input("Amount (₹)", value=100000, step=10000)
    making = c.number_input("Jewellery making charge %", value=8.0, step=1.0)
    etf_name = d.selectbox("Gold ETF", list(ETFS))
    etf, nifty = close(ETFS[etf_name]), close("^NSEI")
    if etf is None:
        st.info("Couldn't load the ETF price from Yahoo Finance just now, so it is left out.")
    g = growth(price, etf, nifty, start, invest, 3.0, making)
    if g is None:
        st.warning("Pick an earlier start date.")
        return
    fig = go.Figure([go.Scatter(x=g.index, y=g[col], name=col) for col in g.columns])
    fig.update_layout(title=f"Growth of ₹{invest:,.0f}", legend_orientation="h")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(summary(g), width="stretch", hide_index=True)
    st.caption("Gold prices here are global parity (international price times USD/INR), so they ignore Indian duty and "
               "premiums. Nifty excludes dividends. Everything is before tax.")

    st.subheader("Sovereign Gold Bond model")
    hold = st.radio("Hold for", [8, 5], format_func=lambda y: "8 years (maturity)" if y == 8 else "5 years (earliest exit)",
                    horizontal=True)
    issue = max(pd.Timestamp(start), pd.Timestamp("2015-11-30"))
    m = sgb_model(issue, hold, price, invest)
    note = "" if m["matured"] else " (not yet matured, valued at the latest price)"
    x1, x2, x3 = st.columns(3)
    x1.metric("Yearly return incl. coupons", f"{m['xirr'] * 100:.1f}%")
    x2.metric("Gold price gain", f"{m['price_return'] * 100:.0f}%")
    x3.metric("Coupons received", f"₹{m['coupons']:,.0f}")
    st.caption(f"Bought {issue:%b %Y}, valued {m['end']:%b %Y}{note}. SGBs started in November 2015, run 8 years with exit "
               "from year 5, and pay 2.5% a year in two instalments. No new tranche has been issued since February 2024.")

    st.subheader("Gold ETF versus gold itself")
    if etf is not None:
        t = tracking(etf, price)
        if len(t):
            st.dataframe(t, width="stretch", hide_index=True)
        st.caption("The gap covers the fund's yearly cost plus Indian price differences such as duty and premiums.")

    st.subheader("Actual SGB series")
    actual = actual_series()
    if len(actual):
        st.dataframe(actual, width="stretch", hide_index=True)
    else:
        st.caption("Add real series to data/sgb_series.csv from RBI redemption notices (columns: series, issue_date, "
                   "issue_price, redeem_date, redeem_price, per gram) and they appear here with their actual returns.")
