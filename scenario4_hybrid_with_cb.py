"""
SCENARIO 4: HYBRID FILTER + MONTHLY CIRCUIT BREAKER
LONG: RSI < 30 AND Price > 200 EMA
SHORT: RSI > 70 (no filter)
With circuit breaker: If cumulative loss in any calendar month exceeds $500, stop all new entries until first day of next month
April 1, 2024 to April 10, 2026 - 1H candles
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*200)
print("SCENARIO 4: HYBRID FILTER + MONTHLY CIRCUIT BREAKER")
print("="*200)

# Fetch 1H data
print("\n[Downloading BTC-USD 1H data Apr 24 2024 - Apr 10 2026...]")
df = yf.download("BTC-USD", start="2024-04-24", end="2026-04-10", interval="1h", progress=False)

# Calculate RSI
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

df = df.dropna()

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")

# Parameters
ENTRY_COST_RATE = 0.001
EXIT_COST_RATE = 0.001
POSITION_SIZE = 0.1
TP_PERCENT = 0.04
SL_PERCENT = 0.012
MONTHLY_LOSS_LIMIT = 500

trades = []
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0

current_month = None
monthly_pnl = 0
circuit_breaker_active = False

for idx in range(len(df)):
    row = df.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema_200 = float(row['EMA_200'])
    current_date = row.name
    current_month_str = current_date.strftime('%Y-%m')
    
    # Check if new month
    if current_month != current_month_str:
        current_month = current_month_str
        monthly_pnl = 0
        circuit_breaker_active = False
    
    if in_trade:
        exit_triggered = False
        if trade_type == 'LONG':
            if price >= tp:
                exit_triggered = True
                exit_price = tp
            elif price <= sl:
                exit_triggered = True
                exit_price = sl
        else:
            if price <= tp:
                exit_triggered = True
                exit_price = tp
            elif price >= sl:
                exit_triggered = True
                exit_price = sl
        
        if exit_triggered:
            if trade_type == 'LONG':
                gross_pnl = (exit_price - entry_price) * POSITION_SIZE
            else:
                gross_pnl = (entry_price - exit_price) * POSITION_SIZE
            
            entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
            exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
            net_pnl = gross_pnl - entry_cost - exit_cost
            
            monthly_pnl += net_pnl
            
            if monthly_pnl < -MONTHLY_LOSS_LIMIT:
                circuit_breaker_active = True
            
            trades.append({
                'Date': current_date.strftime('%Y-%m-%d %H:%M'),
                'Type': trade_type,
                'Entry_Price': entry_price,
                'Exit_Price': exit_price,
                'Gross_PnL': gross_pnl,
                'Fees': entry_cost + exit_cost,
                'Net_PnL': net_pnl,
                'Win': 'Yes' if net_pnl > 0 else 'No'
            })
            
            in_trade = False
    
    if not in_trade and not circuit_breaker_active:
        # LONG: RSI < 30 AND Price > 200 EMA
        if rsi < 30 and price > ema_200:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            tp = price * (1 + TP_PERCENT)
            sl = price * (1 - SL_PERCENT)
        # SHORT: RSI > 70 (no filter)
        elif rsi > 70:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            tp = price * (1 - TP_PERCENT)
            sl = price * (1 + SL_PERCENT)

trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    trades_df['YearMonth'] = pd.to_datetime(trades_df['Date']).dt.strftime('%Y-%m')
    trades_df['Year'] = pd.to_datetime(trades_df['Date']).dt.year
    
    # Monthly breakdown
    monthly = trades_df.groupby('YearMonth').agg({
        'Type': 'count',
        'Net_PnL': 'sum',
    }).reset_index()
    monthly.columns = ['Month', 'Trades', 'Net_PnL']
    monthly['Wins'] = trades_df.groupby('YearMonth')['Win'].apply(lambda x: (x == 'Yes').sum()).values
    monthly['Win_Rate'] = (monthly['Wins'] / monthly['Trades'] * 100).round(1)
    
    # Identify CB triggered months
    monthly['CB'] = 'No'
    for idx, row in monthly.iterrows():
        month_str = row['Month']
        month_pnl = row['Net_PnL']
        if month_pnl < -MONTHLY_LOSS_LIMIT:
            monthly.at[idx, 'CB'] = 'YES'
    
    # Yearly breakdown
    yearly = trades_df.groupby('Year').agg({
        'Type': 'count',
        'Net_PnL': 'sum',
    }).reset_index()
    yearly.columns = ['Year', 'Trades', 'Net_PnL']
    yearly['Wins'] = trades_df.groupby('Year')['Win'].apply(lambda x: (x == 'Yes').sum()).values
    yearly['Win_Rate'] = (yearly['Wins'] / yearly['Trades'] * 100).round(1)
    
    # Summary stats
    total_trades = len(trades_df)
    total_wins = (trades_df['Win'] == 'Yes').sum()
    win_rate = total_wins / total_trades * 100
    total_pnl = trades_df['Net_PnL'].sum()
    
    winning_sum = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].sum()
    losing_sum = abs(trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].sum())
    profit_factor = winning_sum / losing_sum if losing_sum > 0 else 0
    
    print("\n" + "="*200)
    print("SCENARIO 4 - MONTHLY BREAKDOWN (CB = Circuit Breaker)")
    print("="*200)
    for _, row in monthly.iterrows():
        cb_marker = " <-- CB" if row['CB'] == 'YES' else ""
        print(f"{row['Month']}  {int(row['Trades']):4d}T  {int(row['Wins']):3d}W  {row['Win_Rate']:5.1f}%  ${row['Net_PnL']:+10.2f}{cb_marker}")
    
    print("\n" + "="*200)
    print("SCENARIO 4 - YEARLY BREAKDOWN")
    print("="*200)
    for _, row in yearly.iterrows():
        print(f"{int(row['Year'])}  {int(row['Trades']):4d}T  {int(row['Wins']):3d}W  {row['Win_Rate']:5.1f}%  ${row['Net_PnL']:+10.2f}")
    
    print("\n" + "="*200)
    print("SCENARIO 4 - OVERALL RESULTS")
    print("="*200)
    print(f"Total Trades:    {total_trades}")
    print(f"Win Rate:        {win_rate:.1f}%")
    print(f"Net P&L:         ${total_pnl:+.2f}")
    print(f"Profit Factor:   {profit_factor:.2f}x")
    print("="*200 + "\n")
    
    trades_df.to_csv('scenario4_hybrid_with_cb.csv', index=False)

print("Scenario 4 complete!")
