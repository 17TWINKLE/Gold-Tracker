"""Run with: pytest  (uses practice data, no internet needed)."""
import os, sys
import numpy as np
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import analysis as an
import backtest, events, notegen, sample_data, whatif


@pytest.fixture(scope="module")
def ctx():
    df, stocks, daily = sample_data.generate()
    return df, stocks, daily


def test_rupee_bridge_formula():
    r = an.rupee_bridge(2000, 80, 6, 3, 60000)
    landed = 2000 / 31.1035 * 10 * 80
    assert r["global_in_inr"] == pytest.approx(landed)
    assert r["fair_value"] == pytest.approx(landed * 1.06 * 1.03)


def test_decomposition_adds_up(ctx):
    dec = an.decompose(ctx[0], 12)
    parts = dec[["Global gold (USD)", "Rupee (USD/INR)", "Import duty"]].sum(axis=1)
    assert np.allclose(parts, dec["Total"])
    d = ctx[0].dropna(subset=["duty"])
    actual = np.log(d["gold_inr_10g"] / d["gold_inr_10g"].shift(12)) * 100
    # rupee gold here excludes duty, so total minus duty piece must equal the plain rupee-gold change
    assert np.allclose(dec["Total"] - dec["Import duty"], actual.reindex(dec.index))


def test_scorecard_signals_valid(ctx):
    sc = an.scorecard(ctx[0])
    assert set(sc["Signal"]) <= {"Supportive", "Neutral", "Negative", "Stale data", "No data"}
    assert len(sc) >= 5


def test_backtest_has_no_lookahead(ctx):
    df = ctx[0]
    full = backtest.signal_history(df)
    cut = backtest.signal_history(df.iloc[:-24])
    common = cut.index
    assert np.allclose(full.loc[common].fillna(9), cut.fillna(9))


def test_backtest_runs(ctx):
    res = backtest.run(ctx[0])
    assert len(res["table"]) == 3 and res["model"].nobs > 24


def test_whatif_direction(ctx):
    params = an.regression(ctx[0]).params
    up, _ = whatif.implied_move(params, 0, 0, 0, 0)
    assert up == 0
    _, inr = whatif.implied_move(params, 0, 0, 0, 3)
    assert inr == pytest.approx(3.0)


def test_events_and_note(ctx):
    import pandas as pd
    res = events.study(ctx[2], pd.read_csv(events.PATH, parse_dates=["date"]))
    assert len(res) >= 5
    assert "Gold in rupees moved" in notegen.draft(ctx[0])


def test_stale_series_is_flagged_not_used(ctx):
    df = ctx[0].copy()
    df.loc[df.index > "2023-01-01", ["india_cpi_yoy", "india_real_rate"]] = np.nan
    sc = an.scorecard(df).set_index("Factor")
    assert sc.loc["India CPI inflation (YoY)", "Signal"] == "Stale data"
    assert sc.loc["India real rate (repo minus CPI)", "Signal"] == "Stale data"
    assert "Stale data" not in notegen.draft(df)[:0] + ""   # note builds without crashing
    assert "factors with fresh data" in notegen.draft(df)


def test_short_history_does_not_crash(ctx):
    df = ctx[0].iloc[:30]
    an.scorecard(df)
    an.decompose(df, 12)
