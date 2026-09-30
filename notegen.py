"""Idea 6: drafts the monthly note from the tracker's own numbers. You edit it before using it."""
import analysis as an

TITLE = "Auto-drafted note"


def draft(df) -> str:
    sc = an.scorecard(df)
    counts = sc["Signal"].value_counts()
    s, n, b = (int(counts.get(k, 0)) for k in ("Supportive", "Neutral", "Negative"))
    dec = an.decompose(df, 12).iloc[-1]
    net = s - b
    bias = "supportive" if net >= 2 else "negative" if net <= -2 else "mixed"
    sc = sc[sc["Signal"].isin(["Supportive", "Neutral", "Negative"])]
    sc = sc.assign(strength=sc["Z-score"].abs())
    top_s = sc[sc["Signal"] == "Supportive"].sort_values("strength", ascending=False)
    top_n = sc[sc["Signal"] == "Negative"].sort_values("strength", ascending=False)
    lines = [
        f"Data as of {df.index[-1]:%B %Y}.",
        f"Gold in rupees moved {dec['Total']:+.1f}% over the last 12 months: {dec['Global gold (USD)']:+.1f} points "
        f"from global gold, {dec['Rupee (USD/INR)']:+.1f} from the rupee and {dec['Import duty']:+.1f} from import duty.",
        f"Of {s + n + b} factors with fresh data, {s} are supportive, {n} neutral and {b} negative, so the overall picture is {bias}.",
    ]
    if len(top_s):
        lines.append(f"Strongest supportive factor: {top_s.iloc[0]['Factor']}.")
    if len(top_n):
        lines.append(f"Strongest headwind: {top_n.iloc[0]['Factor']}.")
    if "india_real_rate" in df and df["india_real_rate"].notna().any():
        lines.append(f"India's real rate (repo minus CPI) is {df['india_real_rate'].dropna().iloc[-1]:.1f}%.")
    lines.append("Caveat: signals describe recent direction, not a forecast. Check the back-test tab for how "
                 "reliable the scorecard has been.")
    return "\n\n".join(lines)


def render(st, ctx):
    st.write("A first draft built from the numbers. Rewrite it in your own words and add your view.")
    st.text_area("Monthly note", value=draft(ctx["df"]), height=320)
