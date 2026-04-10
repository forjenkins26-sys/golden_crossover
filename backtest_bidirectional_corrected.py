"""
CORRECTED Bidirectional Strategy: LONG + SHORT with RSI + Bollinger Bands
March 1 - April 10, 2026 Backtest
FIXES: Accurate Time_In + Proper Compound Lot Sizing
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
# SESSION FILTERING
# ============================================================================

def get_session(timestamp):
    """Get current session based on IST time (UTC + 5:30)"""
    hour_utc = timestamp.hour
    
    if 0.5 <= hour_utc < 4.5:
        return "Asian"
    elif 5.5 <= hour_utc < 11.5:
        return "London"
    elif 12.5 <= hour_utc < 17.5:
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
TP2_LONG = 0.035
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.035
SL_SHORT = 0.01

TRAIL_PCT = 0.01

# ============================================================================
# MAIN BACKTEST
# ============================================================================

print("=" * 150)
print("CORRECTED BIDIRECTIONAL BACKTEST: March 1 - April 10, 2026")
print("LONG + SHORT with RSI + Bollinger Bands (Fixed Time + Compound Lots)")
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
flat_capital = STARTING_CAPITAL
compound_capital = STARTING_CAPITAL
compound_lot = LOT_SIZE
previous_trade_status = None  # Track if last trade was win/loss

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
                pnl_flat = (exit_price - open_trade['entry']) * LOT_SIZE
                pnl_cmpd = (exit_price - open_trade['entry']) * open_trade['cmpd_lot']
                flat_capital += pnl_flat
                compound_capital += pnl_cmpd
                
                # Update compound lot for NEXT trade (win)
                new_cmpd_lot = open_trade['cmpd_lot'] + LOT_SIZE
                
                trades.append({
                    'Direction': 'LONG',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                    'Flat_P&L': f"${pnl_flat:+.2f}",
                    'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                    'Status': 'TP2',
                    'Session': session
                })
                print(f"[{timestamp}] LONG TP2  @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (WIN)")
                compound_lot = new_cmpd_lot
                open_trade = None
            
            # TP1 trailing stop
            elif price >= open_trade['tp1']:
                if 'trail_sl' not in open_trade:
                    open_trade['trail_sl'] = price * (1 - TRAIL_PCT)
                else:
                    open_trade['trail_sl'] = max(open_trade['trail_sl'], price * (1 - TRAIL_PCT))
                
                if price <= open_trade['trail_sl']:
                    exit_price = open_trade['trail_sl']
                    pnl_flat = (exit_price - open_trade['entry']) * LOT_SIZE
                    pnl_cmpd = (exit_price - open_trade['entry']) * open_trade['cmpd_lot']
                    flat_capital += pnl_flat
                    compound_capital += pnl_cmpd
                    
                    # Update compound lot for NEXT trade (win)
                    new_cmpd_lot = open_trade['cmpd_lot'] + LOT_SIZE
                    
                    trades.append({
                        'Direction': 'LONG',
                        'Flat_Lots': f"{LOT_SIZE:.2f}",
                        'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"${open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"${exit_price:.2f}",
                        'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                        'Flat_P&L': f"${pnl_flat:+.2f}",
                        'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                        'Status': 'TP1_Trail',
                        'Session': session
                    })
                    print(f"[{timestamp}] LONG TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (WIN)")
                    compound_lot = new_cmpd_lot
                    open_trade = None
            
            # Hard SL
            elif price <= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl_flat = (exit_price - open_trade['entry']) * LOT_SIZE
                pnl_cmpd = (exit_price - open_trade['entry']) * open_trade['cmpd_lot']
                flat_capital += pnl_flat
                compound_capital += pnl_cmpd
                
                # Reset compound lot to base (loss)
                new_cmpd_lot = LOT_SIZE
                
                trades.append({
                    'Direction': 'LONG',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                    'Flat_P&L': f"${pnl_flat:+.2f}",
                    'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                    'Status': 'SL',
                    'Session': session
                })
                print(f"[{timestamp}] LONG SL   @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (LOSS-RESET)")
                compound_lot = new_cmpd_lot
                open_trade = None
        
        elif open_trade['type'] == 'SHORT':
            # TP2 exit
            if price <= open_trade['tp2']:
                exit_price = open_trade['tp2']
                pnl_flat = (open_trade['entry'] - exit_price) * LOT_SIZE
                pnl_cmpd = (open_trade['entry'] - exit_price) * open_trade['cmpd_lot']
                flat_capital += pnl_flat
                compound_capital += pnl_cmpd
                
                # Update compound lot for NEXT trade (win)
                new_cmpd_lot = open_trade['cmpd_lot'] + LOT_SIZE
                
                trades.append({
                    'Direction': 'SHORT',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                    'Flat_P&L': f"${pnl_flat:+.2f}",
                    'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                    'Status': 'TP2',
                    'Session': session
                })
                print(f"[{timestamp}] SHORT TP2 @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (WIN)")
                compound_lot = new_cmpd_lot
                open_trade = None
            
            # TP1 trailing stop
            elif price <= open_trade['tp1']:
                if 'trail_sl' not in open_trade:
                    open_trade['trail_sl'] = price * (1 + TRAIL_PCT)
                else:
                    open_trade['trail_sl'] = min(open_trade['trail_sl'], price * (1 + TRAIL_PCT))
                
                if price >= open_trade['trail_sl']:
                    exit_price = open_trade['trail_sl']
                    pnl_flat = (open_trade['entry'] - exit_price) * LOT_SIZE
                    pnl_cmpd = (open_trade['entry'] - exit_price) * open_trade['cmpd_lot']
                    flat_capital += pnl_flat
                    compound_capital += pnl_cmpd
                    
                    # Update compound lot for NEXT trade (win)
                    new_cmpd_lot = open_trade['cmpd_lot'] + LOT_SIZE
                    
                    trades.append({
                        'Direction': 'SHORT',
                        'Flat_Lots': f"{LOT_SIZE:.2f}",
                        'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"${open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"${exit_price:.2f}",
                        'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                        'Flat_P&L': f"${pnl_flat:+.2f}",
                        'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                        'Status': 'TP1_Trail',
                        'Session': session
                    })
                    print(f"[{timestamp}] SHORT TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (WIN)")
                    compound_lot = new_cmpd_lot
                    open_trade = None
            
            # Hard SL
            elif price >= open_trade['sl']:
                exit_price = open_trade['sl']
                pnl_flat = (open_trade['entry'] - exit_price) * LOT_SIZE
                pnl_cmpd = (open_trade['entry'] - exit_price) * open_trade['cmpd_lot']
                flat_capital += pnl_flat
                compound_capital += pnl_cmpd
                
                # Reset compound lot to base (loss)
                new_cmpd_lot = LOT_SIZE
                
                trades.append({
                    'Direction': 'SHORT',
                    'Flat_Lots': f"{LOT_SIZE:.2f}",
                    'Cmpd_Lots': f"{open_trade['cmpd_lot']:.2f}",
                    'Date_In': open_trade['date_in'],
                    'Time_In': open_trade['time_in'],
                    'Price_In': f"${open_trade['entry']:.2f}",
                    'Date_Out': timestamp.strftime('%Y-%m-%d'),
                    'Time_Out': timestamp.strftime('%H:%M'),
                    'Price_Out': f"${exit_price:.2f}",
                    'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                    'Flat_P&L': f"${pnl_flat:+.2f}",
                    'Cmpd_P&L': f"${pnl_cmpd:+.2f}",
                    'Status': 'SL',
                    'Session': session
                })
                print(f"[{timestamp}] SHORT SL  @ ${exit_price:,.0f} | P&L: ${pnl_flat:+.2f} | Cmpd_Lot: {open_trade['cmpd_lot']:.2f} -> {new_cmpd_lot:.2f} (LOSS-RESET)")
                compound_lot = new_cmpd_lot
                open_trade = None
    
    # Entry signals
    if not open_trade and session_active:
        # LONG: RSI < 25 + Price < Lower BB
        if rsi < RSI_LONG and price < bb_lower:
            tp1 = price * (1 + TP1_LONG)
            tp2 = price * (1 + TP2_LONG)
            sl = price * (1 - SL_LONG)
            open_trade = {
                'type': 'LONG',
                'entry': price,
                'date_in': timestamp.strftime('%Y-%m-%d'),
                'time_in': timestamp.strftime('%H:%M'),  # Accurate time with minutes
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl,
                'cmpd_lot': compound_lot
            }
            print(f"[{timestamp}] LONG ENTRY  @ ${price:,.0f} | RSI:{rsi:5.1f} | Cmpd_Lot: {compound_lot:.2f}")
        
        # SHORT: RSI > 75 + Price > Upper BB
        elif rsi > RSI_SHORT and price > bb_upper:
            tp1 = price * (1 - TP1_SHORT)
            tp2 = price * (1 - TP2_SHORT)
            sl = price * (1 + SL_SHORT)
            open_trade = {
                'type': 'SHORT',
                'entry': price,
                'date_in': timestamp.strftime('%Y-%m-%d'),
                'time_in': timestamp.strftime('%H:%M'),  # Accurate time with minutes
                'tp1': tp1,
                'tp2': tp2,
                'sl': sl,
                'cmpd_lot': compound_lot
            }
            print(f"[{timestamp}] SHORT ENTRY @ ${price:,.0f} | RSI:{rsi:5.1f} | Cmpd_Lot: {compound_lot:.2f}")

# Results
print("\n" + "=" * 150)
print("BACKTEST RESULTS")
print("=" * 150)

total_trades = len(trades)
winning = sum(1 for t in trades if '$+' in t['Flat_P&L'])
losing = total_trades - winning
win_rate = (winning / total_trades * 100) if total_trades > 0 else 0

long_trades = sum(1 for t in trades if t['Direction'] == 'LONG')
short_trades = sum(1 for t in trades if t['Direction'] == 'SHORT')

flat_total_pnl = flat_capital - STARTING_CAPITAL
flat_return = (flat_total_pnl / STARTING_CAPITAL * 100)

compound_total_pnl = compound_capital - STARTING_CAPITAL
compound_return = (compound_total_pnl / STARTING_CAPITAL * 100)

print(f"\nTrade Summary:")
print(f"  Total Trades: {total_trades}")
print(f"  LONG Trades:  {long_trades}")
print(f"  SHORT Trades: {short_trades}")
print(f"  Wins:  {winning}")
print(f"  Losses: {losing}")
print(f"  Win Rate: {win_rate:.1f}%")

print(f"\nFlat Lot Sizing (0.10 BTC constant):")
print(f"  Initial Capital: ${STARTING_CAPITAL:,.2f}")
print(f"  Final Equity:    ${flat_capital:,.2f}")
print(f"  Total P&L:       ${flat_total_pnl:,.2f}")
print(f"  Return:          {flat_return:+.2f}%")

print(f"\nCompound Lot Sizing (0.10 base, +0.10 on wins, reset on losses):")
print(f"  Initial Capital: ${STARTING_CAPITAL:,.2f}")
print(f"  Final Equity:    ${compound_capital:,.2f}")
print(f"  Total P&L:       ${compound_total_pnl:,.2f}")
print(f"  Return:          {compound_return:+.2f}%")

# Save to CSV
if trades:
    output_file = "backtest_bidirectional_corrected.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys())
        writer.writeheader()
        writer.writerows(trades)
    print(f"\nResults saved to: {output_file}")
    
    print(f"\n{'Direction':>10} {'Flat_Lots':>10} {'Cmpd_Lots':>10} {'Date_In':>12} {'Time_In':>8} {'Price_In':>12} {'Date_Out':>12} {'Price_Out':>12} {'Flat_P&L':>10} {'Cmpd_P&L':>10} {'Status':>11} {'Session':>10}")
    print("-" * 150)
    for t in trades:
        print(f"{t['Direction']:>10} {t['Flat_Lots']:>10} {t['Cmpd_Lots']:>10} {t['Date_In']:>12} {t['Time_In']:>8} {t['Price_In']:>12} {t['Date_Out']:>12} {t['Price_Out']:>12} {t['Flat_P&L']:>10} {t['Cmpd_P&L']:>10} {t['Status']:>11} {t['Session']:>10}")
