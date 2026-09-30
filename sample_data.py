"""Practice data (randomly generated, NOT real). Lets the app open without a FRED key
and lets the tests run offline. The app shows a warning banner whenever this is in use."""
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"


def _csv(name, col, idx):
    s = pd.read_csv(DATA / name, parse_dates=["date"]).set_index("date")[col]
    return s.reindex(idx, method="ffill")


def generate(seed: int = 7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2013-08-31", "2025-06-30", freq="ME")
    n = len(idx)
    real = 0.5 + np.cumsum(rng.normal(0, 0.12, n))
    dxy = 90 * np.exp(np.cumsum(rng.normal(0, 0.015, n)))
    be = 2 + 0.3 * np.cumsum(rng.normal(0, 0.05, n))
    usdinr = 60 * np.exp(np.cumsum(rng.normal(0.003, 0.012, n)))
    dlog = (-0.05 * np.diff(real, prepend=real[0]) - 0.3 * np.diff(np.log(dxy), prepend=np.log(dxy[0]))
            + 0.05 * np.diff(be, prepend=be[0]) + rng.normal(0.004, 0.03, n))
    gold = 1200 * np.exp(np.cumsum(dlog))
    df = pd.DataFrame({"gold": gold, "dxy": dxy, "usdinr": usdinr, "real_yield": real, "breakeven": be}, index=idx)
    df["cpi_yoy"] = 2.5 + 0.5 * np.cumsum(rng.normal(0, 0.15, n))
    df["payrolls_chg"] = rng.normal(150, 60, n)
    df["gold_inr_10g"] = df["gold"] / 31.1035 * 10 * df["usdinr"]
    df["repo"] = _csv("repo_rate.csv", "repo_rate", idx)
    df["duty"] = _csv("import_duty.csv", "import_duty_pct", idx)
    df["india_cpi_yoy"] = 4 + 0.4 * np.cumsum(rng.normal(0, 0.2, n))
    df["india_real_rate"] = df["repo"] - df["india_cpi_yoy"]

    g = df["gold_inr_10g"].pct_change().fillna(0).to_numpy()
    stocks = pd.DataFrame({name: 100 * np.cumprod(1 + b * g + rng.normal(0, 0.06, n))
                           for name, b in [("Muthoot Finance", 0.8), ("Titan", 0.5), ("Kalyan Jewellers", 0.9)]},
                          index=idx)
    d = pd.bdate_range("2013-08-01", "2025-06-30")
    m = len(d)
    daily = pd.DataFrame({"gold": 1200 * np.exp(np.cumsum(rng.normal(0.0002, 0.009, m))),
                          "usdinr": 60 * np.exp(np.cumsum(rng.normal(0.00015, 0.003, m)))}, index=d)
    return df, stocks, daily
