"""
🤖 PAPER TRADING BOT - BTC 1-Hour RSI + Bollinger Band Strategy
Production-Grade. No API keys needed. Free Binance public API.
Simulates trades with real-time data. Logs everything to CSV.
"""

import requests
import pandas as pd
import numpy as np
import csv
import time
from datetime import datetime
import os
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

LOT_SIZE = 0.10  # Flat lot sizing (proven from backtest)
SYMBOL = "BTCUSDT"
INTERVAL = "1h"

# Trading parameters
RSI_PERIOD = 14
RSI_THRESHOLD = 25
BB_PERIOD = 20
BB_STD = 2.0
TP1_PCT = 0.015  # +1.5%
TP2_PCT = 0.035  # +3.5%
SL_PCT = 0.010   # -1.0%
TRAIL_PCT = 0.01  # Trail by 1%

# ============================================================================
# SESSION DEFINITIONS (IST to UTC Conversion)
# ============================================================================
# IST = UTC + 5:30
# So: IST time - 5:30 = UTC time

RSI_OVERBOUGHT = 75  # For SHORT entries
EMA_PERIOD = 200  # Trend filter

SESSIONS = {
    "Asian": {
        "name": "Asian (06:00-10:00 IST)",
        "utc_start": 0.5,      # 06:00 IST = 00:30 UTC
        "utc_end": 4.5,        # 10:00 IST = 04:30 UTC
        "enabled": True
    },
    "London": {
        "name": "London (11:00-17:00 IST)",
        "utc_start": 5.5,      # 11:00 IST = 05:30 UTC
        "utc_end": 11.5,       # 17:00 IST = 11:30 UTC
        "enabled": True
    },
    "New York": {
        "name": "New York (18:00-23:00 IST)",
        "utc_start": 12.5,     # 18:00 IST = 12:30 UTC
        "utc_end": 17.5,       # 23:00 IST = 17:30 UTC
        "enabled": True
    }
}

def get_session():
    """
    Returns current trading session based on UTC time.
    
    Returns:
        tuple: (session_name, is_active) 
        - session_name: str (e.g., "London", "New York", "Asian")
        - is_active: bool (True if session is enabled and current time is in range)
    """
    utc_now = datetime.utcnow()
    hour_decimal = utc_now.hour + utc_now.minute / 60.0
    
    for session_key, session_info in SESSIONS.items():
        if not session_info["enabled"]:
            continue
        
        # Handle sessions that wrap around midnight
        if session_info["utc_start"] < session_info["utc_end"]:
            # Normal case (doesn't wrap)
            if session_info["utc_start"] <= hour_decimal < session_info["utc_end"]:
                return session_key, True
        else:
            # Wraps around midnight (utc_start > utc_end)
            if hour_decimal >= session_info["utc_start"] or hour_decimal < session_info["utc_end"]:
                return session_key, True
    
    return "Off-Session", False

# CSV file paths
TRADES_CSV = 'paper_trades.csv'
LOG_FILE = 'paper_trading.log'

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(series, period=RSI_PERIOD):
    """Calculate RSI"""
    if len(series) < period + 1:
        return pd.Series([np.nan] * len(series))
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=BB_PERIOD, num_std=BB_STD):
    """Calculate Bollinger Bands"""
    if len(series) < period:
        return (pd.Series([np.nan] * len(series)), 
                pd.Series([np.nan] * len(series)), 
                pd.Series([np.nan] * len(series)))
    
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower

def calculate_ema(series, period=EMA_PERIOD):
    """Calculate EMA for trend detection"""
    if len(series) < period:
        return pd.Series([np.nan] * len(series))
    return series.ewm(span=period, adjust=False).mean()

# ============================================================================
# DATA FETCHING (BINANCE PUBLIC API - NO AUTH)
# ============================================================================

