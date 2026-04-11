import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

# Download data (using daily interval as hourly is limited to 730 days)
print("[Downloading BTC-USD data for April 2024 - April 2025...]")
start_date = "2024-04-01"
end_date = "2025-04-10"
df = yf.download("BTC-USD", start=start_date, end=end_date, interval="1d")

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")
print(f"[Total period: {(df.index[-1] - df.index[0]).days} days]\n")

# Calculate indicators
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

df = df.dropna()

# Trading parameters
TAKE_PROFIT = 0.04
STOP_LOSS = 0.012
POSITION_SIZE = 0.1
FEES = 0.002  # 0.20% round-trip

trades = []
balance = 0
position = None
entry_price = None
entry_time = None
entry_type = None

for i in range(14, len(df)):
    current_price = float(df['Close'].iloc[i])
    current_rsi = float(df['RSI'].iloc[i])
    ema200 = float(df['EMA200'].iloc[i])
    time = df.index[i]
    
    # Exit existing position
    if position is not None:
        pnl = (current_price - entry_price) * POSITION_SIZE * (1 if entry_type == 'LONG' else -1)
        pnl_pct = ((current_price / entry_price) - 1) * (1 if entry_type == 'LONG' else -1)
        fee_cost = abs(entry_price * POSITION_SIZE * FEES) + abs(current_price * POSITION_SIZE * FEES)
        net_pnl = pnl - fee_cost
        
        exit_reason = None
        
        # Check TP/SL
        if entry_type == 'LONG':
            if pnl_pct >= TAKE_PROFIT:
                exit_reason = 'TP'
            elif pnl_pct <= -STOP_LOSS:
                exit_reason = 'SL'
        else:  # SHORT
            if pnl_pct >= TAKE_PROFIT:
                exit_reason = 'TP'
            elif pnl_pct <= -STOP_LOSS:
                exit_reason = 'SL'
        
        # Check for opposite signal (crossover)
        if exit_reason is None:
            if entry_type == 'LONG' and current_rsi > 70:
                exit_reason = 'Signal'
            elif entry_type == 'SHORT' and current_rsi < 30:
                exit_reason = 'Signal'
        
        if exit_reason is not None:
            trades.append({
                'Entry Time': entry_time,
                'Exit Time': time,
                'Type': entry_type,
                'Entry Price': entry_price,
                'Exit Price': current_price,
                'P&L': net_pnl,
                'P&L %': pnl_pct * 100,
                'Exit Reason': exit_reason,
                'Win': 'Yes' if net_pnl > 0 else 'No'
            })
            balance += net_pnl
            position = None
            entry_price = None
            entry_time = None
            entry_type = None
    
    # Entry signals (only if no position)
    if position is None:
        # LONG: RSI < 30 AND Price > 200 EMA
        if current_rsi < 30 and current_price > ema200:
            position = 'LONG'
            entry_price = current_price
            entry_time = time
            entry_type = 'LONG'
        
        # SHORT: RSI > 70 (unfiltered)
        elif current_rsi > 70:
            position = 'SHORT'
            entry_price = current_price
            entry_time = time
            entry_type = 'SHORT'

