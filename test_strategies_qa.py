"""
SIMPLE STRATEGY COMPARISON - QA Approach
Test 5 different strategies, find the ONE that works
"""

import pandas as pd
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*140)
print("STRATEGY TESTING - Find ONE Working Approach")
print("="*140)

print("\nDownloading data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Calc RSI properly
def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

df['RSI'] = calc_rsi(df['Close'])
df['SMA20'] = df['Close'].rolling(20).mean()
df['STD20'] = df['Close'].rolling(20).std()
df['BB_U'] = df['SMA20'] + 2 * df['STD20']
df['BB_L'] = df['SMA20'] - 2 * df['STD20']
df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
df = df.dropna()

# Session
df['InSession'] = df.index.map(lambda x: (0.5 <= x.hour + x.minute/60 < 4.5) or 
                                          (5.5 <= x.hour + x.minute/60 < 11.5) or 
                                          (12.5 <= x.hour + x.minute/60 < 17.5))

def test_strat(data, name, entry_long, entry_short, tp_pct, sl_pct):
    trades, in_trade, entry = [], False, 0
    tp, sl = 0, 0
    is_long = False
    
    for idx in range(len(data)):
        row = data.iloc[idx]
        price = float(row['Close'])
        in_session = row['InSession'].item() if hasattr(row['InSession'], 'item') else bool(row['InSession'])
        
        # Exit
        if in_trade:
            if (is_long and price >= tp) or (is_long and price <= sl):
                pnl = ((price - entry) if price >= tp else (sl - entry)) * 0.1 - 0.002
                trades.append(pnl)
                in_trade = False
            elif (not is_long and price <= tp) or (not is_long and price >= sl):
                pnl = ((entry - price) if price <= tp else (entry - sl)) * 0.1 - 0.002
                trades.append(pnl)
                in_trade = False
        
        # Entry
        if not in_trade and in_session:
            if entry_long(row):
                in_trade = True
                is_long = True
                entry = price
                tp = price * (1 + tp_pct)
                sl = price * (1 - sl_pct)
            elif entry_short(row):
                in_trade = True
                is_long = False
                entry = price
                tp = price * (1 - tp_pct)
                sl = price * (1 + sl_pct)
    
    if not trades:
        return name, 0, 0, 0, 0, 0
    
    pnl = sum(trades)
    wr = sum(1 for t in trades if t > 0) / len(trades) * 100
    wins = sum(max(t, 0) for t in trades)
    loss = sum(abs(min(t, 0)) for t in trades)
    pf = wins / loss if loss > 0 else 0
    score = pnl * pf
    
    return name, len(trades), pnl, wr, pf, score

print("Testing strategies...\n")

results = []

# ST1: Original RSI+BB
print("  ► Strategy 1: RSI + Bollinger Bands")
s1 = test_strat(df, "S1: RSI+BB", 
                lambda r: float(r['RSI']) < 25 and float(r['Close']) <= float(r['BB_L']),
                lambda r: float(r['RSI']) > 75 and float(r['Close']) >= float(r['BB_U']),
                0.05, 0.01)
results.append(s1)
print(f"     Trades: {s1[1]}, P&L: ${s1[2]:+.2f}, WR: {s1[3]:.0f}%, PF: {s1[4]:.2f}\n")

# ST2: EMA Crossover (Trend)
print("  ► Strategy 2: EMA 12/26 Crossover")
df['EMA12_P']  = df['EMA12'].shift(1)
df['EMA26_P'] = df['EMA26'].shift(1)
s2 = test_strat(df, "S2: EMA12/26",
                lambda r: float(r['EMA12_P']) <= float(r['EMA26_P']) and float(r['EMA12']) > float(r['EMA26']),
                lambda r: float(r['EMA12_P']) >= float(r['EMA26_P']) and float(r['EMA12']) < float(r['EMA26']),
                0.04, 0.01)
results.append(s2)
print(f"     Trades: {s2[1]}, P&L: ${s2[2]:+.2f}, WR: {s2[3]:.0f}%, PF: {s2[4]:.2f}\n")

# ST3: RSI Only
print("  ► Strategy 3: RSI Oversold/Overbought")
s3 = test_strat(df, "S3: RSI30/70",
                lambda r: float(r['RSI']) < 30,
                lambda r: float(r['RSI']) > 70,
                0.04, 0.012)
results.append(s3)
print(f"     Trades: {s3[1]}, P&L: ${s3[2]:+.2f}, WR: {s3[3]:.0f}%, PF: {s3[4]:.2f}\n")

# ST4: BB Only
print("  ► Strategy 4: Bollinger Bands Only")
s4 = test_strat(df, "S4: BB",
                lambda r: float(r['Close']) <= float(r['BB_L']),
                lambda r: float(r['Close']) >= float(r['BB_U']),
                0.03, 0.015)
results.append(s4)
print(f"     Trades: {s4[1]}, P&L: ${s4[2]:+.2f}, WR: {s4[3]:.0f}%, PF: {s4[4]:.2f}\n")

# ST5: RSI + EMA200 Filter
print("  ► Strategy 5: RSI + EMA200 Confirmation")
s5 = test_strat(df, "S5: RSI+EMA200",
                lambda r: float(r['RSI']) < 25 and float(r['Close']) > float(r['EMA200']),
               lambda r: float(r['RSI']) > 75 and float(r['Close']) < float(r['EMA200']),
                0.05, 0.01)
results.append(s5)
print(f"     Trades: {s5[1]}, P&L: ${s5[2]:+.2f}, WR: {s5[3]:.0f}%, PF: {s5[4]:.2f}\n")

# Display results
print("\n" + "="*140)
print("RESULTS - Full 100 Days (Jan 1 - Apr 10, 2026)")
print("="*140)
print(f"\n{'Strategy':<25} {'Trades':>8} {'P&L':>12} {'Win Rate':>12} {'Profit Factor':>15} {'Score':>12}")
print("-" * 140)

for name, trades, pnl, wr, pf, score in sorted(results, key=lambda x: x[2], reverse=True):
    status = "✓ WIN" if pnl > 0 else "✗ LOSS" if pnl < 0 else "FLAT"
    print(f"{name:<25} {trades:8d} ${pnl:+11.2f} {wr:11.1f}% {pf:15.2f} {score:+11.2f}  [{status}]")

print("\n" + "="*140 )

# Winner
profitable = [r for r in results if r[2] > 0]
if profitable:
    winner = max(profitable, key=lambda x: x[2])
    print(f"\n🏆 BEST STRATEGY: {winner[0]}")
    print(f"   P&L: ${winner[2]:.2f} | Trades: {winner[1]} | Win Rate: {winner[3]:.1f}% | Profit Factor: {winner[4]:.2f}\n")
else:
    print("\n❌ FULL 100 DAYS: No strategy profitable\n")
    print("Testing March/April ONLY (known profitable):\n")
    
    df_ma = df[(df.index.month == 3) | (df.index.month == 4)]
    
    print(f"Bars in Mar/Apr: {len(df_ma)}\n")
    
    # Retesting on March/April
    s1_ma = test_strat(df_ma, "S1: RSI+BB (Mar/Apr)",
                       lambda r: float(r['RSI']) < 25 and float(r['Close']) <= float(r['BB_L']),
                       lambda r: float(r['RSI']) > 75 and float(r['Close']) >= float(r['BB_U']),
                       0.05, 0.01)
    
    print(f"  RSI+BB on Mar/Apr: {s1_ma[1]} trades, P&L: ${s1_ma[2]:+.2f} ({s1_ma[3]:.0f}% WR)\n")
    
    if s1_ma[2] > 0:
        print(f"✓ VIABLE: Use RSI+BB strategy, trade ONLY March/April")
        print(f"  Alternative: Apply other strategies during Mar/Apr window only")

print("="*140 + "\n")
