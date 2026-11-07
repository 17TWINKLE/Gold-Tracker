"""Live tab: near-real-time gold, rupee, gold ETF, gold stocks, bond yields and policy rates.

Honest limits (also shown in the app):
- Yahoo Finance prices are usually delayed by about 15 minutes and refresh every 5 minutes here.
- There is no free official feed for the Indian city gold rate (MCX or jeweller quote), so you type it in
  and the app compares it with the live fair value. The gold ETF is shown as a live Indian market check.
- RBI repo rate and import duty have no free API. They come from data/*.csv and the app warns when they look old.
- SGB (Sovereign Gold Bond) prices: type the NSE symbol of the tranche you want to look up.
"""
import os
import pandas as pd
import streamlit as st
import yfinance as yf
import analysis as an
import data

TITLE = "Live prices"
GOLD, FX, DXY = "GC=F", "INR=X", "DX-Y.NYB"
ETF = "GOLDBEES.NS"  # Nippon India Gold BeES. Verify the ticker on Yahoo Finance before relying on it.
FRED_LIVE = {  # series id: (label, how often it updates)
    "DGS10": ("US 10-year yield", "daily"),
    "DFII10": ("US 10-year real yield", "daily"),
    "T10YIE": ("US 10-year inflation expectation", "daily"),
    "INDIRLTLT01STM": ("India 10-year government bond yield", "monthly, lags by weeks"),
}


def age_days(ts) -> int:
    return int((pd.Timestamp.today().normalize() - pd.Timestamp(ts).normalize()).days)


def fair_value_live(gold_usd: float, usdinr: float, duty_pct: float, gst_pct: float) -> dict:
    """Same maths as the Rupee bridge tab, fed with live inputs."""
    return an.rupee_bridge(gold_usd, usdinr, duty_pct, gst_pct, local_quote=0.0)