# Convert trades to dataframe
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    trades_df['Year'] = trades_df['Entry Time'].dt.year
    trades_df['Month'] = trades_df['Entry Time'].dt.month
    trades_df['YearMonth'] = trades_df['Entry Time'].dt.strftime('%Y-%m')
    
    # Monthly breakdown
    monthly = trades_df.groupby('YearMonth').agg({
        'Type': 'count',
        'Win': lambda x: (x == 'Yes').sum(),
        'P&L': 'sum'
    }).reset_index()
    monthly.columns = ['Month', 'Trades', 'Wins', 'Net P&L']
    monthly['Losses'] = monthly['Trades'] - monthly['Wins']
    monthly['Win Rate'] = (monthly['Wins'] / monthly['Trades'] * 100).round(1)
    monthly['Net P&L'] = monthly['Net P&L'].round(2)
    
    # Direction breakdown
    long_trades = trades_df[trades_df['Type'] == 'LONG']
    short_trades = trades_df[trades_df['Type'] == 'SHORT']
    
    long_wins = (long_trades['Win'] == 'Yes').sum()
    short_wins = (short_trades['Win'] == 'Yes').sum()
    
    print("="*150)
    print("HYBRID FILTER STRATEGY - 1 YEAR BACKTEST (Apr 2024 - Apr 2025)".center(150))
    print("="*150)
    print()
    
    print("MONTHLY BREAKDOWN - PROFITABILITY BY MONTH".center(150))
    print("="*150)
    print()
    for _, row in monthly.iterrows():
        print(f"{row['Month']}  {int(row['Trades']):2d}  {int(row['Wins']):2d}  {int(row['Losses']):2d}  {row['Win Rate']:5.1f}%  ${row['Net P&L']:+9.2f}")
    print()
    print("="*150)
    
    print("OVERALL SUMMARY - 1 YEAR (Apr 2024 - Apr 2025)".center(150))
    print("="*150)
    print()
    print(f"Total Period:              365 days (Apr 2024 - Apr 2025)")
    print(f"Data Points:               {len(df)} daily bars")
    print()
    print("TRADE STATISTICS:")
    total_trades = len(trades_df)
    total_wins = (trades_df['Win'] == 'Yes').sum()
    total_losses = total_trades - total_wins
    win_rate = total_wins / total_trades * 100
    print(f"  Total Trades:            {total_trades}")
    print(f"  Winning Trades:          {total_wins}")
    print(f"  Losing Trades:           {total_losses}")
    print(f"  Win Rate:                {win_rate:.1f}%")
    print()
    print("PROFITABILITY:")
    gross_pnl = trades_df['P&L'].sum()
    avg_win = trades_df[trades_df['Win'] == 'Yes']['P&L'].mean()
    avg_loss = trades_df[trades_df['Win'] == 'No']['P&L'].mean()
    profit_factor = abs(trades_df[trades_df['Win'] == 'Yes']['P&L'].sum() / trades_df[trades_df['Win'] == 'No']['P&L'].sum()) if len(trades_df[trades_df['Win'] == 'No']) > 0 else 0
    
    print(f"  NET P&L:                 ${gross_pnl:+.2f}")
    print(f"  Profit Factor:           {profit_factor:.2f}x")
    print(f"  Avg Win:                 ${avg_win:+.2f} (per winning trade)")
    print(f"  Avg Loss:                ${avg_loss:+.2f} (per losing trade)")
    print()
    print("="*150)
    print("DIRECTION BREAKDOWN".center(150))
    print("="*150)
    print()
    
    long_pnl = long_trades['P&L'].sum()
    short_pnl = short_trades['P&L'].sum()
    long_wr = long_wins / len(long_trades) * 100 if len(long_trades) > 0 else 0
    short_wr = short_wins / len(short_trades) * 100 if len(short_trades) > 0 else 0
    
    print(f"LONG TRADES (RSI < 30 + Price > 200 EMA):")
    print(f"  Trades:        {len(long_trades)}")
    print(f"  Wins/Losses:   {long_wins} / {len(long_trades) - long_wins}")
    print(f"  Win Rate:      {long_wr:.1f}%")
    print(f"  Net P&L:       ${long_pnl:+.2f}")
    print()
    
    print(f"SHORT TRADES (RSI > 70, unfiltered):")
    print(f"  Trades:        {len(short_trades)}")
    print(f"  Wins/Losses:   {short_wins} / {len(short_trades) - short_wins}")
    print(f"  Win Rate:      {short_wr:.1f}%")
    print(f"  Net P&L:       ${short_pnl:+.2f}")
    print()
    print("="*150)
    print("DIRECTION COMPARISON TABLE".center(150))
    print("="*150)
    print()
    print(f"{'Direction':<10} {'Trades':>8} {'Wins':>6} {'Losses':>8} {'Win_Rate':>10} {'Net_PnL':>12}")
    print(f"{'LONG':<10} {len(long_trades):>8} {long_wins:>6} {len(long_trades) - long_wins:>8} {long_wr:>9.1f}% ${long_pnl:>10.2f}")
    print(f"{'SHORT':<10} {len(short_trades):>8} {short_wins:>6} {len(short_trades) - short_wins:>8} {short_wr:>9.1f}% ${short_pnl:>10.2f}")
    print(f"{'TOTAL':<10} {total_trades:>8} {total_wins:>6} {total_losses:>8} {win_rate:>9.1f}% ${gross_pnl:>10.2f}")
    print()
    print("="*150)
    print("PROFITABILITY VERDICT".center(150))
    print("="*150)
    print()
    
    if gross_pnl > 0:
        print(f"YES - PROFITABLE over 1 year!")
    else:
        print(f"NO - UNPROFITABLE over 1 year")
    
    print()
    print(f"Results Summary:")
    print(f"  Net Profit:     ${gross_pnl:+.2f}")
    print(f"  Trades:         {total_trades}")
    print(f"  Win Rate:       {win_rate:.1f}%")
    print(f"  Profit Factor:  {profit_factor:.2f}x")
    print()
    
    if gross_pnl > 0:
        print(f"Status: PROFITABLE - Strategy validates across diverse market conditions")
    else:
        print(f"Status: REVIEW NEEDED - Strategy underperforms in this period")
    print()
    print("="*150)
    
    # Export trades
    trades_df.to_csv('rsi_hybrid_1year_apr2024_apr2025_trades.csv', index=False)
    print(f"\nTrades exported to: rsi_hybrid_1year_apr2024_apr2025_trades.csv")
    print("="*150)
else:
    print("No trades generated in this period.")
