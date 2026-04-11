"""
CLEAN PARAMETER OPTIMIZATION
Using direct DataFrame access for simplicity and reliability
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*150)
print("PARAMETER OPTIMIZATION - Testing 360 Combinations")
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

df['RSI'] = calculate_rsi(df['Close'])
df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
df['Session'] = df.index.map(lambda x: True if (0.5 <= x.hour + x.minute/60 < 4.5 or 
                                                  5.5 <= x.hour + x.minute/60 < 11.5 or
                                                  12.5 <= x.hour + x.minute/60 < 17.5) else False)
df = df.dropna()

print(f"Loaded {len(df)} bars. Testing {3 * 3 * 4 * 5 * 2} combinations...\n")

results = []
test_count = 0

# Test all combinations
for rsi_long in [20, 25, 30]:
    for rsi_short in [70, 75, 80]:
        for tp2_pct in [0.03, 0.04, 0.05, 0.06]:
            for sl_pct in [0.005, 0.008, 0.01, 0.015, 0.02]:
                for use_ema in [True, False]:
                    test_count += 1
                    
                    # Backtest
                    trades = []
                    in_trade = False
                    trade_type = None
                    entry_price = 0.0
                    tp_price = 0.0
                    sl_price = 0.0
                    
                    for idx in range(len(df)):
                        try:
                            row = df.iloc[idx]
                            
                            price = float(row['Close'])
                            rsi = float(row['RSI'])
                            bb_upper = float(row['BB_Upper'])
                            bb_lower = float(row['BB_Lower'])
                            ema_200 = float(row['EMA_200'])
                            in_session = bool(row['Session'])
                            
                            # Exit
                            if in_trade:
                                if trade_type == 'LONG':
                                    if price >= tp_price or price <= sl_price:
                                        pnl = ((price - entry_price) if price >= tp_price else (sl_price - entry_price)) * 0.1 - 0.002
                                        trades.append(pnl)
                                        in_trade = False
                                else:  # SHORT
                                    if price <= tp_price or price >= sl_price:
                                        pnl = ((entry_price - price) if price <= tp_price else (entry_price - sl_price)) * 0.1 - 0.002
                                        trades.append(pnl)
                                        in_trade = False
                            
                            # Entry
                            if not in_trade and in_session:
                                # LONG
                                long_cond = (rsi < rsi_long and price <= bb_lower)
                                if use_ema:
                                    long_cond = long_cond and (price > ema_200)
                                
                                if long_cond:
                                    in_trade = True
                                    trade_type = 'LONG'
                                    entry_price = price
                                    tp_price = price * (1 + tp2_pct)
                                    sl_price = price * (1 - sl_pct)
                                
                                # SHORT
                                short_cond = (rsi > rsi_short and price >= bb_upper)
                                if use_ema:
                                    short_cond = short_cond and (price < ema_200)
                                
                                if short_cond:
                                    in_trade = True
                                    trade_type = 'SHORT'
                                    entry_price = price
                                    tp_price = price * (1 - tp2_pct)
                                    sl_price = price * (1 + sl_pct)
                        except (ValueError, TypeError):
                            pass
                    
                    # Collect results
                    if len(trades) >= 10:
                        pnl_total = sum(trades)
                        wins = sum(1 for p in trades if p > 0)
                        win_rate = wins / len(trades)
                        total_wins = sum(max(p, 0) for p in trades)
                        total_loss = sum(abs(min(p, 0)) for p in trades)
                        pf = total_wins / total_loss if total_loss > 0 else 0
                        score = pnl_total * pf if pf > 0 else pnl_total
                        
                        results.append({
                            'RSI_L': rsi_long, 'RSI_S': rsi_short,
                            'TP2%': tp2_pct * 100, 'SL%': sl_pct * 100,
                            'EMA': 'Y' if use_ema else 'N',
                            'Trades': len(trades), 'P&L': pnl_total,
                            'WinRate%': win_rate * 100, 'PF': pf, 'Score': score
                        })
                    
                    if test_count % 60 == 0:
                        print(f"  Progress: {test_count}/360... ({len(results)} viable)")

# Sort by score
results = sorted(results, key=lambda x: x['Score'], reverse=True)

print("\n" + "="*150)
print("TOP 20 BEST COMBINATIONS")
print("="*150 + "\n")

if results:
    for i, r in enumerate(results[:20], 1):
        print(f"{i:2d}. RSI {r['RSI_L']}/{r['RSI_S']} | "
              f"TP2 {r['TP2%']:3.0f}% SL {r['SL%']:4.2f}% | EMA:{r['EMA']} | "
              f"T:{r['Trades']:2d} | P&L:${r['P&L']:+7.2f} | WR:{r['WinRate%']:5.1f}% | "
              f"PF:{r['PF']:.2f} | Score:{r['Score']:+8.2f}")
else:
    print("No viable combinations (need >=10 trades)")

print("\n" + "="*150)
print(f"TOTAL: {len(results)}/360 combinations viable")
print("="*150 + "\n")
