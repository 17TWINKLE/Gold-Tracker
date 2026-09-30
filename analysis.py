"""Analytics: regression, rolling correlations, rule-based scorecard, rupee bridge, stock betas."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

# +1: a rise supports gold, -1: a rise pressures gold
FACTORS = {
    "Real yields (10Y)": ("real_yield", -1),
    "US dollar (DXY)": ("dxy", -1),
    "Inflation expectations": ("breakeven", +1),
    "US CPI inflation (YoY)": ("cpi_yoy", +1),
    "USD/INR (weaker rupee)": ("usdinr", +1),
    "RBI repo rate": ("repo", -1),
    "India CPI inflation (YoY)": ("india_cpi_yoy", +1),
    "India real rate (repo minus CPI)": ("india_real_rate", -1),
}


def regression(df: pd.DataFrame):
    """Monthly gold return explained by change in real yield, dollar return, change in breakeven."""
    x = pd.DataFrame({
        "d_real_yield": df["real_yield"].diff(),
        "dxy_return": df["dxy"].pct_change(),
        "d_breakeven": df["breakeven"].diff(),
    })
    y = df["gold"].pct_change().rename("gold_return")
    d = pd.concat([y, x], axis=1).dropna()
    return sm.OLS(d["gold_return"], sm.add_constant(d.drop(columns="gold_return"))).fit()


def rolling_corr(df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    g = df["gold"].pct_change()
    return pd.DataFrame({
        "Real yield change": g.rolling(window).corr(df["real_yield"].diff()),
        "Dollar return": g.rolling(window).corr(df["dxy"].pct_change()),
        "USD/INR return": g.rolling(window).corr(df["usdinr"].pct_change()),
    }).dropna()


def scorecard(df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    """Signal = direction of the 3-month change, scaled by its own history (z-score).
    Neutral if the move is within half a standard deviation."""
    rows = []
    for name, (col, sign) in FACTORS.items():
        if col not in df or df[col].dropna().shape[0] < 24:
            continue  # India series missing or too short
        s = df[col].dropna()
        chg = s.diff(months)
        z = chg.iloc[-1] / chg.std()
        stale = (df.index[-1] - s.index[-1]).days > 150  # source stopped updating
        if stale:
            signal = "Stale data"
        elif np.isnan(z):
            signal = "No data"
        elif abs(z) < 0.5:
            signal = "Neutral"
        else:
            signal = "Supportive" if np.sign(z) == sign else "Negative"
        rows.append({"Factor": name, "Latest": round(s.iloc[-1], 2), f"{months}M change": round(chg.iloc[-1], 2),
                     "Z-score": round(z, 2), "Signal": signal, "As of": s.index[-1].strftime("%b %Y")})
    return pd.DataFrame(rows)


def rupee_bridge(gold_usd: float, usdinr: float, duty_pct: float, gst_pct: float, local_quote: float) -> dict:
    landed = gold_usd / 31.1035 * 10 * usdinr
    after_duty = landed * (1 + duty_pct / 100)
    fair = after_duty * (1 + gst_pct / 100)
    return {"global_in_inr": landed, "after_duty": after_duty, "fair_value": fair,
            "premium_pct": (local_quote / fair - 1) * 100}


def gold_beta(stocks: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    """Beta of each gold-linked stock to monthly INR gold returns."""
    g = df["gold_inr_10g"].pct_change().rename("gold")
    out = []
    for c in stocks.columns:
        d = pd.concat([stocks[c].pct_change(), g], axis=1).dropna()
        m = sm.OLS(d.iloc[:, 0], sm.add_constant(d["gold"])).fit()
        out.append({"Stock": c, "Beta to gold": round(m.params["gold"], 2), "R-squared": round(m.rsquared, 2)})
    return pd.DataFrame(out)


def decompose(df: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """Splits the rolling change in rupee gold into its three causes.
    Uses log changes, so the pieces add up exactly to the total (in log percentage points)."""
    d = df.dropna(subset=["duty"])
    out = pd.DataFrame({
        "Global gold (USD)": np.log(d["gold"] / d["gold"].shift(months)),
        "Rupee (USD/INR)": np.log(d["usdinr"] / d["usdinr"].shift(months)),
        "Import duty": np.log((1 + d["duty"] / 100) / (1 + d["duty"].shift(months) / 100)),
    }) * 100
    out["Total"] = out.sum(axis=1)
    return out.dropna()
