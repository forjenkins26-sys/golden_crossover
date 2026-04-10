"""
🤖 ENHANCED PAPER TRADING BOT - LONG + SHORT with 200 EMA Trend Filter
Real-time Binance data | RSI + Bollinger Bands | Bidirectional trading
No API keys needed - uses public Binance API
"""

import requests
import pandas as pd
import numpy as np
import csv
import time
from datetime import datetime
import os

# Configuration
LOT_SIZE = 0.10  # BTC
SYMBOL = "BTCUSDT"
INTERVAL = "1h"

# Indicators
RSI_PERIOD = 14
RSI_OVERSOLD = 25
RSI_OVERBOUGHT = 75
BB_PERIOD = 20
BB_STD = 2.0
EMA_PERIOD = 200

# Trade levels
TP1_PCT_LONG = 0.015    # +1.5%
TP2_PCT_LONG = 0.035    # +3.5%
SL_PCT_LONG = 0.01      # -1.0%

TP1_PCT_SHORT = 0.015   # -1.5%
TP2_PCT_SHORT = 0.035   # -3.5%
SL_PCT_SHORT = 0.01     # +1.0%

TRAIL_PCT = 0.01        # Trail by 1%

# Session definitions (IST to UTC)
SESSION_UTC = {
    "Asian": {"start": 0.5, "end": 4.5},      # 06:00-10:00 IST
    "London": {"start": 5.5, "end": 11.5},    # 11:00-17:00 IST
    "NewYork": {"start": 12.5, "end": 17.5},  # 18:00-23:00 IST
}

# File paths
TRADES_CSV = 'paper_trades_enhanced.csv'
SIGNAL_LOG = 'signal_log_enhanced.csv'

def get_session():
    """Get current session"""
    utc_now = datetime.utcnow()
    hour_decimal = utc_now.hour + utc_now.minute / 60.0
    
    for session_name, times in SESSION_UTC.items():
        if times["start"] <= hour_decimal <= times["end"]:
            return session_name, True
    return "Off-Session", False