@st.cache_data(ttl=300)
def get_quote(ticker: str):
    """Latest price and previous close, or None if Yahoo has nothing for this ticker."""
    try:
        fi = yf.Ticker(ticker).fast_info
        last, prev = fi["last_price"], fi["previous_close"]
        if last is None or pd.isna(last):
            raise ValueError("no price")
        return {"price": float(last), "prev": float(prev) if prev else None}
    except Exception:
        try:
            s = yf.download(ticker, period="5d", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
            if not len(s):
                return None
            return {"price": float(s.iloc[-1]), "prev": float(s.iloc[-2]) if len(s) > 1 else None}
        except Exception:
            return None


@st.cache_data(ttl=3600)
def fred_latest(series_id: str):
    """(value, date) of the newest FRED observation, or None (no key, no internet, series gone)."""
    if not os.getenv("FRED_API_KEY"):
        return None
    try:
        start = (pd.Timestamp.today() - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        s = data.fred(series_id, start=start)
        return float(s.iloc[-1]), s.index[-1]
    except Exception:
        return None


def chg(q):
    return None if not q or not q["prev"] else (q["price"] / q["prev"] - 1) * 100


def metric(col, label, q, fmt="{:,.2f}"):
    if q is None:
        col.metric(label, "n/a")
    else:
        c = chg(q)
        col.metric(label, fmt.format(q["price"]), None if c is None else f"{c:+.2f}% vs last close")


def last_manual(name, col):
    s = data.manual(name, col).dropna()
    return float(s.iloc[-1]), s.index[-1]


def render(st_, ctx):
    st_.caption("Yahoo Finance prices are usually about 15 minutes delayed and refresh every 5 minutes. "
                "Indian market data only moves during Indian trading hours.")
    if st_.button("Refresh now"):
        get_quote.clear()
        fred_latest.clear()

    # 1. Global prices
    st_.subheader("Global gold, rupee and dollar")
    gold, fx, dxy = get_quote(GOLD), get_quote(FX), get_quote(DXY)
    a, b, c = st_.columns(3)
    metric(a, "Gold (USD/oz)", gold)
    metric(b, "USD/INR", fx)
    metric(c, "Dollar index", dxy)

    # 2. Live rupee bridge
    st_.subheader("Live fair value of gold in India")
    if gold is None or fx is None:
        st_.info("Live gold or USD/INR price is not available right now. Try Refresh in a minute.")
    else:
        duty, duty_date = last_manual("import_duty.csv", "import_duty_pct")
        d1, d2, d3 = st_.columns(3)
        duty = d1.number_input("Import duty %", value=duty, key="live_duty")
        gst = d2.number_input("GST %", value=3.0, key="live_gst")
        quote = d3.number_input("Indian quote ₹/10 g (optional)", value=0.0, step=100.0, key="live_quote")
        r = fair_value_live(gold["price"], fx["price"], duty, gst)
        k1, k2, k3 = st_.columns(3)
        k1.metric("Global price in ₹/10 g", f"{r['global_in_inr']:,.0f}")
        k2.metric("After import duty", f"{r['after_duty']:,.0f}")
        k3.metric("Fair value (after duty + GST)", f"{r['fair_value']:,.0f}")
        if quote > 0:
            prem = (quote / r["fair_value"] - 1) * 100
            st_.metric("Your quote vs fair value", f"{prem:+.1f}%")
        else:
            st_.caption("Type today's local rate above to see how far it sits above or below fair value.")
        st_.caption(f"Default duty is the latest row in data/import_duty.csv (dated {duty_date:%d %b %Y}). "
                    "Check it against the latest government notification.")
        if age_days(duty_date) > 365:
            st_.warning("The duty entry is over a year old. Confirm the current rate before relying on this.")

    # 3. Indian market check through the gold ETF
    st_.subheader("Indian market check: gold ETF")
    etf = get_quote(ETF)
    metric(st_, "Nippon India Gold BeES (₹ per unit)", etf)
    ce, cg, cf = chg(etf), chg(gold), chg(fx)
    if None not in (ce, cg, cf):
        rupee_gold = ((1 + cg / 100) * (1 + cf / 100) - 1) * 100
        st_.caption(f"Rupee gold at global parity moved {rupee_gold:+.2f}% vs last close, the ETF moved {ce:+.2f}%. "
                    "A big gap can just be different trading hours.")

    # 4. SGB lookup
    st_.subheader("Sovereign Gold Bond price")
    sym = st_.text_input("NSE symbol of an SGB tranche (you find it on NSE or your broker app)", value="",
                         key="live_sgb").strip().upper()
    if sym:
        q = get_quote(sym if sym.endswith(".NS") else sym + ".NS")
        if q is None:
            st_.info("No price found for that symbol. SGBs trade thinly and Yahoo may not list every tranche.")
        else:
            metric(st_, f"{sym} (₹ per unit)", q)

    # 5. Gold stocks
    st_.subheader("Gold-linked stocks")
    cols = st_.columns(len(data.STOCKS))
    for col, (name, tkr) in zip(cols, data.STOCKS.items()):
        metric(col, name, get_quote(tkr), "₹{:,.2f}")

    # 6. Rates
    st_.subheader("Interest rates and bond yields")
    if not os.getenv("FRED_API_KEY"):
        st_.info("Add your FRED key in Secrets to see US and India bond yields.")
    else:
        cols = st_.columns(len(FRED_LIVE))
        for col, (sid, (label, freq)) in zip(cols, FRED_LIVE.items()):
            res = fred_latest(sid)
            if res is None:
                col.metric(label, "n/a")
            else:
                col.metric(label, f"{res[0]:.2f}%", f"as of {res[1]:%d %b %Y} ({freq})", delta_color="off")
    repo, repo_date = last_manual("repo_rate.csv", "repo_rate")
    st_.metric("RBI repo rate (from data/repo_rate.csv)", f"{repo:.2f}%",
               f"last change recorded {repo_date:%d %b %Y}", delta_color="off")
    if age_days(repo_date) > 120:
        st_.warning("The last repo rate entry is over four months old. Check rbi.org.in and add a row to "
                    "data/repo_rate.csv if the rate has changed.")
