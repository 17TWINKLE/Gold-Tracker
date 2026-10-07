# Handover guide: what each file is and where it goes

Keep this exact folder layout. Tomorrow, just tell me a file name from the tables below.

```
gold-tracker-india/
├── app.py               main dashboard (start here)
├── data.py              fetches live data
├── analysis.py          maths: scorecard, regression, return split
├── sample_data.py       practice data (runs without internet or a key)
├── backtest.py          [optional tab] does the scorecard work?
├── whatif.py            [optional tab] what-if sliders
├── events.py            [optional tab] event studies
├── stocks.py            [optional tab] gold stocks deep dive
├── screener.py          [optional tab] Screener-style company view
├── longrun.py           [optional tab] long history and crisis episodes
├── etf_sgb.py           [optional tab] gold ETF, SGB and physical gold compared
├── notegen.py           [optional tab] auto-drafted monthly note
├── requirements.txt     list of tools to install
├── README.md            front page for GitHub
├── DEPLOY.md            steps to make the live link
├── HANDOVER.md          this file
├── .gitignore           tells GitHub what to skip
├── data/
│   ├── repo_rate.csv    RBI repo rate history (you update)
│   ├── import_duty.csv  gold import duty history (you update)
│   ├── events.csv       events for the event study (you can add rows)
│   ├── episodes.csv     crisis episodes for the long history tab (editable)
│   ├── sgb_series.csv   real SGB series you add from RBI notices (starts empty)
│   └── gold_long_history.csv  OPTIONAL: your download of monthly gold since 1960 (columns: date, gold_usd)
├── tests/
│   ├── test_analysis.py checks the maths is right
│   ├── test_app.py      checks the dashboard opens (practice, live and failure cases)
│   ├── test_data_mock.py checks the live-data code using faked FRED / Yahoo replies
│   ├── test_screener.py checks the company screener
│   └── conftest.py      stops tests touching the real internet
└── docs/
    └── FINDINGS_TEMPLATE.md  where you write your results
```

## Adding pieces one at a time
The eight `[optional tab]` files each add one tab. Delete one and its tab disappears; add it back and the tab returns. Nothing else needs editing.

## Order I suggest
1. Run with practice data first (no key needed) to see everything open.
2. Add the FRED key to switch to live data. The yellow "PRACTICE data" banner disappears.
3. Fill in `docs/FINDINGS_TEMPLATE.md` from the real results.
4. Follow `DEPLOY.md` for the live link.

## Things only you can do
- Update `data/repo_rate.csv` (last entry June 2025) and confirm `data/import_duty.csv`.
- Confirm the dates in `data/events.csv`.
- Write your own conclusions. Recruiters will ask about them.