def fetch_klines():
    """Fetch last 100 1H candles from Binance (NO API KEY NEEDED)"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': SYMBOL,
            'interval': INTERVAL,
            'limit': 100
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'
        ])
        
        # Convert to numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
        
        # Convert timestamps
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
        
        return df
    
    except Exception as e:
        print(f"⚠️ Error fetching data: {e}")
        return None

# ============================================================================
# TRADE MANAGEMENT
# ============================================================================

class Trade:
    """Track a single trade (LONG or SHORT)"""
    def __init__(self, entry_price, entry_time, lot_size, session, direction="LONG"):
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.lot_size = lot_size
        self.session = session
        self.direction = direction  # "LONG" or "SHORT"
        
        # Calculate levels based on direction
        if direction == "LONG":
            self.tp1 = entry_price * (1 + TP1_PCT)           # +1.5%
            self.tp2 = entry_price * (1 + TP2_PCT)           # +3.5%
            self.sl = entry_price * (1 - SL_PCT)             # -1.0%
        else:  # SHORT
            self.tp1 = entry_price * (1 - TP1_PCT)           # -1.5%
            self.tp2 = entry_price * (1 - TP2_PCT)           # -3.5%
            self.sl = entry_price * (1 + SL_PCT)             # +1.0%
        
        # State
        self.tp1_hit = False
        self.trail_sl = None
        self.extreme_price = entry_price  # Highest (LONG) or Lowest (SHORT)
        
        # Exit
        self.exit_price = None
        self.exit_time = None
        self.exit_reason = None
    
    def update_extreme(self, high, low):
        """Update extreme price for trailing (highest for LONG, lowest for SHORT)"""
        if self.direction == "LONG":
            if high > self.extreme_price:
                self.extreme_price = high
                if self.tp1_hit:
                    new_trail = high * (1 - TRAIL_PCT)
                    if new_trail > (self.trail_sl or 0):
                        self.trail_sl = new_trail
        else:  # SHORT
            if low < self.extreme_price:
                self.extreme_price = low
                if self.tp1_hit:
                    new_trail = low * (1 + TRAIL_PCT)
                    if new_trail < (self.trail_sl or float('inf')):
                        self.trail_sl = new_trail
    
    def check_exit(self, high, low, close):
        """Check if any exit condition is hit"""
        
        if self.direction == "LONG":
            return self._check_exit_long(high, low)
        else:  # SHORT
            return self._check_exit_short(high, low)
    
    def _check_exit_long(self, high, low):
        """Check exit conditions for LONG"""
        # TP2: Book profit
        if high >= self.tp2:
            return "TP2", self.tp2
        
        # TP1: Start trailing
        if not self.tp1_hit and high >= self.tp1:
            self.tp1_hit = True
            self.trail_sl = high * (1 - TRAIL_PCT)
        
        # Trail SL: Exit on trailing stop
        if self.tp1_hit and self.trail_sl and low <= self.trail_sl:
            return "TP1_TRAIL", self.trail_sl
        
        # SL: Hard stop loss
        if low <= self.sl:
            return "SL", self.sl
        
        return None, None
    
    def _check_exit_short(self, high, low):
        """Check exit conditions for SHORT"""
        # TP2: Book profit
        if low <= self.tp2:
            return "TP2", self.tp2
        
        # TP1: Start trailing
        if not self.tp1_hit and low <= self.tp1:
            self.tp1_hit = True
            self.trail_sl = low * (1 + TRAIL_PCT)
        
        # Trail SL: Exit on trailing stop
        if self.tp1_hit and self.trail_sl and high >= self.trail_sl:
            return "TP1_TRAIL", self.trail_sl
        
        # SL: Hard stop loss
        if high >= self.sl:
            return "SL", self.sl
        
        return None, None
    
    def close(self, exit_price, exit_time, exit_reason):
        """Close the trade"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = exit_reason
    
    def get_pnl(self):
        """Calculate P&L"""
        if self.exit_price is None:
            return 0
        
        if self.direction == "LONG":
            price_move = self.exit_price - self.entry_price
        else:  # SHORT
            price_move = self.entry_price - self.exit_price
        
        return price_move * self.lot_size
    
    def get_pnl_pct(self):
        """Calculate P&L %"""
        if self.exit_price is None:
            return 0
        
        if self.direction == "LONG":
            return ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            return ((self.entry_price - self.exit_price) / self.entry_price) * 100

