"""
Backtest: LONG + SHORT with 200 EMA Trend Filter (March-April 2026)
Simplified version with better debugging
"""

import pandas as pd
import numpy as np
import yfinance as yf
import csv

START_DATE = "2026-03-01"
END_DATE = "2026-04-10"
LOT_SIZE = 0.10
STARTING_CAPITAL = 500

print("=" * 100)
print("📊 BACKTEST: LONG + SHORT with 200 EMA Trend Filter")
print(f"📅 Period: {START_DATE} to {END_DATE}")
print("=" * 100)

# Download data
df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
print(f"📥 Downloaded {len(df)} bars\n")

# Calculate indicators
df['RSI'] = df['Close'].rolling(14).apply(lambda x: 100 - 100/(1 + np.sum(np.maximum(x.diff(), 0)) / np.abs(np.sum(np.minimum(x.diff(), 0)))) if len(x) > 1 else None)
df['EMA200'] = df['Close'].ewm(span=200).mean()
df['BB_Mid'] = df['Close'].rolling(20).mean()
df['BB_Std'] = df['Close'].rolling(20).std()
df['BB_Upper'] = df['BB_Mid'] + (2.0 * df['BB_Std'])
df['BB_Lower'] = df['BB_Mid'] - (2.0 * df['BB_Std'])

df = df.dropna()
print(f"✅ After indicators: {len(df)} bars\n")

trades = []
open_trade = None
capital = STARTING_CAPITAL
tp1_hit = False

