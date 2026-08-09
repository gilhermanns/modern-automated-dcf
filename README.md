# Modern Automated DCF

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A professional-grade Discounted Cash Flow (DCF) modeling framework. This tool automates the extraction of financial data and provides a robust, rule-based valuation analysis.

## Core Features
- **Automated Data Ingestion**: Fetches historical financials directly via `yfinance`.
- **WACC Calculation**: Rule-based CAPM implementation for cost of equity and debt.
- **Sensitivity Analysis**: Evaluates intrinsic value across various growth and discount rate scenarios.
- **Professional Reporting**: Exports formatted Excel models for further analysis.

## Worked Example: Apple Inc. (AAPL)

Below is a demonstration of how the model processes a real-world company.

```python
from automated_dcf.dcf import DCFModel

# Initialize model for Apple
model = DCFModel("AAPL")

# Run valuation with 5% growth and 2% terminal growth
results = model.run_dcf(growth_rate=0.05, perpetual_growth=0.02)

print(f"Intrinsic Value: ${results['intrinsic_value']:.2f}")
print(f"Current Price: ${results['current_price']:.2f}")
print(f"Upside: {results['upside']*100:.1f}%")
```

### Model Output (Illustrative)
| Metric | Value |
| :--- | :--- |
| **Enterprise Value** | $2.85 Trillion |
| **Equity Value** | $2.91 Trillion |
| **WACC** | 8.2% |
| **Implied Upside** | +12.4% |

## Technical Architecture
The model follows a modular structure, separating data ingestion, financial logic, and reporting layers. It adheres to PEP 8 standards and avoids hard-coded "magic numbers" by using configurable financial constants.

## Installation
```bash
pip install -r requirements.txt
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Entwickelt mit Unterstützung von Claude Code (Anthropic).*
