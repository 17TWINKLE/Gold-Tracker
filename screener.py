"""Screener-style company view for gold-linked stocks. Data: Yahoo Finance via yfinance
(Screener.in has no free public data feed, so numbers can differ slightly from it)."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

TITLE = "Company screener"

# Verify each ticker on Yahoo Finance / NSE before relying on it.
UNIVERSE = {
    "Muthoot Finance": "MUTHOOTFIN.NS",
    "Manappuram Finance": "MANAPPURAM.NS",
    "Titan": "TITAN.NS",
    "Kalyan Jewellers": "KALYANKJIL.NS",
    "Senco Gold": "SENCO.NS",
    "PN Gadgil Jewellers": "PNGJL.NS",
    "Thangamayil Jewellery": "THANGAMAYL.NS",
    "Goldiam International": "GOLDIAM.NS",
    "Tribhovandas Bhimji Zaveri": "TBZ.NS",
    "Sky Gold and Diamonds": "SKYGOLD.NS",
}
PERIODS = {"1M": 21, "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260, "Max": None}


def history(ticker: str):
    """Daily close and volume, or None if Yahoo returns nothing."""
    try:
        d = yf.download(ticker, period="max", auto_adjust=True, progress=False)
        out = pd.DataFrame({"Close": d["Close"].squeeze(), "Volume": d["Volume"].squeeze()}).dropna()
    except Exception:
        return None
    if out.empty:
        return None
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    out.index = out.index.normalize()
    return out


def _num(info, key, scale=1.0):
    v = info.get(key)
    return round(v * scale, 1) if isinstance(v, (int, float)) else None


def fundamentals(universe: dict) -> pd.DataFrame:
    rows = []
    for name, t in universe.items():
        try:
            info = yf.Ticker(t).info or {}
        except Exception:
            info = {}
        h = history(t)
        ret_1y = None
        if h is not None and len(h) > 252:
            ret_1y = round((h["Close"].iloc[-1] / h["Close"].iloc[-253] - 1) * 100, 1)
        rows.append({"Company": name, "Ticker": t,
                     "Market cap (₹ cr)": _num(info, "marketCap", 1e-7),
                     "PE": _num(info, "trailingPE"), "P/B": _num(info, "priceToBook"),
                     "ROE %": _num(info, "returnOnEquity", 100), "Net margin %": _num(info, "profitMargins", 100),
                     "Revenue growth %": _num(info, "revenueGrowth", 100), "1Y return %": ret_1y})
    return pd.DataFrame(rows)


def screen(df: pd.DataFrame, max_pe=None, min_roe=None, min_cap=None) -> pd.DataFrame:
    """Keeps companies passing every filter. Companies with missing data fail a filter that needs it."""
    out = df
    if max_pe is not None:
        out = out[out["PE"].le(max_pe)]
    if min_roe is not None:
        out = out[out["ROE %"].ge(min_roe)]
    if min_cap is not None:
        out = out[out["Market cap (₹ cr)"].ge(min_cap)]
    return out


def price_volume_chart(h: pd.DataFrame, title: str):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=h.index, y=h["Volume"], name="Volume", opacity=0.3), secondary_y=False)
    fig.add_trace(go.Scatter(x=h.index, y=h["Close"], name="Price (₹)"), secondary_y=True)
    fig.update_layout(title=title, legend_orientation="h")
    return fig


def vs_gold(h: pd.DataFrame, daily: pd.DataFrame):
    """Stock and rupee gold, both rebased to 100 at the start of the chosen window."""
    gold = (daily["gold"] * daily["usdinr"]).reindex(h.index, method="ffill").dropna()
    both = pd.DataFrame({"Stock": h["Close"], "Gold (₹)": gold}).dropna()
    if both.empty:
        return None
    return both / both.iloc[0] * 100


@st.cache_data(ttl=6 * 3600)
def _load_table():
    return fundamentals(UNIVERSE)


def render(st_, ctx):
    st_.write("A Screener-style view of gold-linked companies: key ratios, a screen with filters, "
              "and a price and volume chart compared with rupee gold.")
    table = _load_table()
    if table[["PE", "ROE %", "Market cap (₹ cr)"]].isna().all().all():
        st_.warning("Yahoo Finance returned no company data just now. Try again in a few minutes.")
    a, b, c = st_.columns(3)
    max_pe = a.number_input("Max PE (0 = ignore)", value=0.0, step=5.0)
    min_roe = b.number_input("Min ROE % (0 = ignore)", value=0.0, step=5.0)
    min_cap = c.number_input("Min market cap ₹ cr (0 = ignore)", value=0.0, step=1000.0)
    shown = screen(table, max_pe or None, min_roe or None, min_cap or None)
    st_.dataframe(shown, width="stretch", hide_index=True)
    st_.caption(f"{len(shown)} of {len(table)} companies pass. Ratios come from Yahoo Finance and can differ from "
                "Screener.in. Check any number you quote against the company's annual report.")

    name = st_.selectbox("Company chart", list(UNIVERSE))
    period = st_.radio("Period", list(PERIODS), index=2, horizontal=True)
    h = history(UNIVERSE[name])
    if h is None:
        st_.info("No price history available for this company right now.")
        return
    if PERIODS[period]:
        h = h.iloc[-PERIODS[period]:]
    st_.plotly_chart(price_volume_chart(h, f"{name}: price and volume"), width="stretch")
    cmp_ = vs_gold(h, ctx["daily"])
    if cmp_ is not None:
        fig = go.Figure([go.Scatter(x=cmp_.index, y=cmp_[c], name=c) for c in cmp_.columns])
        fig.update_layout(title="Stock vs rupee gold (start of period = 100)", legend_orientation="h")
        st_.plotly_chart(fig, width="stretch")
