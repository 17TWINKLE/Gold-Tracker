"""Opens the whole dashboard headlessly and checks no tab crashes."""
import os
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def fresh_cache():
    st.cache_data.clear()  # otherwise one test's data leaks into the next
    yield


def test_app_runs_without_errors():
    os.environ.pop("FRED_API_KEY", None)
    at = AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=120).run()
    assert not at.exception


def _app():
    return AppTest.from_file(os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py"), default_timeout=120)


def test_live_path_with_faked_apis(monkeypatch):
    import test_data_mock as m, data
    monkeypatch.setattr(data.requests, "get", m.fake_get)
    monkeypatch.setattr(data.yf, "download", m.fake_download)
    monkeypatch.setenv("FRED_API_KEY", "fake")
    at = _app().run()
    assert not at.exception and not any("PRACTICE" in w.value for w in at.warning)  # live path, no practice banner


def test_live_path_without_india_cpi(monkeypatch):
    import test_data_mock as m, data
    monkeypatch.setattr(data.requests, "get", m.fake_get)
    monkeypatch.setattr(data.yf, "download", m.fake_download)
    monkeypatch.setenv("FRED_API_KEY", "fake")
    monkeypatch.setenv("FAKE_NO_INDIA_CPI", "1")
    at = _app().run()
    assert not at.exception


def test_falls_back_when_live_data_fails(monkeypatch):
    import data
    def boom(*a, **k): raise ConnectionError("no internet")
    monkeypatch.setattr(data.requests, "get", boom)
    monkeypatch.setenv("FRED_API_KEY", "fake")
    at = _app().run()
    assert not at.exception and any("PRACTICE" in w.value for w in at.warning)
