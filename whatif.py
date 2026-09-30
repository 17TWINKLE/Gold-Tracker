"""Idea 3: what-if sliders. Uses the fitted regression to show the model-implied move in gold."""
import analysis as an

TITLE = "What-if scenarios"


def implied_move(params, d_real, dxy_pct, d_be, fx_pct):
    gold_usd = params["d_real_yield"] * d_real + params["dxy_return"] * dxy_pct / 100 + params["d_breakeven"] * d_be
    inr = (1 + gold_usd) * (1 + fx_pct / 100) - 1
    return gold_usd * 100, inr * 100


def render(st, ctx):
    model = an.regression(ctx["df"])
    st.write("Move the sliders to imagine a month where these factors change. The model estimates what "
             "gold would do, based on how it reacted historically.")
    a, b = st.columns(2)
    d_real = a.slider("Change in 10Y real yield (points)", -1.0, 1.0, 0.0, 0.05)
    dxy = b.slider("Dollar index move (%)", -5.0, 5.0, 0.0, 0.25)
    d_be = a.slider("Change in inflation expectations (points)", -1.0, 1.0, 0.0, 0.05)
    fx = b.slider("Rupee move vs USD (% weaker = positive)", -5.0, 5.0, 0.0, 0.25)
    usd, inr = implied_move(model.params, d_real, dxy, d_be, fx)
    c1, c2 = st.columns(2)
    c1.metric("Implied gold move (USD)", f"{usd:+.1f}%")
    c2.metric("Implied gold move (₹)", f"{inr:+.1f}%")
    st.caption(f"Based on monthly data (R² {model.rsquared:.2f}). The model explains only part of gold's moves, "
               "so treat this as a rough guide, not a forecast.")