# Main loop
for idx in range(len(df)):
    row = df.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema200 = float(row['EMA200'])
    bb_upper = float(row['BB_Upper'])
    bb_lower = float(row['BB_Lower'])
    timestamp = df.index[idx]
    
    trend = "UPTREND" if price > ema200 else "DOWNTREND"
    
    # Check signals
    long_signal = (price > ema200 and rsi < 25 and price < bb_lower)
    short_signal = (price < ema200 and rsi > 75 and price > bb_upper)
    
    # Process open trade
    if open_trade:
        if open_trade['type'] == 'LONG':
            # TP2 exit
            if price >= open_trade['tp2']:
                exit_price = open_trade['tp2']
                pnl = (exit_price - open_trade['price_in']) * LOT_SIZE
                capital += pnl
                trades.append({
                    'Entry': open_trade['date_in'],
                    'Type': 'LONG',
                    'Price_In': f"{open_trade['price_in']:.2f}",
                    'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                    'Price_Out': f"{exit_price:.2f}",
                    'Status': 'TP2',
                    'P&L': f"{pnl:.2f}",
                    'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                })
                print(f"✅ LONG TP2 Exit  @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                open_trade = None
                tp1_hit = False
            
            # TP1 trail start
            elif price >= open_trade['tp1'] and not tp1_hit:
                tp1_hit = True
                open_trade['sl'] = price * 0.99
            
            # TP1 trailing SL
            elif tp1_hit:
                open_trade['sl'] = max(open_trade['sl'], price * 0.99)
                if price <= open_trade['sl']:
                    exit_price = open_trade['sl']
                    pnl = (exit_price - open_trade['price_in']) * LOT_SIZE
                    capital += pnl
                    trades.append({
                        'Entry': open_trade['date_in'],
                        'Type': 'LONG',
                        'Price_In': f"{open_trade['price_in']:.2f}",
                        'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                        'Price_Out': f"{exit_price:.2f}",
                        'Status': 'TP1_TRAIL',
                        'P&L': f"{pnl:.2f}",
                        'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                    })
                    print(f"📉 LONG TP1TRAIL Exit @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                    open_trade = None
                    tp1_hit = False
            
            # Hard SL
            elif price <= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl = (exit_price - open_trade['price_in']) * LOT_SIZE
                capital += pnl
                trades.append({
                    'Entry': open_trade['date_in'],
                    'Type': 'LONG',
                    'Price_In': f"{open_trade['price_in']:.2f}",
                    'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                    'Price_Out': f"{exit_price:.2f}",
                    'Status': 'SL',
                    'P&L': f"{pnl:.2f}",
                    'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                })
                print(f"❌ LONG SL Hit    @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                open_trade = None
                tp1_hit = False
        
        elif open_trade['type'] == 'SHORT':
            # TP2 exit
            if price <= open_trade['tp2']:
                exit_price = open_trade['tp2']
                pnl = (open_trade['price_in'] - exit_price) * LOT_SIZE
                capital += pnl
                trades.append({
                    'Entry': open_trade['date_in'],
                    'Type': 'SHORT',
                    'Price_In': f"{open_trade['price_in']:.2f}",
                    'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                    'Price_Out': f"{exit_price:.2f}",
                    'Status': 'TP2',
                    'P&L': f"{pnl:.2f}",
                    'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                })
                print(f"✅ SHORT TP2 Exit @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                open_trade = None
                tp1_hit = False
            
            # TP1 trail start
            elif price <= open_trade['tp1'] and not tp1_hit:
                tp1_hit = True
                open_trade['sl'] = price * 1.01
            
            # TP1 trailing SL
            elif tp1_hit:
                open_trade['sl'] = min(open_trade['sl'], price * 1.01)
                if price >= open_trade['sl']:
                    exit_price = open_trade['sl']
                    pnl = (open_trade['price_in'] - exit_price) * LOT_SIZE
                    capital += pnl
                    trades.append({
                        'Entry': open_trade['date_in'],
                        'Type': 'SHORT',
                        'Price_In': f"{open_trade['price_in']:.2f}",
                        'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                        'Price_Out': f"{exit_price:.2f}",
                        'Status': 'TP1_TRAIL',
                        'P&L': f"{pnl:.2f}",
                        'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                    })
                    print(f"📈 SHORT TP1TRAIL Exit @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                    open_trade = None
                    tp1_hit = False
            
            # Hard SL
            elif price >= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl = (open_trade['price_in'] - exit_price) * LOT_SIZE
                capital += pnl
                trades.append({
                    'Entry': open_trade['date_in'],
                    'Type': 'SHORT',
                    'Price_In': f"{open_trade['price_in']:.2f}",
                    'Exit': timestamp.strftime("%Y-%m-%d %H:%M"),
                    'Price_Out': f"{exit_price:.2f}",
                    'Status': 'SL',
                    'P&L': f"{pnl:.2f}",
                    'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
                })
                print(f"❌ SHORT SL Hit   @ ${exit_price:,.0f} | P&L: ${pnl:+7.2f} | Capital: ${capital:,.2f}")
                open_trade = None
                tp1_hit = False
    
    # Entry logic
    if not open_trade:
        if long_signal:
            entry_price = price
            tp1 = entry_price * 1.015
            tp2 = entry_price * 1.035
            sl = entry_price * 0.99
            open_trade = {
                'type': 'LONG',
                'date_in': timestamp.strftime("%Y-%m-%d %H:%M"),
                'price_in': entry_price,
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl
            }
            print(f"🟢 LONG Entry    @ ${entry_price:,.0f} | RSI:{rsi:5.1f} | {trend:9} | TP1:${tp1:,.0f} TP2:${tp2:,.0f}")
        
        elif short_signal:
            entry_price = price
            tp1 = entry_price * 0.985
            tp2 = entry_price * 0.965
            sl = entry_price * 1.01
            open_trade = {
                'type': 'SHORT',
                'date_in': timestamp.strftime("%Y-%m-%d %H:%M"),
                'price_in': entry_price,
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl
            }
            print(f"🔴 SHORT Entry   @ ${entry_price:,.0f} | RSI:{rsi:5.1f} | {trend:9} | TP1:${tp1:,.0f} TP2:${tp2:,.0f}")

# Close open position
if open_trade:
    final_price = df.iloc[-1]['Close']
    if open_trade['type'] == 'LONG':
        pnl = (final_price - open_trade['price_in']) * LOT_SIZE
    else:
        pnl = (open_trade['price_in'] - final_price) * LOT_SIZE
    capital += pnl
    trades.append({
        'Entry': open_trade['date_in'],
        'Type': open_trade['type'],
        'Price_In': f"{open_trade['price_in']:.2f}",
        'Exit': df.index[-1].strftime("%Y-%m-%d %H:%M"),
        'Price_Out': f"{final_price:.2f}",
        'Status': 'CLOSED_END',
        'P&L': f"{pnl:.2f}",
        'P&L%': f"{(pnl/open_trade['price_in']/LOT_SIZE)*100:.2f}",
    })

# Results
print("\n" + "=" * 100)
print("📊 RESULTS")
print("=" * 100)

total_trades = len(trades)
winning = sum(1 for t in trades if float(t['P&L']) > 0)
losing = total_trades - winning
win_rate = (winning / total_trades * 100) if total_trades > 0 else 0

long_trades = sum(1 for t in trades if t['Type'] == 'LONG')
short_trades = sum(1 for t in trades if t['Type'] == 'SHORT')

total_pnl = capital - STARTING_CAPITAL
return_pct = (total_pnl / STARTING_CAPITAL * 100)

print(f"\n📈 Trade Summary:")
print(f"   Total: {total_trades} trades ({long_trades} LONG, {short_trades} SHORT)")
print(f"   Wins: {winning} | Losses: {losing} | Win Rate: {win_rate:.1f}%")

print(f"\n💰 Capital Summary:")
print(f"   Start: ${STARTING_CAPITAL:,.2f}")
print(f"   End: ${capital:,.2f}")
print(f"   P&L: ${total_pnl:,.2f}")
print(f"   Return: {return_pct:.2f}%")

# Save to CSV
if trades:
    output_file = "backtest_long_short_200ema_march_apr.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
    print(f"\n📁 Results saved to: {output_file}")
    
    print(f"\n📋 All Trades:")
    for i, t in enumerate(trades, 1):
        print(f"   {i}. {t['Type']:5} @ ${t['Price_In']:>8} → ${t['Price_Out']:>8} | {t['Status']:11} | ${t['P&L']:>8}")
