import os, sys
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import live

PRICES = {"GC=F": (2500.0, 2475.0), "INR=X": (84.0, 83.9), "DX-Y.NYB": (104.0, 104.5),
          "GOLDBEES.NS": (70.0, 69.5), "MUTHOOTFIN.NS": (2000.0, 1990.0), "TITAN.NS": (3500.0, 3490.0),
          "KALYANKJIL.NS": (500.0, 495.0)}


class FakeTicker:
    def __init__(self, t): self.t = t
    @property
    def fast_info(self):
        if self.t not in PRICES: raise RuntimeError("unknown ticker")
        return {"last_price": PRICES[self.t][0], "previous_close": PRICES[self.t][1]}


@pytest.fixture(autouse=True)
def patch(monkeypatch):
    monkeypatch.setattr(live.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(live.yf, "download", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(live.data, "fred",
                        lambda sid, start=None: pd.Series([4.1, 4.2], index=pd.to_datetime(["2026-11-04", "2026-11-05"])))
    monkeypatch.setenv("FRED_API_KEY", "x")
    st.cache_data.clear()


def test_fair_value_matches_hand_calculation():
    r = live.fair_value_live(2500, 84, 6, 3)
    assert round(r["global_in_inr"]) == 67517 and round(r["fair_value"]) == 73715


def test_quote_and_unknown_ticker():
    q = live.get_quote("GC=F")
    assert q["price"] == 2500.0 and round(live.chg(q), 2) == 1.01
    assert live.get_quote("NOPE.NS") is None  # fails softly, no crash


def test_fred_latest_without_key(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY")
    st.cache_data.clear()
    assert live.fred_latest("DGS10") is None
    monkeypatch.setenv("FRED_API_KEY", "x")
    st.cache_data.clear()
    val, date = live.fred_latest("DGS10")
    assert val == 4.2 and date == pd.Timestamp("2026-11-05")


def test_age_days():
    assert live.age_days(pd.Timestamp.today() - pd.Timedelta(days=10)) == 10


def run(script):
    at = AppTest.from_string(script, default_timeout=30).run()
    assert not at.exception
    return at


def test_tab_renders_with_live_and_missing_data():
    at = run("import streamlit as st, live\nlive.render(st, {})")
    labels = [m.label for m in at.metric]
    assert "Gold (USD/oz)" in labels
    assert any("Fair value" in l for l in labels)


def test_tab_survives_no_prices(monkeypatch):
    monkeypatch.setattr(live.yf, "Ticker", lambda t: (_ for _ in ()).throw(RuntimeError("down")))
    at = run("import streamlit as st, live\nlive.render(st, {})")
    assert any("not available" in i.value for i in at.info)
