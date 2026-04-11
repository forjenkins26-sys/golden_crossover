"""
FAST PARAMETER OPTIMIZATION - Pre-calculated Indicators
Tests 360 parameter combinations quickly on pre-loaded data
"""

import pandas as pd
import numpy as np
import yfinance as yf

# ============================================================================
# INDICATORS
# ============================================================================

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

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def get_session(timestamp):
    hour_utc = timestamp.hour + timestamp.minute / 60.0
    if 0.5 <= hour_utc < 4.5:
        return "Asian"
    elif 5.5 <= hour_utc < 11.5:
        return "London"
    elif 12.5 <= hour_utc < 17.5:
        return "NewYork"
    else:
        return "Off"

# ============================================================================
# FAST BACKTEST (using pre-calculated indicators)
# ============================================================================

def fast_backtest(data, rsi_long, rsi_short, tp2_pct, sl_pct, use_ema):
    """Fast backtest using pre-calculated indicators"""
    trades = []
    open_trade = None
    
    for idx in range(len(data)):
        row = data.iloc[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        ema_200 = float(row['EMA_200'])
        
        # Exit
        if open_trade:
            if open_trade['type'] == 'LONG':
                if price >= open_trade['tp2'] or price <= open_trade['sl']:
                    pnl = (price - open_trade['entry']) * 0.1 if price >= open_trade['tp2'] else (open_trade['sl'] - open_trade['entry']) * 0.1
                    pnl -= 0.002  # approx fees
                    trades.append(pnl)
                    open_trade = None
            else:  # SHORT
                if price <= open_trade['tp2'] or price >= open_trade['sl']:
                    pnl = (open_trade['entry'] - price) * 0.1 if price <= open_trade['tp2'] else (open_trade['entry'] - open_trade['sl']) * 0.1
                    pnl -= 0.002  # approx fees
                    trades.append(pnl)
                    open_trade = None
        
        # Entry
        if not open_trade and get_session(row.name) != "Off":
            # LONG
            long_cond = (rsi < rsi_long and price <= bb_lower)
            if use_ema:
                long_cond = long_cond and (price > ema_200)
            
            if long_cond:
                open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp2': price * (1 + tp2_pct),
                    'sl': price * (1 - sl_pct)
                }
            
            # SHORT
            short_cond = (rsi > rsi_short and price >= bb_upper)
            if use_ema:
                short_cond = short_cond and (price < ema_200)
            
            if short_cond:
                open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp2': price * (1 - tp2_pct),
                    'sl': price * (1 + sl_pct)
                }
    
    if len(trades) == 0:
        return 0, 0, 0, 0
    
    pnl_total = sum(trades)
    wins = sum(1 for p in trades if p > 0)
    win_rate = wins / len(trades)
    total_wins = sum(p for p in trades if p > 0)
    total_loss = abs(sum(p for p in trades if p < 0))
    pf = total_wins / total_loss if total_loss > 0 else 0
    
    return pnl_total, len(trades), win_rate, pf

# ============================================================================
# MAIN
# ============================================================================

print("\n" + "="*150)
print("FAST PARAMETER OPTIMIZATION")
print("="*150)

# Download once
print("\nDownloading data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Pre-calculate ALL indicators ONCE
print("Pre-calculating indicators...")
df['RSI'] = calculate_rsi(df['Close'])
df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
df['EMA_200'] = calculate_ema(df['Close'], 200)
df = df.dropna()

print(f"Ready. Testing {3 * 3 * 4 * 5 * 2} combinations...\n")

results = []

# Test all combinations
for rsi_long in [20, 25, 30]:
    for rsi_short in [70, 75, 80]:
        for tp2_pct in [0.03, 0.04, 0.05, 0.06]:
            for sl_pct in [0.005, 0.008, 0.01, 0.015, 0.02]:
                for use_ema in [True, False]:
                    pnl, trades, wr, pf = fast_backtest(df, rsi_long, rsi_short, tp2_pct, sl_pct, use_ema)
                    
                    if trades >= 10:  # Only store viable combos
                        score = pnl * pf if pf > 0 else pnl
                        results.append({
                            'RSI_L': rsi_long,
                            'RSI_S': rsi_short,
                            'TP2%': tp2_pct * 100,
                            'SL%': sl_pct * 100,
                            'EMA': 'Y' if use_ema else 'N',
                            'Trades': trades,
                            'P&L': pnl,
                            'WinRate%': wr * 100,
                            'PF': pf,
                            'Score': score
                        })

# Sort by score
results = sorted(results, key=lambda x: x['Score'], reverse=True)

print("\n" + "="*150)
print("TOP 20 BEST COMBINATIONS")
print("="*150 + "\n")

for i, r in enumerate(results[:20]):
    print(f"{i+1:2d}. RSI {r['RSI_L']}/{r['RSI_S']} | TP2 {r['TP2%']:.0f}% SL {r['SL%']:.2f}% | EMA:{r['EMA']} | "
          f"Trades:{r['Trades']:2d} | P&L:${r['P&L']:+6.2f} | WR:{r['WinRate%']:5.1f}% | PF:{r['PF']:.2f} | Score:{r['Score']:+8.2f}")

print("\n" + "="*150)
print("CONCLUSION")
print("="*150)

if results:
    best = results[0]
    print(f"""
🏆 BEST STRATEGY FOUND:

Parameters:
  • RSI Thresholds: LONG < {best['RSI_L']}, SHORT > {best['RSI_S']}
  • Take Profit: {best['TP2%']:.0f}%
  • Stop Loss: {best['SL%']:.2f}%
  • 200 EMA Filter: {'YES' if best['EMA'] == 'Y' else 'NO'}

Performance:
  • Trades: {best['Trades']}
  • P&L: ${best['P&L']:+.2f}
  • Win Rate: {best['WinRate%']:.1f}%
  • Profit Factor: {best['PF']:.2f}
  • Composite Score: {best['Score']:.2f}

{'✓ VIABLE' if best['P&L'] > 0 and best['WinRate%'] > 25 else '✗ NOT VIABLE'}
""")
