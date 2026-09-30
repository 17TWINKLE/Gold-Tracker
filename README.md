# Gold Tracker: Indian Investor View

A data-driven dashboard that explains **why gold moves** and what it means for an Indian investor, using three layers:
**global gold price → USD/INR → Indian market factors (duty, GST, premium).**

## What it does
- **Live data** from FRED (real yields, inflation expectations, CPI, payrolls) and Yahoo Finance (gold, dollar index, USD/INR, gold-linked stocks).
- **Auto scorecard:** each factor is labelled Supportive / Neutral / Negative using its 3-month change scaled by historical volatility (z-score).
- **Regression + rolling correlations:** tests how much of gold's monthly return real yields, the dollar and inflation expectations explain, and how stable that relationship is.
- **Rupee price bridge:** global price → ₹/10 g → after import duty and GST → premium/discount to the local quote.
- **India layer:** RBI repo rate, India CPI inflation and the India real rate (repo minus CPI) feed the scorecard.
- **Return split:** rupee gold change broken into global gold, rupee movement and import duty.
- **Gold stock betas:** Muthoot Finance, Titan, Kalyan Jewellers vs rupee gold returns.

## Optional modules (each adds a tab)
| File | What it shows |
|---|---|
| `backtest.py` | Turns the scorecard into a monthly score and tests it against future rupee gold returns, with US-only vs US+India comparison |
| `whatif.py` | Sliders for real yields, dollar, inflation expectations and rupee; shows the model-implied gold move |
| `events.py` | Gold and rupee moves around key events (Fed decisions, duty changes); events editable in `data/events.csv` |
| `stocks.py` | Rolling sensitivity of Muthoot, Titan and Kalyan to gold |
| `notegen.py` | Drafts the monthly note from the tracker's own numbers |

Without a FRED key the app opens with randomly generated practice data and a warning banner. Tests: `pytest` (16 checks, no internet needed). Factors whose source stopped updating are labelled "Stale data" instead of being used.

## Run it
```bash
pip install -r requirements.txt
export FRED_API_KEY=your_free_key
streamlit run app.py
```

## Method notes and limitations
- Monthly data; a regression shows association, not causation.
- Import duty and GST defaults must be checked against current CBIC / Ministry of Finance notifications.
- Repo rate and import duty history are hand-maintained in `data/*.csv` (last repo entry: June 2025). Add a row whenever a rate changes.
- India CPI comes from FRED and can lag; if missing, the India inflation rows are skipped.
- Central bank buying, ETF flows and Indian premiums (World Gold Council) have no free API; add them manually.

## Credit
Factor framework inspired by The Valuation School's gold price tracking checklist. Data and analysis are my own.
