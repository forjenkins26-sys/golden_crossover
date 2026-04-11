"""
ULTRA-FAST PARAMETER OPTIMIZATION
- Vectorized where possible
- Fixed deprecation warnings
- Progress tracking
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*150)
print("ULTRA-FAST PARAMETER OPTIMIZATION")
print("="*150)

# Download once
print("\nDownloading data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Calculate indicators
print("Pre-calculating indicators...")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=20, num_std=2.0):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, lower

df['RSI'] = calculate_rsi(df['Close']).values
df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
df['BB_Upper'] = df['BB_Upper'].values
df['BB_Lower'] = df['BB_Lower'].values
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean().values
df['Session'] = df.index.map(lambda x: 'Active' if (0.5 <= x.hour + x.minute/60 < 4.5 or 
                                                      5.5 <= x.hour + x.minute/60 < 11.5 or
                                                      12.5 <= x.hour + x.minute/60 < 17.5) else 'Off')
df = df.dropna()

# Convert to numpy arrays for speed
close_arr = df['Close'].values
rsi_arr = df['RSI'].values
bb_upper_arr = df['BB_Upper'].values
bb_lower_arr = df['BB_Lower'].values
ema_200_arr = df['EMA_200'].values
session_arr = df['Session'].values

num_bars = len(close_arr)
print(f"Loaded {num_bars} bars. Testing {3 * 3 * 4 * 5 * 2} combinations...\n")

results = []
test_count = 0

# Test all combinations
for rsi_long in [20, 25, 30]:
    for rsi_short in [70, 75, 80]:
        for tp2_pct in [0.03, 0.04, 0.05, 0.06]:
            for sl_pct in [0.005, 0.008, 0.01, 0.015, 0.02]:
                for use_ema in [True, False]:
                    test_count += 1
                    
                    # Fast backtest using numpy arrays
                    trades = []
                    in_trade = False
                    trade_type = None
                    entry_price = 0.0
                    tp_price = 0.0
                    sl_price = 0.0
                    
                    for i in range(num_bars):
                        price = float(close_arr[i])
                        rsi = float(rsi_arr[i])
                        
                        # Exit logic
                        if in_trade:
                            if trade_type == 'LONG':
                                if price >= tp_price or price <= sl_price:
                                    if price >= tp_price:
                                        pnl = (price - entry_price) * 0.1 - 0.002
                                    else:
                                        pnl = (sl_price - entry_price) * 0.1 - 0.002
                                    trades.append(float(pnl))
                                    in_trade = False
                            else:  # SHORT
                                if price <= tp_price or price >= sl_price:
                                    if price <= tp_price:
                                        pnl = (entry_price - price) * 0.1 - 0.002
                                    else:
                                        pnl = (entry_price - sl_price) * 0.1 - 0.002
                                    trades.append(float(pnl))
                                    in_trade = False
                        
                        # Entry logic
                        if not in_trade and session_arr[i] == 'Active':
                            price_le_bb_lower = price <= float(bb_lower_arr[i])
                            price_ge_bb_upper = price >= float(bb_upper_arr[i])
                            
                            # LONG
                            if rsi < rsi_long and price_le_bb_lower:
                                if use_ema:
                                    if price > float(ema_200_arr[i]):
                                        in_trade = True
                                        trade_type = 'LONG'
                                        entry_price = price
                                        tp_price = price * (1 + tp2_pct)
                                        sl_price = price * (1 - sl_pct)
                                else:
                                    in_trade = True
                                    trade_type = 'LONG'
                                    entry_price = price
                                    tp_price = price * (1 + tp2_pct)
                                    sl_price = price * (1 - sl_pct)
                            
                            # SHORT
                            elif rsi > rsi_short and price_ge_bb_upper:
                                if use_ema:
                                    if price < float(ema_200_arr[i]):
                                        in_trade = True
                                        trade_type = 'SHORT'
                                        entry_price = price
                                        tp_price = price * (1 - tp2_pct)
                                        sl_price = price * (1 + sl_pct)
                                else:
                                    in_trade = True
                                    trade_type = 'SHORT'
                                    entry_price = price
                                    tp_price = price * (1 - tp2_pct)
                                    sl_price = price * (1 + sl_pct)
                    
                    # Process results
                    if len(trades) >= 10:
                        pnl_total = float(sum(trades))
                        wins = int(sum(1 for p in trades if p > 0))
                        win_rate = float(wins / len(trades))
                        total_wins = float(sum(max(p, 0) for p in trades))
                        total_loss = float(sum(abs(min(p, 0)) for p in trades))
                        pf = float(total_wins / total_loss if total_loss > 0 else 0)
                        
                        score = float(pnl_total * pf if pf > 0 else pnl_total)
                        
                        results.append({
                            'RSI_L': int(rsi_long),
                            'RSI_S': int(rsi_short),
                            'TP2%': float(tp2_pct * 100),
                            'SL%': float(sl_pct * 100),
                            'EMA': 'Y' if use_ema else 'N',
                            'Trades': int(len(trades)),
                            'P&L': pnl_total,
                            'WinRate%': win_rate * 100,
                            'PF': pf,
                            'Score': score
                        })
                    
                    if test_count % 60 == 0:
                        print(f"  Progress: {test_count}/360 combos tested...")

# Sort by score
results = sorted(results, key=lambda x: x['Score'], reverse=True)

print("\n" + "="*150)
print("TOP 20 BEST COMBINATIONS")
print("="*150 + "\n")

if results:
    for i, r in enumerate(results[:20]):
        print(f"{i+1:2d}. RSI {r['RSI_L']}/{r['RSI_S']} | TP2 {r['TP2%']:.0f}% SL {r['SL%']:.2f}% | EMA:{r['EMA']} | "
              f"Trades:{r['Trades']:2d} | P&L:${r['P&L']:+7.2f} | WR:{r['WinRate%']:5.1f}% | PF:{r['PF']:.2f} | Score:{r['Score']:+8.2f}")
else:
    print("No viable combinations found (need >=10 trades)")

print("\n" + "="*150)
print(f"TOTAL VIABLE COMBINATIONS: {len(results)} out of 360")
print("="*150 + "\n")
