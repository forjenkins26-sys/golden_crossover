"""
HYBRID FILTER - PERIOD ANALYSIS
1. Jan 2026 to April 10 2026 (3.5 months)
2. April 2025 to April 2026 (1 year)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

# Fetch data for both periods
print("\n" + "="*150)
print("HYBRID FILTER - PERIOD ANALYSIS")
print("="*150)

# PERIOD 1: Jan 2026 to April 10 2026
print("\n[Period 1: Jan 2026 - Apr 10 2026]")
print("[Downloading BTC-USD data...]")
df1 = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1d", progress=False)

delta_rsi = df1['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df1['RSI'] = 100 - (100 / (1 + rs))
df1['EMA_200'] = df1['Close'].ewm(span=200, adjust=False).mean()
df1 = df1.dropna()

ENTRY_COST_RATE = 0.0010
EXIT_COST_RATE = 0.0010
POSITION_SIZE = 0.1
TP_PERCENT = 0.04
SL_PERCENT = 0.012

trades1 = []
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0
trade_num = 0

for idx in range(len(df1)):
    row = df1.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema_200 = float(row['EMA_200'])
    current_date = row.name
    
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
            
            trades1.append({
                'Date': current_date.strftime('%Y-%m-%d'),
                'Type': trade_type,
                'Entry': entry_price,
                'Exit': exit_price,
                'PnL': net_pnl,
            })
            
            trade_num += 1
            in_trade = False
    
    if not in_trade:
        if rsi < 30 and price > ema_200:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            tp = price * (1 + TP_PERCENT)
            sl = price * (1 - SL_PERCENT)
        elif rsi > 70:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            tp = price * (1 - TP_PERCENT)
            sl = price * (1 + SL_PERCENT)

trades_df1 = pd.DataFrame(trades1)

print(f"[Data loaded: {len(df1)} bars from {df1.index[0]} to {df1.index[-1]}]")
print(f"[Trades found: {len(trades_df1)}]")
total_pnl1 = trades_df1['PnL'].sum() if len(trades_df1) > 0 else 0
print(f"[Net P&L: ${total_pnl1:+.2f}]")

# PERIOD 2: April 2025 to April 2026
print("\n[Period 2: Apr 2025 - Apr 2026 (1 year)]")
print("[Downloading BTC-USD data...]")
df2 = yf.download("BTC-USD", start="2025-04-10", end="2026-04-10", interval="1d", progress=False)

delta_rsi = df2['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df2['RSI'] = 100 - (100 / (1 + rs))
df2['EMA_200'] = df2['Close'].ewm(span=200, adjust=False).mean()
df2 = df2.dropna()

trades2 = []
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0
trade_num = 0

for idx in range(len(df2)):
    row = df2.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema_200 = float(row['EMA_200'])
    current_date = row.name
    
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
            
            trades2.append({
                'Date': current_date.strftime('%Y-%m-%d'),
                'Type': trade_type,
                'Entry': entry_price,
                'Exit': exit_price,
                'PnL': net_pnl,
            })
            
            trade_num += 1
            in_trade = False
    
    if not in_trade:
        if rsi < 30 and price > ema_200:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            tp = price * (1 + TP_PERCENT)
            sl = price * (1 - SL_PERCENT)
        elif rsi > 70:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            tp = price * (1 - TP_PERCENT)
            sl = price * (1 + SL_PERCENT)

trades_df2 = pd.DataFrame(trades2)

print(f"[Data loaded: {len(df2)} bars from {df2.index[0]} to {df2.index[-1]}]")
print(f"[Trades found: {len(trades_df2)}]")
total_pnl2 = trades_df2['PnL'].sum() if len(trades_df2) > 0 else 0
print(f"[Net P&L: ${total_pnl2:+.2f}]")

# Summary
print("\n" + "="*150)
print("SUMMARY")
print("="*150)
print()
print(f"Period 1: Jan 2026 - Apr 10 2026 (3.5 months)")
print(f"  Trades: {len(trades_df1)}")
print(f"  Net P&L: ${total_pnl1:+.2f}")
print()
print(f"Period 2: Apr 2025 - Apr 2026 (1 year)")
print(f"  Trades: {len(trades_df2)}")
print(f"  Net P&L: ${total_pnl2:+.2f}")
print()
print("="*150)
