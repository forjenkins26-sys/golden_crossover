"""
PARAMETER OPTIMIZATION - Final Version
Shows top combinations regardless of trade count
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*150)
print("FINAL PARAMETER OPTIMIZATION - All 360 Combinations")
print("="*150)

print("\nDownloading data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

print("Calculating indicators...")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(series, period=20, num_std=2.0):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    return sma + (std * num_std), sma - (std * num_std)

df['RSI'] = calculate_rsi(df['Close'])
df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
df['IsAsian'] = df.index.map(lambda x: 0.5 <= (x.hour + x.minute/60) < 4.5)
df['IsLondon'] = df.index.map(lambda x: 5.5 <= (x.hour + x.minute/60) < 11.5)
df['IsNYork'] = df.index.map(lambda x: 12.5 <= (x.hour + x.minute/60) < 17.5)
df['InSession'] = df['IsAsian'] | df['IsLondon'] | df['IsNYork']
df = df.dropna()

print(f"Loaded {len(df)} bars\nTesting {3 * 3 * 4 * 5 * 2} combinations:\n")

results = []
combo_num = 0

for rsi_long in [20, 25, 30]:
    for rsi_short in [70, 75, 80]:
        for tp2_pct in [0.03, 0.04, 0.05, 0.06]:
            for sl_pct in [0.005, 0.008, 0.01, 0.015, 0.02]:
                for use_ema in [True, False]:
                    combo_num += 1
                    
                    # Backtest this combination
                    trades = []
                    in_trade = False
                    trade_return = 0
                    entry_price = 0
                    tp_price = 0
                    sl_price = 0
                    trade_type = None
                    
                    for idx, row in df.iterrows():
                        price = float(row['Close'])
                        rsi = float(row['RSI'])
                        bb_upper = float(row['BB_Upper'])
                        bb_lower = float(row['BB_Lower'])
                        ema_200 = float(row['EMA_200'])
                        in_session = row['InSession'].item() if hasattr(row['InSession'], 'item') else row['InSession']
                        
                        # Exit
                        if in_trade:
                            if trade_type == 'L' and (price >= tp_price or price <= sl_price):
                                actual_price = tp_price if price >= tp_price else sl_price
                                trades.append((actual_price - entry_price) * 0.1 - 0.002)
                                in_trade = False
                            elif trade_type == 'S' and (price <= tp_price or price >= sl_price):
                                actual_price = tp_price if price <= tp_price else sl_price
                                trades.append((entry_price - actual_price) * 0.1 - 0.002)
                                in_trade = False
                        
                        # Entry
                        if not in_trade and in_session:
                            # LONG
                            if rsi < rsi_long and price <= bb_lower:
                                if not use_ema or price > ema_200:
                                    in_trade = True
                                    trade_type = 'L'
                                    entry_price = price
                                    tp_price = price * (1 + tp2_pct)
                                    sl_price = price * (1 - sl_pct)
                            # SHORT
                            elif rsi > rsi_short and price >= bb_upper:
                                if not use_ema or price < ema_200:
                                    in_trade = True
                                    trade_type = 'S'
                                    entry_price = price
                                    tp_price = price * (1 - tp2_pct)
                                    sl_price = price * (1 + sl_pct)
                    
                    # Store results for all combos
                    if len(trades) > 0:
                        pnl = sum(trades)
                        wr = sum(1 for t in trades if t > 0) / len(trades)
                        wins = sum(max(t, 0) for t in trades)
                        loss = sum(abs(min(t, 0)) for t in trades)
                        pf = wins / loss if loss > 0 else float('inf')
                        score = pnl * pf if pf != float('inf') else pnl
                        
                        results.append({
                            'RSI': f"{rsi_long}/{rsi_short}",
                            'TP%': f"{tp2_pct*100:.0f}",
                            'SL%': f"{sl_pct*100:.2f}",
                            'EMA': 'Y' if use_ema else 'N',
                            'Trades': len(trades),
                            'P&L': pnl,
                            'WR%': wr * 100,
                            'PF': pf if pf != float('inf') else 999,
                            'Score': score
                        })
                    
                    if combo_num % 60 == 0:
                        print(f"  {combo_num:3d}/360 done... ({len(results)} with trades)")

# Sort and display top 20
results = sorted(results, key=lambda x: x['Score'], reverse=True)

print("\n" + "="*150)
print("TOP 20 RESULTS")
print("="*150 + "\n")

for i, r in enumerate(results[:20], 1):
    print(f"{i:2d}. RSI:{r['RSI']:7} TP%:{r['TP%']:4} SL%:{r['SL%']:5} EMA:{r['EMA']} | "
          f"Trades:{r['Trades']:2} P&L:${r['P&L']:+7.2f} WR:{r['WR%']:5.1f}% PF:{r['PF']:6.2f} "
          f"Score:{r['Score']:+8.2f}")

print("\n" + "="*150)
print(f"Total: {len(results)}/360 combinations generated trades")
if len(results) == 0:
    print("WARNING: No combinations generated trades! Check session filtering or parameters.")
print("="*150 + "\n")
