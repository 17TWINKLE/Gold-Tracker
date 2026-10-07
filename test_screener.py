import os, sys
import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import screener


class FakeTicker:
    def __init__(self, t): self.t = t
    @property
    def info(self):
        if self.t.startswith("BAD"): raise RuntimeError("rate limited")
        return {"marketCap": 5e11, "trailingPE": 22.5, "priceToBook": 3.1, "returnOnEquity": 0.18,
                "profitMargins": 0.11, "revenueGrowth": 0.2}


def fake_download(t, period=None, auto_adjust=True, progress=False):
    idx = pd.bdate_range("2015-01-01", "2025-06-30").tz_localize("Asia/Kolkata")
    px = 100 * np.exp(np.cumsum(np.random.default_rng(3).normal(0, 0.01, len(idx))))
    cols = pd.MultiIndex.from_product([["Close", "Volume"], [t]])
    return pd.DataFrame(np.column_stack([px, np.full(len(idx), 1e5)]), index=idx, columns=cols)


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(screener.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(screener.yf, "download", fake_download)
    st.cache_data.clear()


def test_table_units_and_failures():
    df = screener.fundamentals({"Good": "GOOD.NS", "Bad": "BAD.NS"})
    good = df[df.Company == "Good"].iloc[0]
    assert good["Market cap (₹ cr)"] == 50000.0 and good["ROE %"] == 18.0 and good["1Y return %"] is not None
    assert len(df) == 2  # a failing ticker does not break the table


def test_screen_filters():
    df = pd.DataFrame({"Company": ["A", "B", "C"], "PE": [10, 30, None], "ROE %": [20, 5, 25],
                       "Market cap (₹ cr)": [1000, 50000, 200]})
    assert list(screener.screen(df, max_pe=20)["Company"]) == ["A"]
    assert list(screener.screen(df, min_roe=15)["Company"]) == ["A", "C"]
    assert list(screener.screen(df, max_pe=40, min_cap=500)["Company"]) == ["A", "B"]


def test_history_survives_empty_download(monkeypatch):
    monkeypatch.setattr(screener.yf, "download", lambda *a, **k: pd.DataFrame())
    assert screener.history("X.NS") is None


def test_tab_renders_in_app():
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=120)
    os.environ.pop("FRED_API_KEY", None)
    at.run()
    assert not at.exception
