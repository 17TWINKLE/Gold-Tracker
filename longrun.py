"""Long history: gold, rupee, inflation and yields back to the 1960s and 1970s, with crisis episodes.
Gold source order: your own data/gold_long_history.csv, then the DBnomics copy of the monthly LBMA series,
then Yahoo Finance gold futures (2000 onward only)."""
import os
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import yfinance as yf
import data

TITLE = "Long history"
HERE = os.path.dirname(__file__)
LONG_START = "1960-01-01"
DBNOMICS = "https://api.db.nomics.world/v22/series/LBMA/gold_M/gold_M_USD_PM_AVG?observations=1&format=json"


def _month_end(s: pd.Series) -> pd.Series:
    return s.resample("ME").last().dropna()


def gold_usd_monthly():
    """Returns (monthly gold in USD per oz, description of the source)."""
    path = os.path.join(HERE, "data", "gold_long_history.csv")
    if os.path.exists(path):
        d = pd.read_csv(path, parse_dates=["date"]).set_index("date")["gold_usd"]
        return _month_end(d), "your file data/gold_long_history.csv"
    try:
        r = requests.get(DBNOMICS, timeout=30)
        r.raise_for_status()
        doc = r.json()["series"]["docs"][0]
        vals = pd.to_numeric(pd.Series(doc["value"]), errors="coerce").to_numpy()
        s = pd.Series(vals, index=pd.to_datetime(doc["period_start_day"])).dropna()
        if len(s) > 100:
            return _month_end(s), "LBMA monthly average via DBnomics"
    except Exception:
        pass
    y = _yf_monthly("GC=F")
    return y, "Yahoo Finance gold futures (starts around 2000 only)"


def _yf_monthly(ticker: str) -> pd.Series:
    try:
        d = yf.download(ticker, period="max", auto_adjust=True, progress=False)["Close"].squeeze()
    except Exception:
        return pd.Series(dtype=float)
    if not len(d):
        return pd.Series(dtype=float)
    if getattr(d.index, "tz", None) is not None:
        d.index = d.index.tz_localize(None)
    return _month_end(d)


def build():
    gold, src = gold_usd_monthly()
    df = pd.concat({
        "gold_usd": gold,
        "usdinr": _month_end(data.fred("EXINUS", LONG_START)),
        "cpi": _month_end(data.fred("CPIAUCSL", LONG_START)),
        "gs10": _month_end(data.fred("GS10", LONG_START)),
        "spx": _yf_monthly("^GSPC"),
        "sensex": _yf_monthly("^BSESN"),
    }, axis=1, sort=True)
    df = df[df["gold_usd"].notna()].copy()
    df["gold_inr"] = df["gold_usd"] * df["usdinr"]
    df["cpi_yoy"] = df["cpi"].pct_change(12, fill_method=None) * 100
    df["real_gold"] = df["gold_usd"] * df["cpi"].dropna().iloc[-1] / df["cpi"]
    df["real_yield_proxy"] = df["gs10"] - df["cpi_yoy"]  # before 2003 there is no TIPS data, so this is an estimate
    return df, src


def _ret(s: pd.Series, a, b):
    s = s.dropna()
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    if s.empty or a < s.index[0] or b > s.index[-1]:
        return np.nan
    return round((s.asof(b) / s.asof(a) - 1) * 100, 1)


def episode_table(df: pd.DataFrame, episodes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, e in episodes.iterrows():
        rows.append({"Episode": e["name"], "From": e["start"][:7], "To": e["end"][:7],
                     "Gold USD %": _ret(df["gold_usd"], e["start"], e["end"]),
                     "Gold ₹ %": _ret(df["gold_inr"], e["start"], e["end"]),
                     "S&P 500 %": _ret(df["spx"], e["start"], e["end"]),
                     "Sensex %": _ret(df["sensex"], e["start"], e["end"])})
    return pd.DataFrame(rows)


def decade_corr(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.concat([df["gold_usd"].pct_change(), df["real_yield_proxy"].diff()], axis=1, keys=["g", "dy"]).dropna()
    out = {f"{k}s": round(g["g"].corr(g["dy"]), 2) for k, g in d.groupby(d.index.year // 10 * 10)}
    return pd.DataFrame({"Correlation of gold with change in real yield": out})


@st.cache_data(ttl=24 * 3600)
def _cached_build():
    return build()


def render(st_, ctx):
    if not os.getenv("FRED_API_KEY"):
        st_.info("Long history needs your FRED key (rupee, inflation and yield data). Add it in Secrets and reload.")
        return
    try:
        df, src = _cached_build()
    except Exception as e:
        st_.error(f"Couldn't load long history ({type(e).__name__}). Try again later.")
        return
    st_.write(f"Gold data from {df.index[0]:%b %Y} to {df.index[-1]:%b %Y}. Source: {src}.")
    if "Yahoo" in src:
        st_.warning("Only about 25 years of gold prices loaded. For the 1970s, 1980s and 1990s, download the monthly "
                    "gold series from the World Bank Pink Sheet and save it as data/gold_long_history.csv "
                    "with columns date and gold_usd.")
    episodes = pd.read_csv(os.path.join(HERE, "data", "episodes.csv"))
    view = st_.radio("Show", ["Gold in USD", "Gold in ₹ (estimate)", "Inflation-adjusted gold"], horizontal=True)
    col = {"Gold in USD": "gold_usd", "Gold in ₹ (estimate)": "gold_inr", "Inflation-adjusted gold": "real_gold"}[view]
    fig = px.line(df, y=col, log_y=True, labels={col: view, "index": ""})
    for _, e in episodes.iterrows():
        if pd.Timestamp(e["end"]) > df.index[0]:
            fig.add_vrect(x0=e["start"], x1=e["end"], opacity=0.12, line_width=0)
    st_.plotly_chart(fig, width="stretch")
    st_.caption("Shaded bands are the episodes in the table below. Log scale, so equal steps are equal percentage moves. "
                "Rupee gold before the 2000s is gold times the average USD/INR rate and ignores import duty and local premiums.")
    st_.subheader("Did gold protect in past crises?")
    st_.dataframe(episode_table(df, episodes), width="stretch", hide_index=True)
    st_.caption("Blank means the index didn't exist yet. Episode dates are approximate and editable in data/episodes.csv.")
    st_.subheader("Did gold's link to real yields hold over the decades?")
    st_.dataframe(decade_corr(df), width="stretch")
    st_.caption("Real yield before 2003 is estimated as the 10-year Treasury yield minus current US inflation, "
                "because inflation-linked bonds didn't exist yet. A negative number means gold rose when real yields fell.")
