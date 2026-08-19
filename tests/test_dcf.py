import pytest
from automated_dcf.dcf import DCFModel
import pandas as pd

def test_model_init():
    model = DCFModel("AAPL")
    assert model.ticker_symbol == "AAPL"

def test_get_metric():
    model = DCFModel("AAPL")
    df = pd.DataFrame({'Value': [100, 200]}, index=['Metric A', 'Metric B'])
    
    # Test exact match
    res = model.get_metric(df, ['Metric A'])
    assert res.iloc[0] == 100
    
    # Test fallback
    res = model.get_metric(df, ['NonExistent', 'Metric B'])
    assert res.iloc[0] == 200
    
    # Test default
    res = model.get_metric(df, ['None'], default=0.0)
    assert res.iloc[0] == 0.0


def test_sensitivity_analysis_returns_grid_and_restores_base_case(monkeypatch):
    model = DCFModel("AAPL")
    model.results = {"intrinsic_value": 100.0, "perpetual_growth": 0.02}

    def fake_run_dcf(*, years=10, growth_rate=0.05, discount_rate=None, perpetual_growth=0.02):
        value = (growth_rate * 1_000) - ((discount_rate or 0.08) * 500)
        model.results = {"intrinsic_value": value, "perpetual_growth": perpetual_growth}
        return model.results

    monkeypatch.setattr(model, "run_dcf", fake_run_dcf)

    table = model.sensitivity_analysis([0.02, 0.04], [0.08, 0.10])

    assert table.shape == (2, 2)
    assert table.loc[0.04, 0.08] == 0.0
    assert model.results == {"intrinsic_value": 100.0, "perpetual_growth": 0.02}

@pytest.mark.skip(reason="Requires internet access and live data")
def test_fetch_data():
    model = DCFModel("AAPL")
    model.fetch_data()
    assert model.financials is not None
    assert not model.financials.empty
