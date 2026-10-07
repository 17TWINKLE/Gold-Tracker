"""Data layer: pulls every driver of gold from free APIs (FRED + Yahoo Finance)."""
import os
import pandas as pd
import requests
import yfinance as yf

FRED_KEY = os.getenv("FRED_API_KEY")  # free key: https://fred.stlouisfed.org/docs/api/api_key.html
START = "2010-01-01"

FRED_SERIES = {
    "real_yield": "DFII10",    # 10Y US real yield
    "breakeven": "T10YIE",     # 10Y inflation expectations
    "cpi": "CPIAUCSL",         # US CPI index
    "payrolls": "PAYEMS",      # Non-farm payrolls
}
MARKET = {"gold": "GC=F", "dxy": "DX-Y.NYB", "usdinr": "INR=X"}
STOCKS = {"Muthoot Finance": "MUTHOOTFIN.NS", "Titan": "TITAN.NS", "Kalyan Jewellers": "KALYANKJIL.NS"}


def fred(series_id: str, start: str = START) -> pd.Series:
    r = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params=dict(series_id=series_id, api_key=FRED_KEY, file_type="json", observation_start=start),
        timeout=30,
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["observations"])
    s = pd.to_numeric(df["value"], errors="coerce")
    s.index = pd.to_datetime(df["date"])
    return s.dropna()


def market(ticker: str) -> pd.Series:
    s = yf.download(ticker, start=START, auto_adjust=True, progress=False)["Close"].squeeze()
    if getattr(s.index, "tz", None) is not None:  # Indian tickers can come back time-zone aware
        s.index = s.index.tz_localize(None)
    s.index = s.index.normalize()
    return s


def india_cpi() -> pd.Series:
    """India CPI index from FRED. This series can lag or be discontinued, so fail softly."""
    try:
        return fred("INDCPIALLMINMEI")
    except Exception:
        return pd.Series(dtype=float)


def manual(name: str, col: str) -> pd.Series:
    """Hand-maintained history (RBI repo rate, import duty). Add a row whenever a rate changes."""
    d = pd.read_csv(os.path.join(os.path.dirname(__file__), "data", name), parse_dates=["date"])
    return d.set_index("date")[col]


def build_monthly() -> pd.DataFrame:
    """One tidy monthly table with all drivers. Gold in USD/oz and INR/10g."""
    parts = {k: fred(v) for k, v in FRED_SERIES.items()}
    parts.update({k: market(v) for k, v in MARKET.items()})
    df = pd.DataFrame(parts).resample("ME").last().ffill()
    df["cpi_yoy"] = df["cpi"].pct_change(12) * 100
    df["payrolls_chg"] = df["payrolls"].diff()
    df["gold_inr_10g"] = df["gold"] / 31.1035 * 10 * df["usdinr"]
    # India layer
    df["repo"] = manual("repo_rate.csv", "repo_rate").reindex(df.index, method="ffill")
    df["duty"] = manual("import_duty.csv", "import_duty_pct").reindex(df.index, method="ffill")
    raw_cpi = india_cpi()
    if len(raw_cpi):
        cpi = raw_cpi.resample("ME").last()
        df["india_cpi_yoy"] = (cpi.pct_change(12, fill_method=None) * 100).reindex(df.index)
        df["india_real_rate"] = df["repo"] - df["india_cpi_yoy"]
    return df.dropna(subset=["gold", "real_yield", "dxy", "usdinr"])


def stock_prices() -> pd.DataFrame:
    return pd.DataFrame({k: market(v) for k, v in STOCKS.items()}).resample("ME").last().dropna()


def daily_prices() -> pd.DataFrame:
    """Daily gold (USD/oz) and USD/INR, used for event studies."""
    return pd.DataFrame({"gold": market(MARKET["gold"]), "usdinr": market(MARKET["usdinr"])}).dropna()
