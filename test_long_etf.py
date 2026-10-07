import os, sys
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import etf_sgb, longrun, sample_data


# ---------- long history ----------
def fake_get(url, params=None, timeout=None):
    class R:
        def __init__(s, p): s.p = p
        def raise_for_status(s): pass
        def json(s): return s.p
    if "db.nomics" in url:
        idx = pd.date_range("1968-02-01", "2025-08-01", freq="MS")
        vals = list(np.linspace(35, 3400, len(idx)))
        vals[3] = "NA"
        return R({"series": {"docs": [{"period_start_day": [d.strftime("%Y-%m-%d") for d in idx], "value": vals}]}})
    idx = pd.date_range(params["observation_start"], "2025-08-01", freq="MS")
    base = {"EXINUS": (7, 88), "CPIAUCSL": (30, 320), "GS10": (3, 6)}[params["series_id"]]
    return R({"observations": [{"date": d.strftime("%Y-%m-%d"), "value": f"{v:.3f}"}
                               for d, v in zip(idx, np.linspace(*base, len(idx)))]})


def fake_download(t, period=None, auto_adjust=True, progress=False):
    idx = pd.bdate_range("1990-01-01" if t == "^GSPC" else "1997-07-01" if t == "^BSESN" else "2007-03-01", "2025-08-01")
    px = 100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0.0003, 0.01, len(idx))))
    return pd.DataFrame(px, index=idx, columns=pd.MultiIndex.from_product([["Close"], [t]]))


@pytest.fixture
def mocks(monkeypatch):
    monkeypatch.setattr(longrun.requests, "get", fake_get)
    monkeypatch.setattr(longrun.data.requests, "get", fake_get)
    monkeypatch.setattr(longrun.yf, "download", fake_download)
    monkeypatch.setattr(etf_sgb.yf, "download", fake_download)
    monkeypatch.setattr(longrun.data, "FRED_KEY", "fake")


def test_long_build_reaches_1968(mocks):
    df, src = longrun.build()
    assert df.index[0].year == 1968 and "DBnomics" in src
    assert df["gold_inr"].notna().sum() > 400 and df["real_yield_proxy"].notna().any()


def test_episode_table_blank_before_index_exists(mocks):
    df, _ = longrun.build()
    ep = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "episodes.csv"))
    t = longrun.episode_table(df, ep).set_index("Episode")
    assert pd.isna(t.loc["Long gold bear market", "Sensex %"])      # Sensex starts 1997
    assert t.loc["Global financial crisis", "Gold USD %"] == t.loc["Global financial crisis", "Gold USD %"]
    assert len(longrun.decade_corr(df)) >= 5


def test_falls_back_to_yahoo_when_dbnomics_down(mocks, monkeypatch):
    def boom(url, **k):
        if "db.nomics" in url: raise ConnectionError("down")
        return fake_get(url, **k)
    monkeypatch.setattr(longrun.requests, "get", boom)
    _, src = longrun.gold_usd_monthly()
    assert "Yahoo" in src


# ---------- ETF and SGB ----------
@pytest.fixture(scope="module")
def price():
    return etf_sgb.inr_gold(sample_data.generate()[2])


def test_xirr_known_value():
    flows = [(pd.Timestamp("2020-01-01"), -100.0), (pd.Timestamp("2021-01-01"), 110.0)]
    assert etf_sgb.xirr(flows) == pytest.approx(0.10, abs=0.002)


def test_sgb_model_adds_coupons(price):
    m = etf_sgb.sgb_model("2016-01-04", 5, price, 100000)
    assert m["coupons"] == pytest.approx(100000 * 0.025 * 5, rel=0.01)
    assert m["xirr"] > (1 + m["price_return"]) ** (1 / 5) - 1 - 1e-6   # coupons can only help versus price alone
    assert etf_sgb.sgb_model("2020-01-01", 8, price)["matured"] is False


def test_growth_and_summary(price):
    etf = price * 0.99
    g = etf_sgb.growth(price, etf, price * 0.5, "2016-01-01", 100000, 3, 8)
    assert g.shape[1] == 4
    first = g.iloc[0]
    assert first["Gold ETF"] == pytest.approx(100000) and first["Physical gold (after GST and making charge)"] < 100000
    s = etf_sgb.summary(g)
    assert (s["Worst fall %"] <= 0).all()


def test_tracking_difference_small_for_near_identical(price):
    t = etf_sgb.tracking(price * 0.99, price)
    assert len(t) == 3 and t["Difference"].abs().max() < 0.01


def test_actual_series_from_csv(tmp_path, monkeypatch):
    p = tmp_path / "data"; p.mkdir()
    (p / "sgb_series.csv").write_text("series,issue_date,issue_price,redeem_date,redeem_price\nTest,2018-01-01,3000,2026-01-01,12000\n")
    monkeypatch.setattr(etf_sgb, "HERE", str(tmp_path))
    out = etf_sgb.actual_series()
    assert out.iloc[0]["Price gain %"] == 300.0 and out.iloc[0]["Yearly return incl. coupons %"] > 20


def test_tabs_render_in_app(mocks, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "fake")
    import data, test_data_mock as m
    monkeypatch.setattr(data.requests, "get", lambda url, **k: fake_get(url, **k) if k["params"]["series_id"] in ("EXINUS", "CPIAUCSL", "GS10") else m.fake_get(url, **k))
    import streamlit as st
    st.cache_data.clear()
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=180).run()
    assert not at.exception
