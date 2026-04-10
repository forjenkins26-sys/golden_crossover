"""
FINAL Bidirectional Strategy: LONG + SHORT with RSI + Bollinger Bands
March 1 - April 10, 2026 Backtest
FIXES: Flat Lot Only + Corrected Session Detection + Accurate Timing
"""

import pandas as pd
import numpy as np
import yfinance as yf
import csv
from datetime import datetime

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(series, period=14):
    """Calculate RSI(14)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=20, num_std=2.0):
    """Calculate Bollinger Bands"""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower

# ============================================================================
# SESSION FILTERING - FIXED
# ============================================================================

def get_session(timestamp):
    """Get current session based on IST time (UTC + 5:30)
    FIXED: Use decimal hours for proper comparison
    """
    # Convert UTC timestamp to decimal hour
    hour_utc = timestamp.hour
    minute_utc = timestamp.minute
    hour_decimal = hour_utc + (minute_utc / 60.0)
    
    # IST = UTC + 5:30, but we check UTC times:
    # Asian (06:00-10:00 IST) = 00:30-04:30 UTC
    # London (11:00-17:00 IST) = 05:30-11:30 UTC  
    # NewYork (18:00-23:00 IST) = 12:30-17:30 UTC
    
    if 0.5 <= hour_decimal < 4.5:
        return "Asian"
    elif 5.5 <= hour_decimal < 11.5:
        return "London"
    elif 12.5 <= hour_decimal < 17.5:
        return "NewYork"
    else:
        return "Off-Session"

# ============================================================================
# CONFIG
# ============================================================================

START_DATE = "2026-03-01"
END_DATE = "2026-04-10"
LOT_SIZE = 0.10
STARTING_CAPITAL = 500

RSI_PERIOD = 14
RSI_LONG = 25
RSI_SHORT = 75
BB_PERIOD = 20
BB_STD = 2.0

TP1_LONG = 0.015
TP2_LONG = 0.05
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.05
SL_SHORT = 0.01

TRAIL_PCT = 0.01

# ============================================================================
# MAIN BACKTEST
# ============================================================================

print("=" * 150)
print("FINAL BACKTEST: March 1 - April 10, 2026")
print("Flat Lot Sizing (0.10 BTC) + Fixed Session Detection")
print("=" * 150)

# Download data
print(f"\nDownloading BTC 1-hour data ({START_DATE} to {END_DATE})...\n")
df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
print(f"Loaded {len(df)} 1-hour bars\n")

# Calculate indicators
df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)
df = df.dropna()

trades = []
open_trade = None
total_capital = STARTING_CAPITAL

# Main loop
print("Running backtest...\n")
for idx in range(len(df)):
    row = df.iloc[idx]
    timestamp = df.index[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    bb_upper = float(row['BB_Upper'])
    bb_lower = float(row['BB_Lower'])
    
    session = get_session(timestamp)
    session_active = session != "Off-Session"
    
    # Check exit for open trade
    if open_trade:
        if open_trade['type'] == 'LONG':
            # TP2 exit
            if price >= open_trade['tp2']:
                exit_price = open_trade['tp2']
                pnl = (exit_price - open_trade['entry']) * LOT_SIZE
                total_capital += pnl
                
                trades.append({
                    'Direction': 'LONG',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                    'Flat_P&L': f"${pnl:+.2f}",
                    'Status': 'TP2',
                    'Session_In': open_trade['session']
                })
                print(f"[{timestamp}] LONG TP2  @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                open_trade = None
            
            # TP1 trailing stop
            elif price >= open_trade['tp1']:
                if 'trail_sl' not in open_trade:
                    open_trade['trail_sl'] = price * (1 - TRAIL_PCT)
                else:
                    open_trade['trail_sl'] = max(open_trade['trail_sl'], price * (1 - TRAIL_PCT))
                
                if price <= open_trade['trail_sl']:
                    exit_price = open_trade['trail_sl']
                    pnl = (exit_price - open_trade['entry']) * LOT_SIZE
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'LONG',
                        'Flat_Lots': f"{LOT_SIZE:.2f}",
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"${open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"${exit_price:.2f}",
                        'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                        'Flat_P&L': f"${pnl:+.2f}",
                        'Status': 'TP1_Trail',
                        'Session_In': open_trade['session']
                    })
                    print(f"[{timestamp}] LONG TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                    open_trade = None
            
            # Hard SL
            elif price <= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl = (exit_price - open_trade['entry']) * LOT_SIZE
                total_capital += pnl
                
                trades.append({
                    'Direction': 'LONG',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                    'Flat_P&L': f"${pnl:+.2f}",
                    'Status': 'SL',
                    'Session_In': open_trade['session']
                })
                print(f"[{timestamp}] LONG SL   @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                open_trade = None
        
        elif open_trade['type'] == 'SHORT':
            # TP2 exit
            if price <= open_trade['tp2']:
                exit_price = open_trade['tp2']
                pnl = (open_trade['entry'] - exit_price) * LOT_SIZE
                total_capital += pnl
                
                trades.append({
                    'Direction': 'SHORT',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                    'Flat_P&L': f"${pnl:+.2f}",
                    'Status': 'TP2',
                    'Session_In': open_trade['session']
                })
                print(f"[{timestamp}] SHORT TP2 @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                open_trade = None
            
            # TP1 trailing stop
            elif price <= open_trade['tp1']:
                if 'trail_sl' not in open_trade:
                    open_trade['trail_sl'] = price * (1 + TRAIL_PCT)
                else:
                    open_trade['trail_sl'] = min(open_trade['trail_sl'], price * (1 + TRAIL_PCT))
                
                if price >= open_trade['trail_sl']:
                    exit_price = open_trade['trail_sl']
                    pnl = (open_trade['entry'] - exit_price) * LOT_SIZE
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'SHORT',
                        'Flat_Lots': f"{LOT_SIZE:.2f}",
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"${open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"${exit_price:.2f}",
                        'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                        'Flat_P&L': f"${pnl:+.2f}",
                        'Status': 'TP1_Trail',
                        'Session_In': open_trade['session']
                    })
                    print(f"[{timestamp}] SHORT TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                    open_trade = None
            
            # Hard SL
            elif price >= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl = (open_trade['entry'] - exit_price) * LOT_SIZE
                total_capital += pnl
                
                trades.append({
                    'Direction': 'SHORT',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                    'Flat_P&L': f"${pnl:+.2f}",
                    'Status': 'SL',
                    'Session_In': open_trade['session']
                })
                print(f"[{timestamp}] SHORT SL  @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${total_capital:,.2f}")
                open_trade = None
    
    # Entry signals (ONLY in active sessions)
    if not open_trade and session_active and rsi is not None:
        # LONG: RSI < 25 + Price < Lower BB
        if rsi < RSI_LONG and price < bb_lower:
            tp1 = price * (1 + TP1_LONG)
            tp2 = price * (1 + TP2_LONG)
            sl = price * (1 - SL_LONG)
            open_trade = {
                'type': 'LONG',
                'entry': price,
                'date_in': timestamp.strftime('%Y-%m-%d'),
                'time_in': timestamp.strftime('%H:%M'),
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl,
                'session': session
            }
            print(f"[{timestamp}] LONG ENTRY  @ ${price:,.0f} | RSI:{rsi:5.1f} | Session: {session}")
        
        # SHORT: RSI > 75 + Price > Upper BB
        elif rsi > RSI_SHORT and price > bb_upper:
            tp1 = price * (1 - TP1_SHORT)
            tp2 = price * (1 - TP2_SHORT)
            sl = price * (1 + SL_SHORT)
            open_trade = {
                'type': 'SHORT',
                'entry': price,
                'date_in': timestamp.strftime('%Y-%m-%d'),
                'time_in': timestamp.strftime('%H:%M'),
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl,
                'session': session
            }
            print(f"[{timestamp}] SHORT ENTRY @ ${price:,.0f} | RSI:{rsi:5.1f} | Session: {session}")

# Results
print("\n" + "=" * 150)
print("BACKTEST RESULTS - FLAT LOT SIZING ONLY")
print("=" * 150)

total_trades = len(trades)
winning = sum(1 for t in trades if '$+' in t['Flat_P&L'])
losing = total_trades - winning
win_rate = (winning / total_trades * 100) if total_trades > 0 else 0

long_trades = sum(1 for t in trades if t['Direction'] == 'LONG')
short_trades = sum(1 for t in trades if t['Direction'] == 'SHORT')

total_pnl = total_capital - STARTING_CAPITAL
return_pct = (total_pnl / STARTING_CAPITAL * 100)

print(f"\nTrade Summary:")
print(f"  Total Trades: {total_trades}")
print(f"  LONG Trades:  {long_trades}")
print(f"  SHORT Trades: {short_trades}")
print(f"  Wins:  {winning}")
print(f"  Losses: {losing}")
print(f"  Win Rate: {win_rate:.1f}%")

print(f"\nCapital & Returns:")
print(f"  Initial Capital: ${STARTING_CAPITAL:,.2f}")
print(f"  Final Equity:    ${total_capital:,.2f}")
print(f"  Total P&L:       ${total_pnl:,.2f}")
print(f"  Return:          {return_pct:+.2f}%")

# Save to CSV
if trades:
    output_file = "backtest_flat_final.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
    print(f"\nResults saved to: {output_file}")
    
    print(f"\n{'Dir':>5} {'Lots':>6} {'Date_In':>12} {'Time_In':>8} {'Price_In':>12} {'Date_Out':>12} {'Time_Out':>8} {'Price_Out':>12} {'PTS':>8} {'P&L':>10} {'Status':>11} {'Session':>10}")
    print("-" * 150)
    for t in trades:
        print(f"{t['Direction']:>5} {t['Flat_Lots']:>6} {t['Date_In']:>12} {t['Time_In']:>8} {t['Price_In']:>12} {t['Date_Out']:>12} {t['Time_Out']:>8} {t['Price_Out']:>12} {t['PTS']:>8} {t['Flat_P&L']:>10} {t['Status']:>11} {t['Session_In']:>10}")
