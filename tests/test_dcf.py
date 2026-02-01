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

@pytest.mark.skip(reason="Requires internet access and live data")
def test_fetch_data():
    model = DCFModel("AAPL")
    model.fetch_data()
    assert model.financials is not None
    assert not model.financials.empty
