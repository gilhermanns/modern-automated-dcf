import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import os
import matplotlib.pyplot as plt
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# Constants for financial defaults to avoid "Magic Numbers"
DEFAULT_RISK_FREE_RATE = 0.04  # 4% proxy for 10Y Treasury
DEFAULT_MARKET_RETURN = 0.10   # 10% historical S&P 500 average
DEFAULT_TAX_RATE = 0.21        # 21% standard corporate tax rate
DEFAULT_WACC = 0.08            # 8% fallback WACC
DEFAULT_BETA = 1.0             # Market beta fallback
MAX_TAX_RATE = 0.5             # Sanity check upper bound for tax rate

class DCFModel:
    """
    A professional-grade Discounted Cash Flow (DCF) model.
    Focuses on rule-based financial logic and robust data handling.
    """
    def __init__(self, ticker: str):
        if not ticker or not isinstance(ticker, str):
            raise ValueError("A valid ticker symbol string must be provided.")
        self.ticker_symbol = ticker.upper()
        self.ticker = yf.Ticker(self.ticker_symbol)
        self.financials = None
        self.balance_sheet = None
        self.cash_flow = None
        self.info = None
        self.results = {}

    def fetch_data(self):
        """Fetch all necessary financial data using yfinance with robust error handling."""
        try:
            self.info = self.ticker.info
            if not self.info or 'symbol' not in self.info:
                raise ValueError(f"Ticker {self.ticker_symbol} not found or invalid.")

            self.financials = self.ticker.financials
            self.balance_sheet = self.ticker.balance_sheet
            self.cash_flow = self.ticker.cashflow
            
            if self.financials is None or self.financials.empty:
                raise ValueError(f"Income statement data missing for {self.ticker_symbol}")
            if self.balance_sheet is None or self.balance_sheet.empty:
                raise ValueError(f"Balance sheet data missing for {self.ticker_symbol}")
            if self.cash_flow is None or self.cash_flow.empty:
                raise ValueError(f"Cash flow statement data missing for {self.ticker_symbol}")
                
        except Exception as e:
            raise ConnectionError(f"Failed to retrieve data for {self.ticker_symbol}: {str(e)}")

    def get_metric(self, df: pd.DataFrame, keys: List[str], default: float = 0.0) -> pd.Series:
        """Helper to fetch metrics with support for multiple possible accounting labels."""
        for key in keys:
            if key in df.index:
                return df.loc[key]
        return pd.Series([default] * len(df.columns), index=df.columns)

    def calculate_wacc(self) -> Dict:
        """Calculate Weighted Average Cost of Capital (WACC) using CAPM."""
        # 1. Cost of Equity
        risk_free_rate = DEFAULT_RISK_FREE_RATE
        beta = self.info.get('beta', DEFAULT_BETA)
        if beta is None or np.isnan(beta):
            beta = DEFAULT_BETA
            
        market_return = DEFAULT_MARKET_RETURN
        cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
        
        # 2. Cost of Debt
        interest_expense_series = self.get_metric(self.financials, ['Interest Expense'])
        interest_expense = abs(interest_expense_series.iloc[0]) if not interest_expense_series.empty else 0
        
        total_debt_series = self.get_metric(self.balance_sheet, ['Total Debt', 'Long Term Debt'])
        total_debt = total_debt_series.iloc[0] if not total_debt_series.empty else 0
        
        if total_debt > 0:
            cost_of_debt = interest_expense / total_debt
            if np.isnan(cost_of_debt) or cost_of_debt > 0.25: # Sanity check
                cost_of_debt = 0.05
        else:
            cost_of_debt = 0.05
        
        # 3. Tax Rate
        income_tax_series = self.get_metric(self.financials, ['Tax Provision', 'Income Tax Expense'])
        income_tax = income_tax_series.iloc[0] if not income_tax_series.empty else 0
        
        ebit_series = self.get_metric(self.financials, ['EBIT', 'Operating Income'])
        ebit = ebit_series.iloc[0] if not ebit_series.empty else 0
        
        tax_rate = income_tax / ebit if ebit > 0 else DEFAULT_TAX_RATE
        if np.isnan(tax_rate) or tax_rate < 0 or tax_rate > MAX_TAX_RATE:
            tax_rate = DEFAULT_TAX_RATE
        
        # 4. Capital Structure
        market_cap = self.info.get('marketCap', 0)
        if not market_cap:
            shares = self.info.get('sharesOutstanding', 0)
            price = self.info.get('currentPrice', 0)
            market_cap = (shares or 0) * (price or 0)
            
        total_capital = market_cap + total_debt
        
        if total_capital <= 0 or np.isnan(total_capital):
            wacc = DEFAULT_WACC
        else:
            equity_weight = market_cap / total_capital
            debt_weight = total_debt / total_capital
            wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
        
        return {
            'wacc': wacc if not np.isnan(wacc) else DEFAULT_WACC,
            'cost_of_equity': cost_of_equity,
            'cost_of_debt': cost_of_debt,
            'tax_rate': tax_rate,
            'equity_weight': market_cap / total_capital if total_capital > 0 else 1.0,
            'debt_weight': total_debt / total_capital if total_capital > 0 else 0.0,
            'beta': beta,
            'risk_free_rate': risk_free_rate,
            'market_return': market_return
        }

    def run_dcf(self, 
                years: int = 10, 
                growth_rate: float = 0.05, 
                discount_rate: Optional[float] = None, 
                perpetual_growth: float = 0.02) -> Dict:
        """
        Execute the DCF valuation pipeline.
        
        Args:
            years: Projection horizon (default 10)
            growth_rate: Expected annual FCF growth (default 5%)
            discount_rate: Custom WACC (optional)
            perpetual_growth: Terminal growth rate (default 2%)
        """
        if self.financials is None:
            self.fetch_data()
            
        # 1. Historical Free Cash Flow (FCF)
        ocf = self.get_metric(self.cash_flow, ['Operating Cash Flow', 'Total Cash From Operating Activities'])
        capex = abs(self.get_metric(self.cash_flow, ['Capital Expenditure', 'Net PPE Purchase And Sale']))
        
        fcf_history = ocf - capex
        if fcf_history.empty or np.isnan(fcf_history.iloc[0]):
            current_fcf = 0
        else:
            current_fcf = fcf_history.iloc[0]
        
        # 2. WACC Calculation
        wacc_comp = self.calculate_wacc()
        dr = discount_rate if discount_rate is not None else wacc_comp['wacc']
        
        # Sanity check: Discount rate must be higher than perpetual growth
        if dr <= perpetual_growth:
            dr = perpetual_growth + 0.02 # Minimum spread
            
        # 3. Projections
        projections = []
        for i in range(1, years + 1):
            projections.append(current_fcf * (1 + growth_rate) ** i)
            
        # 4. Terminal Value (Gordon Growth Model)
        terminal_value = (projections[-1] * (1 + perpetual_growth)) / (dr - perpetual_growth)
        
        # 5. Present Value (PV)
        pv_fcf = sum([fcf / (1 + dr) ** (i + 1) for i, fcf in enumerate(projections)])
        pv_tv = terminal_value / (1 + dr) ** years
        enterprise_value = pv_fcf + pv_tv
        
        # 6. Equity Value (Bridge)
        cash_series = self.get_metric(self.balance_sheet, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments'])
        cash = cash_series.iloc[0] if not cash_series.empty else 0
        
        debt_series = self.get_metric(self.balance_sheet, ['Total Debt', 'Long Term Debt'])
        debt = debt_series.iloc[0] if not debt_series.empty else 0
        
        equity_value = enterprise_value + cash - debt
        
        # 7. Intrinsic Value per Share
        shares = self.info.get('sharesOutstanding', 1)
        if not shares or shares == 0: shares = 1
        intrinsic_value = equity_value / shares
        
        current_price = self.info.get('currentPrice', 0)
        upside = (intrinsic_value / current_price) - 1 if current_price > 0 else 0
        
        self.results = {
            'ticker': self.ticker_symbol,
            'current_price': current_price,
            'intrinsic_value': intrinsic_value,
            'enterprise_value': enterprise_value,
            'equity_value': equity_value,
            'wacc': dr,
            'wacc_components': wacc_comp,
            'growth_rate': growth_rate,
            'perpetual_growth': perpetual_growth,
            'fcf_history': fcf_history.to_dict(),
            'projections': projections,
            'upside': upside,
            'shares': shares,
            'cash': cash,
            'debt': debt
        }
        
        return self.results

    def sensitivity_analysis(
        self,
        growth_rates: List[float],
        discount_rates: List[float],
        years: int = 10,
        perpetual_growth: Optional[float] = None,
    ) -> pd.DataFrame:
        """Return an intrinsic-value sensitivity table for growth and discount-rate scenarios.

        The method reuses the model's existing assumptions and restores the base-case
        results afterwards, so generating a sensitivity table does not overwrite the
        valuation shown in the main model output.
        """
        if not growth_rates or not discount_rates:
            raise ValueError("Growth rates and discount rates must not be empty.")

        if not self.results:
            self.run_dcf(years=years)

        base_results = self.results.copy()
        terminal_growth = (
            perpetual_growth
            if perpetual_growth is not None
            else base_results.get("perpetual_growth", 0.02)
        )
        scenarios = []

        try:
            for growth_rate in growth_rates:
                for discount_rate in discount_rates:
                    scenario = self.run_dcf(
                        years=years,
                        growth_rate=growth_rate,
                        discount_rate=discount_rate,
                        perpetual_growth=terminal_growth,
                    )
                    scenarios.append(
                        {
                            "Growth Rate": growth_rate,
                            "Discount Rate": discount_rate,
                            "Intrinsic Value": scenario["intrinsic_value"],
                        }
                    )
        finally:
            self.results = base_results

        return pd.DataFrame(scenarios).pivot(
            index="Growth Rate",
            columns="Discount Rate",
            values="Intrinsic Value",
        )

    def export_to_excel(self, filename: Optional[str] = None):
        """Export results to a professionally formatted Excel file."""
        if not self.results:
            self.run_dcf()
            
        fname = filename or f"{self.ticker_symbol}_DCF_Analysis.xlsx"
        
        with pd.ExcelWriter(fname, engine='openpyxl') as writer:
            # Summary Sheet
            summary_data = {
                'Metric': ['Ticker', 'Current Price', 'Intrinsic Value', 'Upside', 'WACC', 'Equity Value'],
                'Value': [
                    self.results['ticker'],
                    self.results['current_price'],
                    self.results['intrinsic_value'],
                    f"{self.results['upside']*100:.2f}%",
                    f"{self.results['wacc']*100:.2f}%",
                    self.results['equity_value']
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Historical Data
            hist_df = pd.concat([self.financials, self.balance_sheet, self.cash_flow])
            hist_df.to_excel(writer, sheet_name='Historical Data')
            
        print(f"Analysis exported to {fname}")
