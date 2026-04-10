"""
CORRECTED Bidirectional Strategy: LONG + SHORT with RSI + Bollinger Bands
March 1 - April 10, 2026 Backtest
NO 200 EMA trend filter - allows more trades

Entry Logic:
- LONG: RSI < 25 + Price < Lower BB (oversold)
- SHORT: RSI > 75 + Price > Upper BB (overbought)
"""

import pandas as pd
import numpy as np
import yfinance as yf
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
    
    # IST = UTC + 5:30, so:
    # Asian (06:00-10:00 IST) = 00:30-04:30 UTC
    # London (11:00-17:00 IST) = 05:30-11:30 UTC
    # New York (18:00-23:00 IST) = 12:30-17:30 UTC
    
    if 0.5 <= hour_utc < 4.5:
        return "Asian"
    elif 5.5 <= hour_utc < 11.5:
        return "London"
    elif 12.5 <= hour_utc < 17.5:
        return "New York"
    else:
        return "Off-Session"

# ============================================================================
# TRADE CLASS
# ============================================================================

class Trade:
    """Track individual trade (LONG or SHORT)"""
    
    def __init__(self, entry_idx, entry_price, entry_time, direction, 
                 tp1, tp2, sl, flat_lot, compound_lot, session):
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction  # "LONG" or "SHORT"
        self.tp1 = tp1
        self.tp2 = tp2
        self.sl = sl
        self.flat_lot = flat_lot
        self.compound_lot = compound_lot
        self.session = session
        
        # Exit info
        self.exit_idx = None
        self.exit_price = None
        self.exit_time = None
        self.exit_type = None
        self.highest_price = entry_price if direction == "LONG" else entry_price
        self.lowest_price = entry_price
        self.trail_sl = None
        
        # P&L
        self.flat_pnl = 0
        self.compound_pnl = 0
        self.points = 0
    
    def update_extremes(self, high, low):
        """Update highest/lowest for trailing stop"""
        if self.direction == "LONG":
            if high > self.highest_price:
                self.highest_price = high
        else:  # SHORT
            if low < self.lowest_price:
                self.lowest_price = low
    
    def close(self, exit_idx, exit_price, exit_time, exit_type):
        """Close the trade"""
        self.exit_idx = exit_idx
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_type = exit_type
        
        # Calculate metrics
        if self.direction == "LONG":
            self.points = exit_price - self.entry_price
            self.flat_pnl = self.points * self.flat_lot
            self.compound_pnl = self.points * self.compound_lot
        else:  # SHORT
            self.points = self.entry_price - exit_price
            self.flat_pnl = self.points * self.flat_lot
            self.compound_pnl = self.points * self.compound_lot
    
    def to_dict(self):
        """Convert to dict for CSV"""
        return {
            'Direction': self.direction,
            'Flat_Lots': f"{self.flat_lot:.2f}",
            'Cmpd_Lots': f"{self.compound_lot:.2f}",
            'Date_In': self.entry_time.strftime("%Y-%m-%d"),
            'Time_In': self.entry_time.strftime("%H:%M"),
            'Price_In': f"${self.entry_price:.2f}",
            'Date_Out': self.exit_time.strftime("%Y-%m-%d"),
            'Time_Out': self.exit_time.strftime("%H:%M"),
            'Price_Out': f"${self.exit_price:.2f}",
            'PTS': f"{self.points:+.2f}",
            'Flat_P&L': f"${self.flat_pnl:+.2f}",
            'Cmpd_P&L': f"${self.compound_pnl:+.2f}",
            'Status': self.exit_type,
            'Session': self.session,
        }

# ============================================================================
# CONFIG
# ============================================================================

START_DATE = "2026-03-01"
END_DATE = "2026-04-10"
LOT_SIZE = 0.10
STARTING_CAPITAL = 500

# Indicators
RSI_PERIOD = 14
RSI_LONG = 25        # RSI < 25 for LONG entry
RSI_SHORT = 75       # RSI > 75 for SHORT entry
BB_PERIOD = 20
BB_STD = 2.0

# Trade levels
TP1_LONG = 0.015     # +1.5%
TP2_LONG = 0.035     # +3.5%
SL_LONG = 0.01       # -1.0%

TP1_SHORT = 0.015    # -1.5%
TP2_SHORT = 0.035    # -3.5%
SL_SHORT = 0.01      # +1.0%

TRAIL_PCT = 0.01     # 1% trailing stop

# ============================================================================
# MAIN BACKTEST
# ============================================================================

print("=" * 130)
print("BIDIRECTIONAL BACKTEST: March 1 - April 10, 2026")
print("LONG + SHORT with RSI + Bollinger Bands (NO 200 EMA trend filter)")
print("=" * 130)

# Download data
print(f"\nDownloading BTC 1-hour data ({START_DATE} - {END_DATE})...\n")
df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
print(f"Loaded {len(df)} 1-hour bars\n")

