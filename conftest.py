import pytest
import yfinance as yf


class _NoNetworkTicker:
    def __init__(self, *a, **k): pass
    info = {}


@pytest.fixture(autouse=True)
def no_real_yahoo_calls(monkeypatch):
    """Tests must never hit the real internet. Individual tests can override this."""
    monkeypatch.setattr(yf, "Ticker", _NoNetworkTicker)
