import pandas as pd

scenarios = [
    'scenario1_raw_rsi.csv',
    'scenario2_dual_filter.csv',
    'scenario3_hybrid_filter.csv',
    'scenario4_hybrid_with_cb.csv'
]

print("\nVERIFYING SCENARIO RESULTS FROM CSV FILES:\n")
print("="*100)

for scenario_file in scenarios:
    try:
        df = pd.read_csv(scenario_file)
        
        total_trades = len(df)
        total_pnl = df['Net_PnL'].sum()
        winning_trades = (df['Net_PnL'] > 0).sum()
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        winning_sum = df[df['Net_PnL'] > 0]['Net_PnL'].sum()
        losing_sum = abs(df[df['Net_PnL'] < 0]['Net_PnL'].sum())
        profit_factor = winning_sum / losing_sum if losing_sum > 0 else 0
        
        print(f"\n{scenario_file}:")
        print(f"  Total Trades:   {total_trades}")
        print(f"  Winning Trades: {winning_trades}")
        print(f"  Win Rate:       {win_rate:.1f}%")
        print(f"  Net P&L:        ${total_pnl:+.2f}")
        print(f"  Profit Factor:  {profit_factor:.2f}x")
        
    except FileNotFoundError:
        print(f"\n{scenario_file}: FILE NOT FOUND")

print("\n" + "="*100)
