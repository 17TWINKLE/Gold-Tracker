"""Idea 5: gold-linked stocks in more depth: rolling sensitivity to gold and 12-month performance."""
import pandas as pd
import plotly.express as px
import analysis as an

TITLE = "Gold stocks deep dive"


def rolling_beta(stocks: pd.DataFrame, df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    g = df["gold_inr_10g"].pct_change()
    out = {}
    for c in stocks.columns:
        r = stocks[c].pct_change()
        out[c] = r.rolling(window).cov(g) / g.rolling(window).var()
    return pd.DataFrame(out).dropna(how="all")


def render(st, ctx):
    df, stocks = ctx["df"], ctx["stocks"]
    st.write("How much does each stock move when rupee gold moves, and is that sensitivity stable?")
    st.dataframe(an.gold_beta(stocks, df), width="stretch", hide_index=True)
    st.plotly_chart(px.line(rolling_beta(stocks, df), title="24-month rolling beta to rupee gold"),
                    width="stretch")
    perf = pd.concat([(stocks.iloc[-1] / stocks.iloc[-13] - 1) * 100,
                      pd.Series({"Gold (₹)": (df["gold_inr_10g"].iloc[-1] / df["gold_inr_10g"].iloc[-13] - 1) * 100})])
    st.dataframe(perf.round(1).rename("12-month return %").to_frame(), width="stretch")
    st.caption("Next step for you: add quarterly profit numbers from company results and compare them with gold.")