def fetch_klines(limit=100):
    """Fetch klines from Binance public API"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': SYMBOL,
            'interval': INTERVAL,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        return df
    
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return None

def calculate_rsi(closes, period=14):
    """Calculate RSI"""
    if len(closes) < period + 1:
        return None
    
    closes_array = np.array(closes, dtype=float)
    deltas = np.diff(closes_array)
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
    
    closes_array = np.array(closes, dtype=float)
    sma = np.mean(closes_array[-period:])
    std = np.std(closes_array[-period:])
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    return upper, sma, lower

def calculate_ema(closes, period=200):
    """Calculate EMA"""
    if len(closes) < period:
        return None
    
    closes_array = np.array(closes, dtype=float)
    ema = closes_array[0]
    multiplier = 2.0 / (period + 1)
    
    for close in closes_array[1:]:
        ema = close * multiplier + ema * (1 - multiplier)
    
    return ema

def init_trade_journal():
    """Initialize trade journal CSV"""
    if not os.path.exists(TRADES_CSV):
        with open(TRADES_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Timestamp_In', 'Type', 'Entry_Price', 'TP1', 'TP2', 'SL',
                'Timestamp_Out', 'Exit_Price', 'Status', 'P&L_USD', 'P&L_%', 'Session'
            ])

def log_trade(ts_in, trade_type, entry_price, tp1, tp2, sl, ts_out, exit_price, status, pnl_usd, pnl_pct, session):
    """Log trade to CSV"""
    with open(TRADES_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            ts_in, trade_type, f"{entry_price:.2f}", f"{tp1:.2f}", f"{tp2:.2f}", f"{sl:.2f}",
            ts_out, f"{exit_price:.2f}", status, f"{pnl_usd:.2f}", f"{pnl_pct*100:.2f}", session
        ])

class Trade:
    """Represent an open trade"""
    def __init__(self, trade_type, entry_price, entry_time, session):
        self.type = trade_type  # "LONG" or "SHORT"
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.session = session
        
        if trade_type == "LONG":
            self.tp1 = entry_price * (1 + TP1_PCT_LONG)
            self.tp2 = entry_price * (1 + TP2_PCT_LONG)
            self.sl = entry_price * (1 - SL_PCT_LONG)
        else:  # SHORT
            self.tp1 = entry_price * (1 - TP1_PCT_SHORT)
            self.tp2 = entry_price * (1 - TP2_PCT_SHORT)
            self.sl = entry_price * (1 + SL_PCT_SHORT)
        
        self.tp1_hit = False
    
    def check_exit(self, price):
        """Return (exit_status, exit_price) or (None, None)"""
        if self.type == "LONG":
            if price >= self.tp2:
                return "TP2", self.tp2
            elif price >= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.sl = price * (1 - TRAIL_PCT)
                return None, None
            elif self.tp1_hit:
                self.sl = max(self.sl, price * (1 - TRAIL_PCT))
                if price <= self.sl:
                    return "TP1_TRAIL", self.sl
            elif price <= self.sl:
                return "SL", self.sl
        
        else:  # SHORT
            if price <= self.tp2:
                return "TP2", self.tp2
            elif price <= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.sl = price * (1 + TRAIL_PCT)
                return None, None
            elif self.tp1_hit:
                self.sl = min(self.sl, price * (1 + TRAIL_PCT))
                if price >= self.sl:
                    return "TP1_TRAIL", self.sl
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

def run_bot():
    """Main bot loop"""
    print("=" * 100)
    print("🤖 ENHANCED PAPER TRADING BOT - LONG + SHORT with 200 EMA")
    print("=" * 100)
    print(f"⚙️  Symbol: {SYMBOL} | Timeframe: {INTERVAL}")
    print(f"💰 Lot Size: {LOT_SIZE} BTC | Starting Capital: Not tracked in paper mode")
    print(f"🎯 LONG: RSI<25 + Price<LowerBB + Price>EMA200")
    print(f"🎯 SHORT: RSI>75 + Price>UpperBB + Price<EMA200")
    print(f"📝 Journal: {TRADES_CSV}")
    print("=" * 100 + "\n")
    
    init_trade_journal()
    
    open_trade = None
    check_count = 0
    
    while True:
        try:
            check_count += 1
            now_utc = datetime.utcnow()
            timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Fetch candles
            df = fetch_klines(limit=200)
            if df is None or len(df) < 200:
                print(f"[{timestamp_str}] ⏳ Warming up data...")
                time.sleep(60)
                continue
            
            closes = df['close'].values.flatten()
            
            # Calculate indicators
            rsi = calculate_rsi(closes, period=14)
            bb_upper, bb_mid, bb_lower = calculate_bb(closes, period=20)
            ema200 = calculate_ema(closes, period=200)
            
            if None in [rsi, bb_upper, bb_lower, ema200]:
                print(f"[{timestamp_str}] ⏳ Calculating indicators...")
                time.sleep(60)
                continue
            
            price = float(closes[-1])
            trend = "UPTREND" if price > ema200 else "DOWNTREND"
            session, is_active = get_session()
            
            # Check signals
            long_signal = (price > ema200 and rsi < RSI_OVERSOLD and price < bb_lower)
            short_signal = (price < ema200 and rsi > RSI_OVERBOUGHT and price > bb_upper)
            
            # Display status (every 60 checks)
            if check_count % 60 == 0 or open_trade or long_signal or short_signal:
                status = f"[{timestamp_str}] {session:11} | ${price:,.0f} | RSI:{rsi:5.1f} | {trend:9}"
                if open_trade:
                    status += f" | 📍 {open_trade.type:5} Open"
                print(status)
            
            # Process open trade
            if open_trade:
                exit_status, exit_price = open_trade.check_exit(price)
                if exit_status:
                    pnl_usd, pnl_pct = open_trade.get_pnl(exit_price)
                    
                    emoji = "✅" if pnl_usd > 0 else "❌"
                    status_desc = {
                        "TP2": "TP2 Hit",
                        "TP1_TRAIL": "TP1 Trail Hit",
                        "SL": "SL Hit"
                    }
                    
                    print(f"{emoji} {open_trade.type:5} {status_desc.get(exit_status, exit_status):15} @ ${exit_price:,.0f} | P&L: ${pnl_usd:+7.2f} ({pnl_pct*100:+6.2f}%)")
                    
                    log_trade(
                        open_trade.entry_time.strftime("%Y-%m-%d %H:%M"),
                        open_trade.type,
                        open_trade.entry_price,
                        open_trade.tp1,
                        open_trade.tp2,
                        open_trade.sl,
                        now_utc.strftime("%Y-%m-%d %H:%M"),
                        exit_price,
                        exit_status,
                        pnl_usd,
                        pnl_pct,
                        open_trade.session
                    )
                    
                    open_trade = None
            
            # Entry logic
            if not open_trade and is_active:
                if long_signal:
                    open_trade = Trade("LONG", price, now_utc, session)
                    print(f"🟢 LONG Entry    @ ${price:,.0f} | TP1:${open_trade.tp1:,.0f} | TP2:${open_trade.tp2:,.0f} | SL:${open_trade.sl:,.0f}")
                
                elif short_signal:
                    open_trade = Trade("SHORT", price, now_utc, session)
                    print(f"🔴 SHORT Entry   @ ${price:,.0f} | TP1:${open_trade.tp1:,.0f} | TP2:${open_trade.tp2:,.0f} | SL:${open_trade.sl:,.0f}")
            
            time.sleep(60)
        
        except KeyboardInterrupt:
            print("\n⏹️  Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    run_bot()