# Calculate indicators
df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)

# Drop NaN rows
df = df.dropna()

# Store High/Low for intrabar trailing
if 'High' not in df.columns:
    df['High'] = df['Close']
if 'Low' not in df.columns:
    df['Low'] = df['Close']

trades = []
open_trade = None
flat_capital = STARTING_CAPITAL
compound_capital = STARTING_CAPITAL
compound_lot = LOT_SIZE

# Main loop
print("Running bidirectional backtest (March 1 - April 10, 2026)...\n")
for idx in range(len(df)):
    row = df.iloc[idx]
    timestamp = df.index[idx]
    price = float(row['Close'])
    high = float(row['High'])
    low = float(row['Low'])
    rsi = float(row['RSI'])
    bb_upper = float(row['BB_Upper'])
    bb_lower = float(row['BB_Lower'])
    
    session = get_session(timestamp)
    session_active = session != "Off-Session"
    
    # Check exit for open trade
    if open_trade:
        open_trade.update_extremes(high, low)
        
        if open_trade.direction == "LONG":
            # TP2 exit
            if price >= open_trade.tp2:
                exit_price = open_trade.tp2
                open_trade.close(idx, exit_price, timestamp, 'TP2')
                flat_capital += open_trade.flat_pnl
                compound_capital += open_trade.compound_pnl
                trades.append(open_trade)
                print(f"✅ LONG TP2  @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                open_trade = None
                compound_lot = LOT_SIZE
            
            # TP1 trailing stop (activate on TP1 touch)
            elif price >= open_trade.tp1:
                if open_trade.trail_sl is None:
                    open_trade.trail_sl = price * (1 - TRAIL_PCT)
                else:
                    open_trade.trail_sl = max(open_trade.trail_sl, price * (1 - TRAIL_PCT))
                
                if price <= open_trade.trail_sl:
                    exit_price = open_trade.trail_sl
                    open_trade.close(idx, exit_price, timestamp, 'TP1_Trail')
                    flat_capital += open_trade.flat_pnl
                    compound_capital += open_trade.compound_pnl
                    trades.append(open_trade)
                    print(f"LONG TP1TRAIL @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                    open_trade = None
                    compound_lot = LOT_SIZE
            
            # Hard SL
            elif price <= open_trade.sl:
                exit_price = open_trade.sl
                open_trade.close(idx, exit_price, timestamp, 'SL')
                flat_capital += open_trade.flat_pnl
                compound_capital += open_trade.compound_pnl
                trades.append(open_trade)
                    print(f"LONG SL   @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                open_trade = None
                compound_lot = LOT_SIZE  # Reset after loss
        
        elif open_trade.direction == "SHORT":
            # TP2 exit
            if price <= open_trade.tp2:
                exit_price = open_trade.tp2
                open_trade.close(idx, exit_price, timestamp, 'TP2')
                flat_capital += open_trade.flat_pnl
                compound_capital += open_trade.compound_pnl
                trades.append(open_trade)
                print(f"SHORT TP2 @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                open_trade = None
                compound_lot = LOT_SIZE
            
            # TP1 trailing stop (activate on TP1 touch)
            elif price <= open_trade.tp1:
                if open_trade.trail_sl is None:
                    open_trade.trail_sl = price * (1 + TRAIL_PCT)
                else:
                    open_trade.trail_sl = min(open_trade.trail_sl, price * (1 + TRAIL_PCT))
                
                if price >= open_trade.trail_sl:
                    exit_price = open_trade.trail_sl
                    open_trade.close(idx, exit_price, timestamp, 'TP1_Trail')
                    flat_capital += open_trade.flat_pnl
                    compound_capital += open_trade.compound_pnl
                    trades.append(open_trade)
                    print(f"SHORT TP1TRAIL @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                    open_trade = None
                    compound_lot = LOT_SIZE
            
            # Hard SL
            elif price >= open_trade.sl:
                exit_price = open_trade.sl
                open_trade.close(idx, exit_price, timestamp, 'SL')
                flat_capital += open_trade.flat_pnl
                compound_capital += open_trade.compound_pnl
                trades.append(open_trade)
                print(f"SHORT SL  @ ${exit_price:,.0f} | P&L: ${open_trade.flat_pnl:+7.2f} | Capital: ${flat_capital:,.2f}")
                open_trade = None
                compound_lot = LOT_SIZE  # Reset after loss
    
    # Check entry signals
    if not open_trade and session_active:
        # LONG entry: RSI < 25 + Price < Lower BB
        if rsi < RSI_LONG and price < bb_lower:
            tp1_price = price * (1 + TP1_LONG)
            tp2_price = price * (1 + TP2_LONG)
            sl_price = price * (1 - SL_LONG)
            
            open_trade = Trade(
                idx, price, timestamp, "LONG",
                tp1_price, tp2_price, sl_price,
                LOT_SIZE, compound_lot, session
            )
            print(f"LONG ENTRY  @ ${price:,.0f} | RSI:{rsi:5.1f} | TP1:${tp1_price:,.0f} TP2:${tp2_price:,.0f}")
            compound_lot += LOT_SIZE  # Increase for next trade
        
        # SHORT entry: RSI > 75 + Price > Upper BB
        elif rsi > RSI_SHORT and price > bb_upper:
            tp1_price = price * (1 - TP1_SHORT)
            tp2_price = price * (1 - TP2_SHORT)
            sl_price = price * (1 + SL_SHORT)
            
            open_trade = Trade(
                idx, price, timestamp, "SHORT",
                tp1_price, tp2_price, sl_price,
                LOT_SIZE, compound_lot, session
            )
            print(f"SHORT ENTRY @ ${price:,.0f} | RSI:{rsi:5.1f} | TP1:${tp1_price:,.0f} TP2:${tp2_price:,.0f}")
            compound_lot += LOT_SIZE  # Increase for next trade

# Close remaining position
if open_trade:
    final_price = float(df.iloc[-1]['Close'])
    open_trade.close(len(df)-1, final_price, df.index[-1], 'END_OF_PERIOD')
    if open_trade.direction == "LONG":
        flat_capital += open_trade.flat_pnl
        compound_capital += open_trade.compound_pnl
    else:
        flat_capital += open_trade.flat_pnl
        compound_capital += open_trade.compound_pnl
    trades.append(open_trade)

# Results
print("\n" + "=" * 130)
print("BACKTEST RESULTS")
print("=" * 130)

total_trades = len(trades)
winning = sum(1 for t in trades if t.flat_pnl > 0)
losing = total_trades - winning
win_rate = (winning / total_trades * 100) if total_trades > 0 else 0

long_trades = sum(1 for t in trades if t.direction == "LONG")
short_trades = sum(1 for t in trades if t.direction == "SHORT")

flat_total_pnl = flat_capital - STARTING_CAPITAL
flat_return_pct = (flat_total_pnl / STARTING_CAPITAL * 100)

compound_total_pnl = compound_capital - STARTING_CAPITAL
compound_return_pct = (compound_total_pnl / STARTING_CAPITAL * 100)

print(f"\n📊 SUMMARY:")
print(f"   Total Trades:        {total_trades}")
print(f"   LONG Trades:         {long_trades}")
print(f"   SHORT Trades:        {short_trades}")
print(f"   Wins:                {winning}")
print(f"   Losses:              {losing}")
print(f"   Win Rate:            {win_rate:.1f}%")

print(f"\n💰 FLAT LOT SIZING (0.10 BTC constant):")
print(f"   Initial Capital:     ${STARTING_CAPITAL:,.2f}")
print(f"   Final Equity:        ${flat_capital:,.2f}")
print(f"   Total Return:        {flat_return_pct:.2f}%")
print(f"   Net Profit:          ${flat_total_pnl:,.2f}")

print(f"\n💰 COMPOUND LOT SIZING:")
print(f"   Initial Capital:     ${STARTING_CAPITAL:,.2f}")
print(f"   Final Equity:        ${compound_capital:,.2f}")
print(f"   Total Return:        {compound_return_pct:.2f}%")
print(f"   Net Profit:          ${compound_total_pnl:,.2f}")

if abs(flat_total_pnl) != abs(compound_total_pnl):
    better_method = "FLAT" if flat_total_pnl > compound_total_pnl else "COMPOUND"
    difference = abs(flat_total_pnl - compound_total_pnl)
    print(f"\n{better_method} is better by: ${difference:+.2f}")

# Save to CSV
if trades:
    output_file = "backtest_bidirectional_complete_march_apr.csv"
    import csv
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].to_dict().keys())
        writer.writeheader()
        for trade in trades:
            writer.writerow(trade.to_dict())
    print(f"\nResults saved to: {output_file}")
    
    print(f"\n" + "=" * 130)
    print("DETAILED TRADE JOURNAL")
    print("=" * 130)
    print(f"\n{'Direction':>10} {'Flat_Lots':>10} {'Cmpd_Lots':>10} {'Date_In':>12} {'Time_In':>8} {'Price_In':>12} {'Date_Out':>12} {'Time_Out':>8} {'Price_Out':>12} {'PTS':>10} {'Flat_P&L':>10} {'Cmpd_P&L':>10} {'Status':>11} {'Session':>10}")
    print("-" * 130)
    for trade in trades:
        d = trade.to_dict()
        print(f"{d['Direction']:>10} {d['Flat_Lots']:>10} {d['Cmpd_Lots']:>10} {d['Date_In']:>12} {d['Time_In']:>8} {d['Price_In']:>12} {d['Date_Out']:>12} {d['Time_Out']:>8} {d['Price_Out']:>12} {d['PTS']:>10} {d['Flat_P&L']:>10} {d['Cmpd_P&L']:>10} {d['Status']:>11} {d['Session']:>10}")