# ============================================================================
# LOGGING & PERSISTENCE
# ============================================================================

def log_message(msg):
    """Log message to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(full_msg + "\n")
    except:
        pass

def save_trade(trade):
    """Save trade to CSV"""
    try:
        file_exists = Path(TRADES_CSV).exists()
        
        with open(TRADES_CSV, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            if not file_exists:
                writer.writerow([
                    'Open_Date', 'Open_Time_UTC', 'Entry_Price', 'Lot_Size',
                    'Close_Date', 'Close_Time_UTC', 'Exit_Price',
                    'P&L_USD', 'P&L_%', 'Exit_Reason', 'Session', 'Duration'
                ])
            
            # Trade row
            duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600
            writer.writerow([
                trade.entry_time.strftime("%Y-%m-%d"),
                trade.entry_time.strftime("%H:%M:%S"),
                f"${trade.entry_price:,.2f}",
                f"{trade.lot_size:.2f}",
                trade.exit_time.strftime("%Y-%m-%d"),
                trade.exit_time.strftime("%H:%M:%S"),
                f"${trade.exit_price:,.2f}",
                f"${trade.get_pnl():+.2f}",
                f"{trade.get_pnl_pct():+.2f}%",
                trade.exit_reason,
                trade.session,
                f"{duration:.1f}h"
            ])
    except Exception as e:
        print(f"⚠️ Error saving trade: {e}")

# ============================================================================
# MAIN BOT ENGINE
# ============================================================================

def run_bot():
    """Main trading bot loop"""
    
    log_message("=" * 90)
    log_message("🤖 PAPER TRADING BOT STARTED")
    log_message("=" * 90)
    log_message(f"📡 Using Binance Public API (NO AUTH NEEDED)")
    log_message(f"💰 Starting Capital: $500 | Lot Size: {LOT_SIZE} BTC")
    log_message(f"📊 Strategy: RSI({RSI_PERIOD}) + Bollinger Bands({BB_PERIOD},{BB_STD}) + 200 EMA Trend Filter")
    log_message(f"   LONG:  RSI < {RSI_THRESHOLD} + Price < Lower BB + Price > 200 EMA")
    log_message(f"   SHORT: RSI > {RSI_OVERBOUGHT} + Price > Upper BB + Price < 200 EMA")
    log_message(f"🎯 TP1: ±{TP1_PCT*100:.1f}% (with trail) | TP2: ±{TP2_PCT*100:.1f}% (instant) | SL: ±{SL_PCT*100:.1f}%")
    log_message("=" * 90)
    
    position = None
    total_pnl = 0
    trades_count = 0
    wins = 0
    losses = 0
    
    while True:
        try:
            # Fetch latest data
            df = fetch_klines()
            if df is None or len(df) < 30:
                print("⚠️ Insufficient data, retrying...")
                time.sleep(60)
                continue
            
            # Calculate indicators
            df['rsi'] = calculate_rsi(df['close'], RSI_PERIOD)
            df['bb_upper'], df['bb_mid'], df['bb_lower'] = calculate_bollinger_bands(
                df['close'], BB_PERIOD, BB_STD
            )
            df['ema200'] = calculate_ema(df['close'], EMA_PERIOD)
            
            # Last confirmed candle (not current forming one)
            last_confirmed = df.iloc[-2]
            current_candle = df.iloc[-1]
            
            # Extract values
            last_price = float(last_confirmed['close'])
            current_price = float(current_candle['close'])
            current_high = float(current_candle['high'])
            current_low = float(current_candle['low'])
            rsi_val = float(last_confirmed['rsi']) if pd.notna(last_confirmed['rsi']) else 50
            bb_upper = float(last_confirmed['bb_upper']) if pd.notna(last_confirmed['bb_upper']) else 0
            bb_lower = float(last_confirmed['bb_lower']) if pd.notna(last_confirmed['bb_lower']) else 0
            ema200 = float(last_confirmed['ema200']) if pd.notna(last_confirmed['ema200']) else 0
            
            # Determine trend
            trend = "📈 Bullish" if last_price > ema200 else "📉 Bearish"
            
            # Get current session and check if allowed
            session_name, session_allowed = get_session()
            
            # Display status line
            long_signal = (rsi_val < RSI_THRESHOLD and last_price < bb_lower and last_price > ema200)
            short_signal = (rsi_val > RSI_OVERBOUGHT and last_price > bb_upper and last_price < ema200)
            signal_indicator = ""
            if long_signal:
                signal_indicator = " 🔴 LONG SIGNAL"
            elif short_signal:
                signal_indicator = " 🔴 SHORT SIGNAL"
            
            status_line = (
                f"[{current_candle['close_time'].strftime('%H:%M')} {session_name} {trend}] "
                f"BTC: ${current_price:,.0f} | RSI: {rsi_val:5.1f} | "
                f"P&L: ${total_pnl:+,.2f}{signal_indicator}"
            )
            
            # ===== NO POSITION =====
            if position is None:
                # LONG Entry: RSI < 25 + Price < Lower BB + Price > 200 EMA
                if (long_signal and session_allowed):
                    position = Trade(
                        entry_price=last_price,
                        entry_time=current_candle['close_time'],
                        lot_size=LOT_SIZE,
                        session=session_name,
                        direction="LONG"
                    )
                    
                    log_message(
                        f"{status_line}\n"
                        f"   📊 LONG ENTRY @ ${last_price:,.2f} | "
                        f"TP1: ${position.tp1:,.2f} | "
                        f"TP2: ${position.tp2:,.2f} | "
                        f"SL: ${position.sl:,.2f}"
                    )
                
                # SHORT Entry: RSI > 75 + Price > Upper BB + Price < 200 EMA
                elif (short_signal and session_allowed):
                    position = Trade(
                        entry_price=last_price,
                        entry_time=current_candle['close_time'],
                        lot_size=LOT_SIZE,
                        session=session_name,
                        direction="SHORT"
                    )
                    
                    log_message(
                        f"{status_line}\n"
                        f"   📊 SHORT ENTRY @ ${last_price:,.2f} | "
                        f"TP1: ${position.tp1:,.2f} | "
                        f"TP2: ${position.tp2:,.2f} | "
                        f"SL: ${position.sl:,.2f}"
                    )
                else:
                    print(status_line, end='\r')
            
            # ===== POSITION OPEN =====
            else:
                # Update extreme price for trailing
                position.update_extreme(current_high, current_low)
                
                # Check exit
                exit_reason, exit_price = position.check_exit(current_high, current_low, current_price)
                
                if exit_reason:
                    position.close(exit_price, current_candle['close_time'], exit_reason)
                    pnl = position.get_pnl()
                    pnl_pct = position.get_pnl_pct()
                    
                    total_pnl += pnl
                    trades_count += 1
                    
                    if pnl > 0:
                        wins += 1
                        emoji = "✅"
                    else:
                        losses += 1
                        emoji = "❌"
                    
                    # Save to CSV
                    save_trade(position)
                    
                    log_message(
                        f"{status_line}\n"
                        f"   {emoji} {position.direction} {exit_reason} @ ${exit_price:,.2f} | "
                        f"P&L: ${pnl:+.2f} ({pnl_pct:+.2f}%) | "
                        f"Total P&L: ${total_pnl:+,.2f} | "
                        f"Trades: {trades_count} (W: {wins} L: {losses})"
                    )
                    
                    position = None
                else:
                    # Trade still open, show unrealized
                    if position.direction == "LONG":
                        unrealized = (current_price - position.entry_price) * position.lot_size
                    else:  # SHORT
                        unrealized = (position.entry_price - current_price) * position.lot_size
                    
                    duration_hours = (current_candle['close_time'] - position.entry_time).total_seconds() / 3600
                    
                    print(
                        f"{status_line} | "
                        f"{position.direction} | Unrealized: ${unrealized:+.2f} | "
                        f"Duration: {duration_hours:.1f}h",
                        end='\r'
                    )
        
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(60)
            continue
        
        # Wait before next check
        time.sleep(60)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot terminated")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
