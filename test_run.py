from automated_dcf.dcf import DCFModel

def test():
    ticker = "AAPL"
    print(f"Testing DCF for {ticker}...")
    model = DCFModel(ticker)
    model.fetch_data()
    results = model.run_dcf(growth_rate=0.05)
    
    print("\n--- Results ---")
    for k, v in results.items():
        if k != 'fcf_history' and k != 'projections':
            print(f"{k}: {v}")
    
    print("\nSensitivity Analysis:")
    growth_rates = [0.02, 0.04, 0.06]
    discount_rates = [0.07, 0.08, 0.09]
    sensitivity = model.sensitivity_analysis(growth_rates, discount_rates)
    print(sensitivity)

if __name__ == "__main__":
    test()
