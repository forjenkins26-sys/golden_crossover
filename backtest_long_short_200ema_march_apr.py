"""
Backtest: LONG + SHORT with 200 EMA Trend Filter
Period: March 1 - April 10, 2026
- LONG: Price > 200EMA AND RSI < 25 AND Price < Lower BB
- SHORT: Price < 200EMA AND RSI > 75 AND Price > Upper BB
"""

import pandas as pd
import numpy as np
from datetime import datetime
import yfinance as yf

# Configuration
START_DATE = "2026-03-01"
END_DATE = "2026-04-10"
LOT_SIZE = 0.10  # BTC
STARTING_CAPITAL = 500  # USD

# Long levels
TP1_LONG = 0.015  # +1.5%
TP2_LONG = 0.035  # +3.5%
SL_LONG = -0.01   # -1.0%

# Short levels
TP1_SHORT = -0.015  # -1.5%
TP2_SHORT = -0.035  # -3.5%
SL_SHORT = 0.01   # +1.0%

class Trade:
    def __init__(self, trade_type, entry_price, entry_time, session):
        self.type = trade_type
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.session = session
        self.exit_price = None
        self.exit_time = None
        self.status = None
        self.tp1_hit = False
        
        if trade_type == "LONG":
            self.tp1 = entry_price * (1 + TP1_LONG)
            self.tp2 = entry_price * (1 + TP2_LONG)
            self.sl = entry_price * (1 + SL_LONG)
        else:  # SHORT
            self.tp1 = entry_price * (1 + TP1_SHORT)
            self.tp2 = entry_price * (1 + TP2_SHORT)
            self.sl = entry_price * (1 + SL_SHORT)
    
    def check_exit(self, price):
        """Check if trade should exit, return status or None"""
        if self.type == "LONG":
            # TP2 immediate exit
            if price >= self.tp2:
                return "TP2", self.tp2
            # TP1 trail start
            elif price >= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.sl = price * 0.99
                return None, None  # Continue trailing
            # Trailing SL
            elif self.tp1_hit:
                new_sl = price * 0.99
                if new_sl > self.sl:
                    self.sl = new_sl
                if price <= self.sl:
                    return "TP1_TRAIL", self.sl
            # Hard SL
            elif price <= self.sl:
                return "SL", self.sl
        
        else:  # SHORT
            # TP2 immediate exit
            if price <= self.tp2:
                return "TP2", self.tp2
            # TP1 trail start
            elif price <= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.sl = price * 1.01
                return None, None  # Continue trailing
            # Trailing SL
            elif self.tp1_hit:
                new_sl = price * 1.01
                if new_sl < self.sl:
                    self.sl = new_sl
                if price >= self.sl:
                    return "TP1_TRAIL", self.sl
            # Hard SL
            elif price >= self.sl:
                return "SL", self.sl
        
        return None, None
    
    def get_pnl(self, exit_price):
        """Calculate P&L"""
        if self.type == "LONG":
            pnl_usd = (exit_price - self.entry_price) * LOT_SIZE
            pnl_pct = (exit_price - self.entry_price) / self.entry_price
        else:  # SHORT
            pnl_usd = (self.entry_price - exit_price) * LOT_SIZE
            pnl_pct = (self.entry_price - exit_price) / self.entry_price
        return pnl_usd, pnl_pct

def get_session(hour_utc):
    """Get session from UTC hour"""
    if 0.5 <= hour_utc < 4.5:
        return "Asian"
    elif 5.5 <= hour_utc < 11.5:
        return "London"
    elif 12.5 <= hour_utc < 17.5:
        return "NewYork"
    else:
        return "Off-Session"

def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bb(closes, period=20, std_dev=2.0):
    """Calculate Bollinger Bands"""
    if len(closes) < period:
        return None, None, None
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return sma, upper, lower

def calculate_ema(closes, period=200):
    """Calculate EMA"""
    if len(closes) < period:
        return None
    if isinstance(closes, np.ndarray):
        closes = closes.flatten()
    ema = pd.Series(closes).ewm(span=period, adjust=False).mean()
    return float(ema.iloc[-1])

