"""
HYBRID FILTER STRATEGY + MONTHLY CIRCUIT BREAKER
2 YEAR BACKTEST - April 2024 to April 2026
RISK MANAGEMENT TEST

Entry Rules:
- LONG: RSI < 30 AND Price > 200 EMA
- SHORT: RSI > 70 (unfiltered)

Risk Management:
- Monthly circuit breaker: If losses exceed $500 in a calendar month, stop trading for rest of month
- This prevents catastrophic monthly drawdowns like November 2024 (-$2,028)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

print("\n" + "="*200)
print("HYBRID FILTER + MONTHLY CIRCUIT BREAKER - 2 YEAR BACKTEST (Apr 2024 - Apr 2026)")
print("="*200)

# Fetch data - 2 YEARS (using daily data)
print("\n[Downloading BTC-USD data for 2 years (daily)...]")
df = yf.download("BTC-USD", start="2024-04-11", end="2026-04-10", interval="1d", progress=False)

# Calculate RSI
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

df = df.dropna()

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")
print(f"[Total period: {(df.index[-1] - df.index[0]).days} days (2 years)]")

# Parameters
ENTRY_COST_RATE = 0.0010  # 0.10% entry cost
EXIT_COST_RATE = 0.0010   # 0.10% exit cost
POSITION_SIZE = 0.1       # 0.1 BTC per trade
TP_PERCENT = 0.04         # 4% take profit
SL_PERCENT = 0.012        # 1.2% stop loss
MONTHLY_LOSS_LIMIT = 500  # $500 monthly loss limit for circuit breaker

# Trading state
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0
entry_date = None
trade_num = 0

trades = []
current_month = None
monthly_pnl = 0
circuit_breaker_active = False

print("\n[Starting backtest with monthly circuit breaker...]")

for idx in range(len(df)):
    row = df.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema_200 = float(row['EMA_200'])
    current_date = row.name
    current_month_str = current_date.strftime('%Y-%m')
    
    # Check if we've moved to a new month
    if current_month != current_month_str:
        current_month = current_month_str
        monthly_pnl = 0
        circuit_breaker_active = False
    
    # EXIT LOGIC
    if in_trade:
        exit_triggered = False
        exit_type = None
        exit_price = 0
        
        if trade_type == 'LONG':
            if price >= tp:
                exit_triggered = True
                exit_type = 'TP'
                exit_price = tp
            elif price <= sl:
                exit_triggered = True
                exit_type = 'SL'
                exit_price = sl
        else:  # SHORT
            if price <= tp:
                exit_triggered = True
                exit_type = 'TP'
                exit_price = tp
            elif price >= sl:
                exit_triggered = True
                exit_type = 'SL'
                exit_price = sl
        
        if exit_triggered:
            if trade_type == 'LONG':
                gross_pnl = (exit_price - entry_price) * POSITION_SIZE
            else:
                gross_pnl = (entry_price - exit_price) * POSITION_SIZE
            
            entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
            exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
            net_pnl = gross_pnl - entry_cost - exit_cost
            
            # Update monthly P&L
            monthly_pnl += net_pnl
            
            # Check if circuit breaker should trigger
            if monthly_pnl < -MONTHLY_LOSS_LIMIT:
                circuit_breaker_active = True
            
            cumulative_pnl = sum([t['Net_PnL'] for t in trades]) + net_pnl
            
            trades.append({
                'Trade_Num': trade_num,
                'Date': current_date.strftime('%Y-%m-%d'),
                'Type': trade_type,
                'Entry_Price': entry_price,
                'Exit_Price': exit_price,
                'Result': exit_type,
                'Gross_PnL': gross_pnl,
                'Entry_Cost': entry_cost,
                'Exit_Cost': exit_cost,
                'Net_PnL': net_pnl,
                'Cumulative_PnL': cumulative_pnl,
                'Circuit_Breaker_Active': 'No'
            })
            
            trade_num += 1
            in_trade = False
    
    # ENTRY LOGIC (Only if circuit breaker is NOT active)
    if not in_trade and not circuit_breaker_active:
        
        # LONG ENTRY: RSI < 30 AND Price > 200 EMA
        if rsi < 30 and price > ema_200:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            tp = price * (1 + TP_PERCENT)
            sl = price * (1 - SL_PERCENT)
            entry_date = current_date
        
        # SHORT ENTRY: RSI > 70 (unfiltered HYBRID)
        elif rsi > 70:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            tp = price * (1 - TP_PERCENT)
            sl = price * (1 + SL_PERCENT)
            entry_date = current_date

print("[Backtest complete!]\n")

# Convert to dataframe
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    trades_df['YearMonth'] = pd.to_datetime(trades_df['Date']).dt.strftime('%Y-%m')
    trades_df['Year'] = pd.to_datetime(trades_df['Date']).dt.year
    trades_df['Month'] = pd.to_datetime(trades_df['Date']).dt.month
    
    # Calculate monthly breakdown
    monthly = trades_df.groupby('YearMonth').agg({
        'Type': 'count',
        'Net_PnL': 'sum',
    }).reset_index()
    monthly.columns = ['Month', 'Trades', 'Net_PnL']
    monthly['Wins'] = trades_df.groupby('YearMonth').apply(lambda x: (x['Net_PnL'] > 0).sum()).values
    monthly['Losses'] = monthly['Trades'] - monthly['Wins']
    monthly['Win_Rate'] = (monthly['Wins'] / monthly['Trades'] * 100).round(1)
    
    # Identify which months had circuit breaker triggered
    monthly['Circuit_Breaker'] = 'No'
    for idx, row in monthly.iterrows():
        month_str = row['Month']
        month_trades = trades_df[trades_df['YearMonth'] == month_str]
        month_total_pnl = month_trades['Net_PnL'].sum()
        if month_total_pnl < -MONTHLY_LOSS_LIMIT:
            monthly.at[idx, 'Circuit_Breaker'] = 'YES'
    
    # Calculate yearly breakdown
    yearly = trades_df.groupby('Year').agg({
        'Type': 'count',
        'Net_PnL': 'sum',
    }).reset_index()
    yearly.columns = ['Year', 'Trades', 'Net_PnL']
    yearly['Wins'] = trades_df.groupby('Year').apply(lambda x: (x['Net_PnL'] > 0).sum()).values
    yearly['Losses'] = yearly['Trades'] - yearly['Wins']
    yearly['Win_Rate'] = (yearly['Wins'] / yearly['Trades'] * 100).round(1)
    
    # Direction breakdown
    long_trades = trades_df[trades_df['Type'] == 'LONG']
    short_trades = trades_df[trades_df['Type'] == 'SHORT']
    
    long_wins = (long_trades['Net_PnL'] > 0).sum()
    short_wins = (short_trades['Net_PnL'] > 0).sum()
    long_pnl = long_trades['Net_PnL'].sum()
    short_pnl = short_trades['Net_PnL'].sum()
    
    total_trades = len(trades_df)
    total_wins = (trades_df['Net_PnL'] > 0).sum()
    total_losses = total_trades - total_wins
    total_pnl = trades_df['Net_PnL'].sum()
    
    win_rate = total_wins / total_trades * 100
    
    # Profit factor
    winning_sum = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].sum()
    losing_sum = abs(trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].sum())
    profit_factor = winning_sum / losing_sum if losing_sum > 0 else 0
    
    # Display results
    print("="*200)
    print("MONTHLY BREAKDOWN (With Circuit Breaker)".center(200))
    print("="*200)
    print()
    for _, row in monthly.iterrows():
        cb_marker = " <-- CIRCUIT BREAKER TRIGGERED" if row['Circuit_Breaker'] == 'YES' else ""
        print(f"{row['Month']}  {int(row['Trades']):3d} trades  {int(row['Wins']):2d}W {int(row['Losses']):2d}L  Win Rate: {row['Win_Rate']:5.1f}%  Net P&L: ${row['Net_PnL']:+10.2f}{cb_marker}")
    print()
    
    print("="*200)
    print("YEARLY BREAKDOWN".center(200))
    print("="*200)
    print()
    for _, row in yearly.iterrows():
        print(f"{int(row['Year'])}  {int(row['Trades']):3d} trades  {int(row['Wins']):2d}W {int(row['Losses']):2d}L  Win Rate: {row['Win_Rate']:5.1f}%  Net P&L: ${row['Net_PnL']:+10.2f}")
    print()
    
    print("="*200)
    print("OVERALL SUMMARY - 2 YEARS (Apr 2024 - Apr 2026) WITH MONTHLY CIRCUIT BREAKER".center(200))
    print("="*200)
    print()
    print(f"Risk Management Rule: If monthly loss exceeds $500, stop trading for rest of month")
    print(f"Total Period:              731 days (Apr 2024 - Apr 2026)")
    print(f"Data Points:               {len(df)} daily bars")
    print()
    print("TRADE STATISTICS:")
    print(f"  Total Trades:            {total_trades}")
    print(f"  Winning Trades:          {total_wins}")
    print(f"  Losing Trades:           {total_losses}")
    print(f"  Win Rate:                {win_rate:.1f}%")
    print()
    print("PROFITABILITY:")
    print(f"  NET P&L:                 ${total_pnl:+.2f}")
    print(f"  Profit Factor:           {profit_factor:.2f}x")
    avg_win = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].mean() if total_wins > 0 else 0
    avg_loss = trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].mean() if total_losses > 0 else 0
    print(f"  Avg Win:                 ${avg_win:+.2f} (per winning trade)")
    print(f"  Avg Loss:                ${avg_loss:+.2f} (per losing trade)")
    print()
    
    print("="*200)
    print("DIRECTION BREAKDOWN".center(200))
    print("="*200)
    print()
    
    long_wr = long_wins / len(long_trades) * 100 if len(long_trades) > 0 else 0
    short_wr = short_wins / len(short_trades) * 100 if len(short_trades) > 0 else 0
    
    print(f"LONG TRADES (RSI < 30 + Price > 200 EMA):")
    print(f"  Trades:        {len(long_trades)}")
    print(f"  Wins/Losses:   {long_wins} / {len(long_trades) - long_wins}")
    print(f"  Win Rate:      {long_wr:.1f}%")
    print(f"  Net P&L:       ${long_pnl:+.2f}")
    print()
    
    print(f"SHORT TRADES (RSI > 70, unfiltered HYBRID):")
    print(f"  Trades:        {len(short_trades)}")
    print(f"  Wins/Losses:   {short_wins} / {len(short_trades) - short_wins}")
    print(f"  Win Rate:      {short_wr:.1f}%")
    print(f"  Net P&L:       ${short_pnl:+.2f}")
    print()
    
    print("="*200)
    print("DIRECTION COMPARISON TABLE".center(200))
    print("="*200)
    print()
    print(f"{'Direction':<10} {'Trades':>8} {'Wins':>6} {'Losses':>8} {'Win_Rate':>10} {'Net_PnL':>12}")
    print(f"{'LONG':<10} {len(long_trades):>8} {long_wins:>6} {len(long_trades) - long_wins:>8} {long_wr:>9.1f}% ${long_pnl:>10.2f}")
    print(f"{'SHORT':<10} {len(short_trades):>8} {short_wins:>6} {len(short_trades) - short_wins:>8} {short_wr:>9.1f}% ${short_pnl:>10.2f}")
    print(f"{'TOTAL':<10} {total_trades:>8} {total_wins:>6} {total_losses:>8} {win_rate:>9.1f}% ${total_pnl:>10.2f}")
    print()
    
    print("="*200)
    print("COMPARISON: HYBRID (NO CIRCUIT BREAKER) vs HYBRID (WITH CIRCUIT BREAKER)".center(200))
    print("="*200)
    print()
    print(f"WITHOUT Circuit Breaker: $+2,189.04 (43 trades, 34.9% WR, 1.62x PF)")
    print(f"WITH Circuit Breaker:    ${total_pnl:+.2f} ({total_trades} trades, {win_rate:.1f}% WR, {profit_factor:.2f}x PF)")
    print()
    
    profit_diff = 2189.04 - total_pnl
    trades_diff = 43 - total_trades
    
    if profit_diff > 0:
        print(f"Circuit Breaker Cost:    -${profit_diff:.2f} profit, -{trades_diff} trades")
    else:
        print(f"Circuit Breaker Gain:    +${abs(profit_diff):.2f} profit, -{trades_diff} trades")
    
    print()
    
    # Check if November 2024 was protected
    nov_2024_novbreaker = False
    if '2024-11' in monthly['Month'].values:
        nov_row = monthly[monthly['Month'] == '2024-11'].iloc[0]
        print(f"November 2024 Result: {int(nov_row['Trades'])} trades, Loss: ${nov_row['Net_PnL']:+.2f}")
        if nov_row['Circuit_Breaker'] == 'YES':
            nov_2024_novbreaker = True
            print(f"  --> CIRCUIT BREAKER ACTIVATED: Prevented further losses after month loss exceeded $500")
        else:
            print(f"  --> Circuit breaker did NOT trigger (loss was only ${nov_row['Net_PnL']:.2f}, below $500 threshold)")
    
    print()
    print("="*200)
    print("CIRCUIT BREAKER VERDICT".center(200))
    print("="*200)
    print()
    
    if nov_2024_novbreaker:
        print(f"SUCCESS: Monthly circuit breaker WOULD HAVE PROTECTED you.")
        print(f"But note: The $500 limit needs calibration based on your actual capital.")
        print(f"For $10,000 capital, 5% loss = $500, so rule triggers after 5% monthly loss.")
    else:
        print(f"Circuit breaker did not need to trigger in this backtest.")
        print(f"Adjust the $500 threshold based on your actual capital:")
        print(f"  - $10,000 capital → $500 limit (5% max monthly loss)")
        print(f"  - $20,000 capital → $1,000 limit (5% max monthly loss)")
        print(f"  - $5,000 capital → $250 limit (5% max monthly loss)")
    
    print()
    print("="*200)
    
    # Export trades
    trades_df.to_csv('hybrid_with_circuit_breaker_trades.csv', index=False)
    print(f"\nTrades exported to: hybrid_with_circuit_breaker_trades.csv")
    print("="*200)
else:
    print("No trades generated in this period.")
