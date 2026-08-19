# Modern Automated DCF

[![Tests](https://github.com/gilhermanns/modern-automated-dcf/actions/workflows/tests.yml/badge.svg)](https://github.com/gilhermanns/modern-automated-dcf/actions/workflows/tests.yml)

A Python framework for **Discounted Cash Flow scenario analysis**. It retrieves historical financial data, applies an explicit WACC and terminal-value framework, and produces sensitivity tables and charts for analyst review. The model is a research tool: a DCF output is conditional on its data, forecast and discount-rate assumptions.

## What it covers

| Component | Purpose |
|---|---|
| Data retrieval | Retrieves historical financial statement data through `yfinance` for a selected ticker. |
| DCF mechanics | Connects projected cash flows, discount rates and terminal value to an enterprise- and equity-value estimate. |
| Sensitivity analysis | Shows how intrinsic-value outputs move across growth and discount-rate assumptions. |
| Reporting | Produces projection and sensitivity charts for review and further modelling. |

## Example use

```python
from automated_dcf.dcf import DCFModel

model = DCFModel("AAPL")
result = model.run_dcf(growth_rate=0.05, perpetual_growth=0.02)

print(result["intrinsic_value"])
```

The result is an assumption-dependent analytical output, not a price target or an investment recommendation. No illustrative valuation or upside figure is presented here because such values change with the data retrieval date and model inputs.

## Installation and run

```bash
git clone https://github.com/gilhermanns/modern-automated-dcf.git
cd modern-automated-dcf
python -m pip install -r requirements.txt
python -m pytest -q
```

## Validation

The test suite checks metric fallback behaviour, the sensitivity-grid interface, restoration of the base case after sensitivity analysis, and creation of projection and sensitivity chart files. A separate live-data test is intentionally skipped because it depends on an external market-data connection.

## Limitations

- Public market-data fields can be incomplete, restated or unavailable.
- WACC, forecast growth and terminal growth are assumptions that require analyst judgement.
- The framework does not replace a full company model, financial-statement review or investment-committee process.

---

*Entwickelt mit Unterstützung von Claude Code (Anthropic).*
*For research and educational purposes; not investment advice.*
