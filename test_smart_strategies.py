"""
SMART STRATEGY TESTING - QA Approach
Test different STRATEGIES, not just parameters
Goal: Find ONE working strategy
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*150)
print("SMART STRATEGY TESTING - Find ONE Working Strategy")
print("="*150)

print("\nDownloading data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Indicators
def rsi(s, p=14):
    d = s.diff()
    g = (d.where(d > 0, 0)).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - (100 / (1 + g / l))

def bb(s, p=20, std=2):
    m = s.rolling(p).mean()
    st = s.rolling(p).std()
    return m + st*std, m - st*std

def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

df['RSI'] = rsi(df['Close'])
df['BB_U'], df['BB_L'] = bb(df['Close'])
df['EMA12'] = ema(df['Close'], 12)
df['EMA26'] = ema(df['Close'], 26)
df['EMA200'] = ema(df['Close'], 200)
df['ATR'] = (df['High'] - df['Low']).rolling(14).mean()
df = df.dropna()

df['Session'] = df.index.map(lambda x: 'Active' if (0.5 <= x.hour + x.minute/60 < 4.5 or 
                                                      5.5 <= x.hour + x.minute/60 < 11.5 or
                                                      12.5 <= x.hour + x.minute/60 < 17.5) else 'Off')

def test_strategy(df, name, buy_logic, sell_logic, tp_pct=0.05, sl_pct=0.01):
    """Test a strategy"""
    trades = []
    in_trade = False
    entry = 0
    for _, row in df.iterrows():
        price = row['Close']
        
        if not in_trade and row['Session'] == 'Active':
            if buy_logic(row):
                in_trade = True
                entry = price
                tp = price * (1 + tp_pct)
                sl = price * (1 - sl_pct)
            elif sell_logic(row):
                in_trade = True
                entry = price
                tp = price * (1 - tp_pct)
                sl = price * (1 + sl_pct)
        elif in_trade:
            if 'tp' in locals() and (price >= tp or price <= sl):
                pnl = ((price - entry) if price >= tp else (sl - entry)) * 0.1 - 0.002
                trades.append(pnl)
                in_trade = False
            elif 'sl' in locals() and 'tp' in locals() and not ((price >= tp or price <= sl) if entry < price else (price <= tp or price >= sl)):
                pass
    
    if len(trades) == 0:
        return name, 0, 0, 0, 0, 0
    
    pnl = sum(trades)
    wr = sum(1 for t in trades if t > 0) / len(trades)
    wins = sum(max(t, 0) for t in trades)
    loss = sum(abs(min(t, 0)) for t in trades)
    pf = wins / loss if loss > 0 else 0
    
    return name, len(trades), pnl, wr*100, pf, pnl * pf

print("\nTesting different strategies:\n")

results = []

# STRATEGY 1: Original (Mar-Apr works)
def s1_buy(row):
    return row['RSI'] < 25 and row['Close'] <= row['BB_L']

def s1_sell(row):
    return row['RSI'] > 75 and row['Close'] >= row['BB_U']

r = test_strategy(df, "Strategy 1: RSI+BB (Original)", s1_buy, s1_sell, tp_pct=0.05, sl_pct=0.01)
results.append(r)

# STRATEGY 2: Trend Following (EMA12/26 Crossover)
df['Prev_EMA12'] = df['EMA12'].shift(1)
df['Prev_EMA26'] = df['EMA26'].shift(1)

def s2_buy(row):
    return row['Prev_EMA12'] <= row['Prev_EMA26'] and row['EMA12'] > row['EMA26']

def s2_sell(row):
    return row['Prev_EMA12'] >= row['Prev_EMA26'] and row['EMA12'] < row['EMA26']

r = test_strategy(df, "Strategy 2: EMA12/26 Trend", s2_buy, s2_sell, tp_pct=0.04, sl_pct=0.01)
results.append(r)

# STRATEGY 3: RSI Only (Simpler)
def s3_buy(row):
    return row['RSI'] < 30

def s3_sell(row):
    return row['RSI'] > 70

r = test_strategy(df, "Strategy 3: RSI Only (30/70)", s3_buy, s3_sell, tp_pct=0.04, sl_pct=0.012)
results.append(r)

# STRATEGY 4: Bollinger Bands Only
def s4_buy(row):
    return row['Close'] <= row['BB_L']

def s4_sell(row):
    return row['Close'] >= row['BB_U']

r = test_strategy(df, "Strategy 4: BB Only", s4_buy, s4_sell, tp_pct=0.03, sl_pct=0.015)
results.append(r)

# STRATEGY 5: RSI + EMA200 Filter
def s5_buy(row):
    return row['RSI'] < 25 and row['Close'] > row['EMA200']

def s5_sell(row):
    return row['RSI'] > 75 and row['Close'] < row['EMA200']

r = test_strategy(df, "Strategy 5: RSI+EMA200", s5_buy, s5_sell, tp_pct=0.05, sl_pct=0.01)
results.append(r)

# STRATEGY 6: April Only (Known Profitable)
df_april = df[df.index.month == 4].copy()
print("Testing April 2026 only (known profitable period):\n")

def s6_buy(row):
    return row['RSI'] < 25 and row['Close'] <= row['BB_L']

def s6_sell(row):
    return row['RSI'] > 75 and row['Close'] >= row['BB_U']

r = test_strategy(df_april, "Strategy 6: RSI+BB April", s6_buy, s6_sell, tp_pct=0.05, sl_pct=0.01)
results.append(r)

# Display Results
print("\n" + "="*150)
print("STRATEGY COMPARISON")
print("="*150 + "\n")
print(f"{'Strategy':<35} {'Trades':>6} {'P&L':>10} {'WR%':>7} {'PF':>6} {'Score':>10}")
print("-" * 150)

for name, trades, pnl, wr, pf, score in sorted(results, key=lambda x: x[5], reverse=True):
    if trades > 0:
        print(f"{name:<35} {trades:6d} ${pnl:+9.2f} {wr:6.1f}% {pf:6.2f} {score:+10.2f}")
    else:
        print(f"{name:<35} {'N/A':>6} {'N/A':>10} {'N/A':>7} {'N/A':>6} {'N/A':>10}")

print("\n" + "="*150)
print("RECOMMENDATION: Pick the highest positive score strategy above")
print("="*150 + "\n")
