"""Idea 2: does the scorecard actually work? Turns the scorecard into a monthly score and
checks what rupee gold did in the following 1 and 3 months. No look-ahead: each month's
z-score uses only data available up to that month."""
import numpy as np
import pandas as pd
import plotly.express as px
import statsmodels.api as sm
import analysis as an

TITLE = "Does the scorecard work?"
US_ONLY = ["Real yields (10Y)", "US dollar (DXY)", "Inflation expectations", "US CPI inflation (YoY)"]


def signal_history(df, months=3, thresh=0.5, min_obs=36, cols=None):
    """+1 supportive, 0 neutral, -1 negative for each factor each month (NaN if not enough history)."""
    sig = pd.DataFrame(index=df.index)
    for name, (col, sign) in an.FACTORS.items():
        if col not in df or (cols is not None and name not in cols):
            continue
        chg = df[col].diff(months)
        z = chg / chg.expanding(min_obs).std()
        sig[name] = np.where(z.abs() < thresh, 0.0, np.sign(z) * sign)
        sig.loc[z.isna(), name] = np.nan
    return sig


def run(df, months=3, cols=None):
    sig = signal_history(df, months, cols=cols)
    score = sig.mean(axis=1)
    score = score[sig.notna().sum(axis=1) >= 3]
    px_inr = df["gold_inr_10g"]
    fwd = pd.DataFrame({"fwd_1m": px_inr.pct_change().shift(-1) * 100,
                        "fwd_3m": px_inr.pct_change(3).shift(-3) * 100}).reindex(score.index)
    d = pd.concat([score.rename("score"), fwd], axis=1).dropna()
    d["bucket"] = pd.cut(d["score"], [-1.01, -0.25, 0.25, 1.01],
                         labels=["Mostly negative", "Mixed", "Mostly supportive"])
    table = d.groupby("bucket", observed=False).agg(
        months=("score", "size"), avg_next_1m=("fwd_1m", "mean"), avg_next_3m=("fwd_3m", "mean"),
        share_up_3m=("fwd_3m", lambda x: (x > 0).mean() * 100)).round(1)
    model = sm.OLS(d["fwd_3m"], sm.add_constant(d["score"])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return {"table": table, "data": d, "model": model}


def render(st, ctx):
    df = ctx["df"]
    st.write("Each month the scorecard is turned into a single score (share of factors that were supportive "
             "minus negative). Then we check what rupee gold did over the next 3 months.")
    allf, us = run(df), run(df, cols=US_ONLY)
    st.dataframe(allf["table"], width="stretch")
    m = allf["model"]
    slope, p = m.params["score"], m.pvalues["score"]
    verdict = ("a statistically detectable link" if p < 0.05 else "no reliable link")
    st.metric("Extra 3-month return per +1.0 of score", f"{slope:+.1f}%", f"p-value {p:.2f}")
    st.info(f"In this data the scorecard shows {verdict} with future rupee gold returns "
            f"(sample: {int(m.nobs)} months, R² {m.rsquared:.2f}).")
    st.write(f"**Do India factors add anything?** R² using all factors: {allf['model'].rsquared:.3f}, "
             f"using US factors only: {us['model'].rsquared:.3f}.")
    st.plotly_chart(px.scatter(allf["data"], x="score", y="fwd_3m", trendline="ols",
                               labels={"score": "Scorecard score", "fwd_3m": "Next 3-month rupee gold return (%)"}),
                    width="stretch")
    st.caption("Caution: monthly windows overlap and the sample is small, so p-values are approximate. "
               "A weak result is still a finding; report it honestly.")
