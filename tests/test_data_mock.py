"""Tests the live-data code path by faking what FRED (requests) and Yahoo Finance (yfinance) return,
including awkward real-world details: '.' placeholders in FRED, multi-level columns and
time-zone-aware dates from yfinance."""
import os, sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import data


class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


def fake_get(url, params=None, timeout=None):
    sid = params["series_id"]
    if sid == "INDCPIALLMINMEI" and os.environ.get("FAKE_NO_INDIA_CPI"):
        raise RuntimeError("series discontinued")
    freq = "B" if sid in ("DFII10", "T10YIE") else "MS"
    idx = pd.date_range("2010-01-01", "2025-06-30", freq=freq)
    vals = np.linspace(100, 300, len(idx)) if sid in ("CPIAUCSL", "PAYEMS", "INDCPIALLMINMEI") else np.linspace(0.5, 2, len(idx))
    obs = [{"date": d.strftime("%Y-%m-%d"), "value": f"{v:.3f}"} for d, v in zip(idx, vals)]
    obs[5]["value"] = "."  # FRED uses '.' for missing values
    return FakeResp({"observations": obs})


def fake_download(ticker, start=None, auto_adjust=True, progress=False):
    idx = pd.bdate_range("2010-01-04", "2025-06-30")
    if ticker.endswith(".NS"):
        idx = idx.tz_localize("Asia/Kolkata")  # yfinance can return tz-aware dates for Indian tickers
    base = 1500 if ticker == "GC=F" else 60 if ticker == "INR=X" else 100
    px = base * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.005, len(idx))))
    cols = pd.MultiIndex.from_product([["Close", "Open"], [ticker]])
    return pd.DataFrame(np.column_stack([px, px]), index=idx, columns=cols)


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(data.requests, "get", fake_get)
    monkeypatch.setattr(data.yf, "download", fake_download)
    monkeypatch.setattr(data, "FRED_KEY", "fake")


def test_monthly_frame_complete():
    df = data.build_monthly()
    for c in ["gold", "dxy", "usdinr", "real_yield", "breakeven", "cpi_yoy", "payrolls_chg",
              "gold_inr_10g", "repo", "duty", "india_cpi_yoy", "india_real_rate"]:
        assert c in df and df[c].notna().any(), c
    assert df.index.tz is None


def test_stocks_and_daily_align():
    s, d = data.stock_prices(), data.daily_prices()
    assert len(s) > 100 and s.index.tz is None and len(d) > 1000


def test_works_without_india_cpi(monkeypatch):
    monkeypatch.setenv("FAKE_NO_INDIA_CPI", "1")
    import analysis as an
    df = data.build_monthly()
    assert "india_cpi_yoy" not in df
    assert len(an.scorecard(df)) >= 5           # scorecard still works
    assert len(an.decompose(df)) > 0
