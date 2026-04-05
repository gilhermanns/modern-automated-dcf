import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import os
import matplotlib.pyplot as plt
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

class DCFModel:
    def __init__(self, ticker: str):
        self.ticker_symbol = ticker
        self.ticker = yf.Ticker(ticker)
        self.financials = None
        self.balance_sheet = None
        self.cash_flow = None
        self.info = None
        self.results = {}

    def fetch_data(self):
        """Fetch all necessary financial data using yfinance."""
        try:
            self.financials = self.ticker.financials
            self.balance_sheet = self.ticker.balance_sheet
            self.cash_flow = self.ticker.cashflow
            self.info = self.ticker.info
            
            if self.financials.empty or self.balance_sheet.empty or self.cash_flow.empty:
                raise ValueError(f"Could not fetch complete financial data for {self.ticker_symbol}")
        except Exception as e:
            raise ConnectionError(f"Error fetching data for {self.ticker_symbol}: {str(e)}")

    def get_metric(self, df: pd.DataFrame, keys: list, default: float = 0.0) -> pd.Series:
        """Helper to fetch metrics with fuzzy matching/multiple possible keys."""
        for key in keys:
            if key in df.index:
                return df.loc[key]
        return pd.Series([default] * len(df.columns), index=df.columns)

    def calculate_wacc(self) -> Dict:
        """Calculate Weighted Average Cost of Capital (WACC) and return components."""
        # Risk-free rate (10Y Treasury yield as proxy, default 4%)
        risk_free_rate = 0.04 
        
        # Beta
        beta = self.info.get('beta', 1.2)
        
        # Market Return (S&P 500 historical average ~10%)
        market_return = 0.10
        
        # Cost of Equity (CAPM)
        cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
        
        # Cost of Debt
        interest_expense_series = self.get_metric(self.financials, ['Interest Expense'])
        interest_expense = abs(interest_expense_series.iloc[0]) if not interest_expense_series.empty else 0
        
        total_debt_series = self.get_metric(self.balance_sheet, ['Total Debt', 'Long Term Debt'])
        total_debt = total_debt_series.iloc[0] if not total_debt_series.empty else 0
        
        cost_of_debt = interest_expense / total_debt if (total_debt > 0 and not np.isnan(interest_expense / total_debt)) else 0.05
        
        # Tax Rate
        income_tax_series = self.get_metric(self.financials, ['Tax Provision', 'Income Tax Expense'])
        income_tax = income_tax_series.iloc[0] if (not income_tax_series.empty and not np.isnan(income_tax_series.iloc[0])) else 0
        
        ebit_series = self.get_metric(self.financials, ['EBIT', 'Operating Income'])
        ebit = ebit_series.iloc[0] if (not ebit_series.empty and not np.isnan(ebit_series.iloc[0])) else 0
        
        tax_rate = income_tax / ebit if ebit > 0 else 0.21
        if np.isnan(tax_rate) or tax_rate < 0 or tax_rate > 0.5: tax_rate = 0.21
        
        # Market Value of Equity and Debt
        market_cap = self.info.get('marketCap', 0)
        if market_cap == 0 or market_cap is None:
            shares = self.info.get('sharesOutstanding', 0)
            price = self.info.get('currentPrice', 0)
            market_cap = (shares or 0) * (price or 0)
            
        total_value = market_cap + total_debt
        
        if total_value == 0 or np.isnan(total_value):
            wacc = 0.08
        else:
            wacc = (market_cap / total_value) * cost_of_equity + \
                   (total_debt / total_value) * cost_of_debt * (1 - tax_rate)
        
        return {
            'wacc': wacc if not np.isnan(wacc) else 0.08,
            'cost_of_equity': cost_of_equity,
            'cost_of_debt': cost_of_debt,
            'tax_rate': tax_rate,
            'equity_weight': market_cap / total_value if total_value > 0 else 1.0,
            'debt_weight': total_debt / total_value if total_value > 0 else 0.0,
            'beta': beta,
            'risk_free_rate': risk_free_rate,
            'market_return': market_return
        }

    def run_dcf(self, 
                years: int = 10, 
                growth_rate: float = 0.05, 
                discount_rate: Optional[float] = None, 
                perpetual_growth: float = 0.025) -> Dict:
        """Run the DCF valuation."""
        if self.financials is None:
            self.fetch_data()
            
        # 1. Calculate Historical FCF
        ocf = self.get_metric(self.cash_flow, ['Operating Cash Flow', 'Total Cash From Operating Activities'])
        capex = abs(self.get_metric(self.cash_flow, ['Capital Expenditure', 'Net PPE Purchase And Sale']))
        
        fcf_history = ocf - capex
        current_fcf = fcf_history.iloc[0] # Most recent year
        
        # 2. Determine Discount Rate (WACC)
        wacc_components = self.calculate_wacc()
        if discount_rate is None:
            discount_rate = wacc_components['wacc']
            
        # 3. Project Future Cash Flows
        projections = []
        for i in range(1, years + 1):
            projected_fcf = current_fcf * (1 + growth_rate) ** i
            projections.append(projected_fcf)
            
        # 4. Calculate Terminal Value
        terminal_value = (projections[-1] * (1 + perpetual_growth)) / (discount_rate - perpetual_growth)
        
        # 5. Discount Cash Flows
        pv_fcf = sum([fcf / (1 + discount_rate) ** (i + 1) for i, fcf in enumerate(projections)])
        pv_terminal_value = terminal_value / (1 + discount_rate) ** years
        
        enterprise_value = pv_fcf + pv_terminal_value
        
        # 6. Equity Value
        cash_series = self.get_metric(self.balance_sheet, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments'])
        cash = cash_series.iloc[0] if not cash_series.empty else 0
        
        debt_series = self.get_metric(self.balance_sheet, ['Total Debt', 'Long Term Debt'])
        debt = debt_series.iloc[0] if not debt_series.empty else 0
        
        equity_value = enterprise_value + cash - debt
        
        # 7. Per Share Value
        shares = self.info.get('sharesOutstanding', 1)
        intrinsic_value = equity_value / shares
        
        self.results = {
            'ticker': self.ticker_symbol,
            'current_price': self.info.get('currentPrice'),
            'intrinsic_value': intrinsic_value,
            'enterprise_value': enterprise_value,
            'equity_value': equity_value,
            'wacc': discount_rate,
            'wacc_components': wacc_components,
            'growth_rate': growth_rate,
            'perpetual_growth': perpetual_growth,
            'fcf_history': fcf_history.to_dict(),
            'projections': projections,
            'upside': (intrinsic_value / self.info.get('currentPrice', 1)) - 1,
            'shares': shares,
            'cash': cash,
            'debt': debt
        }
        
        return self.results

    def sensitivity_analysis(self, growth_range, discount_range):
        """Perform sensitivity analysis on growth and discount rates."""
        matrix = []
        for d in discount_range:
            row = []
            for g in growth_range:
                res = self.run_dcf(growth_rate=g, discount_rate=d)
                row.append(res['intrinsic_value'])
            matrix.append(row)
        return pd.DataFrame(matrix, index=[f"{d*100:.1f}%" for d in discount_range], 
                          columns=[f"{g*100:.1f}%" for g in growth_range])

    def _apply_corporate_style(self, ws, title):
        """Apply professional corporate styling to a worksheet."""
        blue_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
        white_font = Font(color='FFFFFF', bold=True)
        header_font = Font(bold=True)
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # Title
        ws.merge_cells('A1:E1')
        ws['A1'] = title
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Headers
        for cell in ws[2]:
            cell.fill = blue_fill
            cell.font = white_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Auto-adjust column width
        for col in ws.columns:
            max_length = 0
            # Use the first cell that is not a MergedCell to get the column letter
            column_letter = None
            for cell in col:
                if not column_letter and hasattr(cell, 'column_letter'):
                    column_letter = cell.column_letter
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            if column_letter:
                adjusted_width = (max_length + 2)
                ws.column_dimensions[column_letter].width = adjusted_width

    def export_to_excel(self, filename: str = None):
        """Export DCF results with professional formatting."""
        if not self.results:
            self.run_dcf()
            
        if filename is None:
            filename = f"{self.ticker_symbol}_DCF_Model.xlsx"
            
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Sheet 1: Historical Financials
            hist_df = pd.concat([self.financials, self.balance_sheet, self.cash_flow])
            hist_df.to_excel(writer, sheet_name='Historical Financials')
            self._apply_corporate_style(writer.sheets['Historical Financials'], f"Historical Financial Data: {self.ticker_symbol}")

            # Sheet 2: DCF Projections
            proj_df = pd.DataFrame({
                'Year': [f"Year {i+1}" for i in range(len(self.results['projections']))],
                'Projected FCF': self.results['projections']
            })
            proj_df.to_excel(writer, sheet_name='DCF Projections', index=False, startrow=1)
            self._apply_corporate_style(writer.sheets['DCF Projections'], f"10-Year FCF Projections: {self.ticker_symbol}")

            # Sheet 3: Valuation Summary
            summary_data = {
                'Metric': ['Ticker', 'Current Price', 'Intrinsic Value', 'Upside', 'WACC', 'Enterprise Value', 'Equity Value', 'Shares Outstanding', 'Cash', 'Debt'],
                'Value': [
                    self.results['ticker'],
                    self.results['current_price'],
                    self.results['intrinsic_value'],
                    f"{self.results['upside']*100:.2f}%",
                    f"{self.results['wacc']*100:.2f}%",
                    self.results['enterprise_value'],
                    self.results['equity_value'],
                    self.results['shares'],
                    self.results['cash'],
                    self.results['debt']
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Valuation Summary', index=False, startrow=1)
            self._apply_corporate_style(writer.sheets['Valuation Summary'], f"Valuation Summary: {self.ticker_symbol}")

            # Sheet 4: Sensitivity Analysis
            growth_rates = np.linspace(0.01, 0.04, 25)
            discount_rates = np.linspace(0.06, 0.18, 25)
            sensitivity_df = self.sensitivity_analysis(growth_rates, discount_rates)
            sensitivity_df.to_excel(writer, sheet_name='Sensitivity Analysis', startrow=1)
            self._apply_corporate_style(writer.sheets['Sensitivity Analysis'], f"Sensitivity Analysis (WACC vs Growth): {self.ticker_symbol}")

            # Sheet 5: Assumptions
            assumptions = {
                'Assumption': ['Growth Rate (Explicit)', 'Perpetual Growth Rate', 'Risk-Free Rate', 'Market Return', 'Beta', 'Cost of Equity', 'Cost of Debt', 'Tax Rate'],
                'Value': [
                    self.results['growth_rate'],
                    self.results['perpetual_growth'],
                    self.results['wacc_components']['risk_free_rate'],
                    self.results['wacc_components']['market_return'],
                    self.results['wacc_components']['beta'],
                    self.results['wacc_components']['cost_of_equity'],
                    self.results['wacc_components']['cost_of_debt'],
                    self.results['wacc_components']['tax_rate']
                ]
            }
            pd.DataFrame(assumptions).to_excel(writer, sheet_name='Assumptions', index=False, startrow=1)
            self._apply_corporate_style(writer.sheets['Assumptions'], f"Model Assumptions: {self.ticker_symbol}")

    def plot_all_charts(self, output_dir: str = "charts"):
        """Generate all required charts for the demo."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        if not self.results:
            self.run_dcf()

        # 1. Historical Revenue/FCF
        hist_fcf = list(self.results['fcf_history'].values())[::-1]
        years_hist = list(range(-len(hist_fcf) + 1, 1))
        
        plt.figure(figsize=(10, 6))
        plt.plot(years_hist, hist_fcf, marker='o', label='Historical FCF')
        plt.title(f"Historical Free Cash Flow: {self.ticker_symbol}")
        plt.xlabel("Years from Present")
        plt.ylabel("FCF (USD)")
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{output_dir}/{self.ticker_symbol}_historical_fcf.png")
        plt.close()

        # 2. 10-year FCF Projection Waterfall (Simplified as bar chart)
        projections = self.results['projections']
        years_proj = list(range(1, len(projections) + 1))
        
        plt.figure(figsize=(10, 6))
        plt.bar(years_proj, projections, color='skyblue', label='Projected FCF')
        plt.title(f"10-Year FCF Projection: {self.ticker_symbol}")
        plt.xlabel("Year")
        plt.ylabel("FCF (USD)")
        plt.savefig(f"{output_dir}/{self.ticker_symbol}_fcf_projection.png")
        plt.close()

        # 3. WACC Components Pie Chart
        w = self.results['wacc_components']
        labels = ['Equity Weight', 'Debt Weight']
        sizes = [w['equity_weight'], w['debt_weight']]
        
        plt.figure(figsize=(8, 8))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=['#1f4e78', '#a6a6a6'])
        plt.title(f"Capital Structure (WACC Components): {self.ticker_symbol}")
        plt.savefig(f"{output_dir}/{self.ticker_symbol}_wacc_pie.png")
        plt.close()