def run_backtest():
    """Run backtest"""
    print("=" * 100)
    print("📊 BACKTEST: LONG + SHORT with 200 EMA Trend Filter")
    print(f"📅 Period: {START_DATE} to {END_DATE}")
    print(f"💰 Capital: ${STARTING_CAPITAL} | Lot: {LOT_SIZE} BTC")
    print(f"🎯 LONG: Price>EMA200 + RSI<25 + Price<BBLower")
    print(f"🎯 SHORT: Price<EMA200 + RSI>75 + Price>BBUpper")
    print("=" * 100)
    
    # Download data
    df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
    print(f"📥 Downloaded {len(df)} 1-hour bars")
    
    closes = df['Close'].values
    times = df.index
    
    # Backtest variables
    trades = []
    open_trade = None
    capital = STARTING_CAPITAL
    
    # Main loop
    for i in range(200, len(closes)):  # Need 200 bars for EMA
        price = closes[i]
        timestamp = times[i]
        
        # Calculate indicators
        rsi = calculate_rsi(closes[max(0, i-50):i+1], period=14)
        sma, bb_upper, bb_lower = calculate_bb(closes[max(0, i-50):i+1], period=20)
        ema200 = calculate_ema(closes[:i+1], period=200)
        
        if None in [rsi, sma, bb_upper, bb_lower, ema200]:
            continue
        
        hour_utc = timestamp.hour + timestamp.minute / 60.0
        session = get_session(hour_utc)
        
        # Process open trade
        if open_trade:
            exit_status, exit_price = open_trade.check_exit(price)
            if exit_status:
                open_trade.exit_price = exit_price
                open_trade.exit_time = timestamp
                open_trade.status = exit_status
                pnl_usd, pnl_pct = open_trade.get_pnl(exit_price)
                capital += pnl_usd
                
                trades.append({
                    'Date_In': open_trade.entry_time.strftime("%Y-%m-%d"),
                    'Time_In': open_trade.entry_time.strftime("%H:%M"),
                    'Type': open_trade.type,
                    'Price_In': f"{open_trade.entry_price:.2f}",
                    'Date_Out': open_trade.exit_time.strftime("%Y-%m-%d"),
                    'Time_Out': open_trade.exit_time.strftime("%H:%M"),
                    'Price_Out': f"{open_trade.exit_price:.2f}",
                    'Status': open_trade.status,
                    'P&L_USD': f"{pnl_usd:.2f}",
                    'P&L_%': f"{pnl_pct*100:.2f}",
                    'Session': open_trade.session
                })
                
                status_emoji = "✅" if pnl_usd > 0 else "❌"
                print(f"{status_emoji} {open_trade.type:5} Exit @ ${exit_price:,.0f} | P&L: ${pnl_usd:7.2f} | Capital: ${capital:,.2f}")
                open_trade = None
        
        # Check entry signals
        trend = "UPTREND" if price > ema200 else "DOWNTREND"
        long_signal = (price > ema200 and rsi < 25 and price < bb_lower)
        short_signal = (price < ema200 and rsi > 75 and price > bb_upper)
        
        # Entry logic
        if not open_trade:
            if long_signal:
                open_trade = Trade("LONG", price, timestamp, session)
                print(f"🟢 LONG Entry @ ${price:,.0f} | RSI:{rsi:.1f} | {trend} | {session}")
            
            elif short_signal:
                open_trade = Trade("SHORT", price, timestamp, session)
                print(f"🔴 SHORT Entry @ ${price:,.0f} | RSI:{rsi:.1f} | {trend} | {session}")
    
    # Close open trade at end
    if open_trade:
        final_price = closes[-1]
        pnl_usd, pnl_pct = open_trade.get_pnl(final_price)
        capital += pnl_usd
        trades.append({
            'Date_In': open_trade.entry_time.strftime("%Y-%m-%d"),
            'Time_In': open_trade.entry_time.strftime("%H:%M"),
            'Type': open_trade.type,
            'Price_In': f"{open_trade.entry_price:.2f}",
            'Date_Out': times[-1].strftime("%Y-%m-%d"),
            'Time_Out': times[-1].strftime("%H:%M"),
            'Price_Out': f"{final_price:.2f}",
            'Status': "CLOSED_AT_END",
            'P&L_USD': f"{pnl_usd:.2f}",
            'P&L_%': f"{pnl_pct*100:.2f}",
            'Session': open_trade.session
        })
    
    # Results
    print("\n" + "=" * 100)
    print("📊 RESULTS")
    print("=" * 100)
    
    total_trades = len(trades)
    winning = sum(1 for t in trades if float(t['P&L_USD']) > 0)
    losing = total_trades - winning
    win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
    
    long_count = sum(1 for t in trades if t['Type'] == 'LONG')
    short_count = sum(1 for t in trades if t['Type'] == 'SHORT')
    
    total_pnl = capital - STARTING_CAPITAL
    return_pct = (total_pnl / STARTING_CAPITAL) * 100
    
    print(f"\n📈 Summary:")
    print(f"   Total Trades: {total_trades} (LONG: {long_count}, SHORT: {short_count})")
    print(f"   Win Rate: {win_rate:.1f}% ({winning}W / {losing}L)")
    print(f"\n💰 Capital:")
    print(f"   Start: ${STARTING_CAPITAL:,.2f}")
    print(f"   End: ${capital:,.2f}")
    print(f"   P&L: ${total_pnl:,.2f} ({return_pct:.2f}%)")
    
    # Save CSV
    import csv
    output_file = f"backtest_long_short_200ema_march_apr.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=trades[0].keys() if trades else [])
        writer.writeheader()
        writer.writerows(trades)
    print(f"\n📁 Trades saved to: {output_file}")
    
    # Show sample trades
    if trades:
        print(f"\n📋 First 5 Trades:")
        for t in trades[:5]:
            print(f"   {t['Type']:5} @ ${t['Price_In']:>8} → ${t['Price_Out']:>8} | {t['Status']:10} | ${t['P&L_USD']:>8}")

if __name__ == "__main__":
    run_backtest()
