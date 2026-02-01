import click
from .dcf import DCFModel
import pandas as pd

@click.command()
@click.argument('ticker')
@click.option('--years', default=5, help='Number of years for projection')
@click.option('--growth', default=0.05, help='Expected growth rate (e.g. 0.05 for 5%)')
@click.option('--discount', default=None, type=float, help='Discount rate (WACC). If None, it will be calculated.')
@click.option('--output', default='excel', type=click.Choice(['excel', 'csv', 'print']), help='Output format')
def main(ticker, years, growth, discount, output):
    """Automated DCF Valuation Tool for TICKER."""
    click.echo(f"Running DCF for {ticker}...")
    
    try:
        model = DCFModel(ticker)
        model.fetch_data()
        results = model.run_dcf(years=years, growth_rate=growth, discount_rate=discount)
        
        click.echo("\n--- DCF Results ---")
        click.echo(f"Ticker: {results['ticker']}")
        click.echo(f"Current Price: ${results['current_price']:.2f}")
        click.echo(f"Intrinsic Value: ${results['intrinsic_value']:.2f}")
        click.echo(f"WACC: {results['wacc']*100:.2f}%")
        click.echo(f"Upside: {results['upside']*100:.2f}%")

        if output == 'excel':
            filename = f"{ticker}_DCF_Analysis.xlsx"
            model.export_to_excel(filename)
            click.echo(f"\nExcel report saved to: {filename}")
            
            plot_filename = f"{ticker}_DCF_Plot.png"
            model.plot_results(plot_filename)
            click.echo(f"Plot saved to: {plot_filename}")
        elif output == 'csv':
            filename = f"{ticker}_DCF_Results.csv"
            pd.DataFrame([results]).to_csv(filename, index=False)
            click.echo(f"\nCSV results saved to: {filename}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    main()
