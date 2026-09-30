"""Idea 4: event studies. How did gold and the rupee move in the week before and after key events?
Events live in data/events.csv, so you can add your own."""
import os
import pandas as pd
import plotly.express as px

TITLE = "Event studies"
PATH = os.path.join(os.path.dirname(__file__), "data", "events.csv")


def study(daily: pd.DataFrame, events: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    rows = []
    for _, e in events.iterrows():
        i = daily.index.searchsorted(pd.Timestamp(e["date"]))
        if i - window < 0 or i + window >= len(daily):
            continue
        a, b = daily.iloc[i - window], daily.iloc[i + window]
        g, f = (b["gold"] / a["gold"] - 1) * 100, (b["usdinr"] / a["usdinr"] - 1) * 100
        rows.append({"Date": pd.Timestamp(e["date"]).date(), "Event": e["event"], "Gold USD %": round(g, 1),
                     "Rupee %": round(f, 1), "Gold ₹ %": round(((1 + g / 100) * (1 + f / 100) - 1) * 100, 1)})
    return pd.DataFrame(rows)


def render(st, ctx):
    window = st.select_slider("Trading days before and after", [3, 5, 10, 20], value=5)
    res = study(ctx["daily"], pd.read_csv(PATH, parse_dates=["date"]), window)
    st.dataframe(res, width="stretch", hide_index=True)
    if len(res):
        st.plotly_chart(px.bar(res, x="Event", y=["Gold USD %", "Rupee %", "Gold ₹ %"], barmode="group"),
                        width="stretch")
    st.caption("Moves around an event are not proof the event caused them; other news lands at the same time. "
               "Verify the event dates and add your own in data/events.csv.")
