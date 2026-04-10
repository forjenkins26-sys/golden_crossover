"""
ENHANCED PAPER TRADING BOT - LONG + SHORT with RSI + Bollinger Bands
Real-time Binance data | No API keys needed | Bidirectional trading
Validated strategy from March 1-April 10, 2026 backtest (16 trades, +103.73% on Delta Exchange)
Updated: TP2 at 5%, Commission 0.05% (Delta Exchange India)
"""

import requests
import pandas as pd
import numpy as np
import csv
import time
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

LOT_SIZE = 0.10
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
REFRESH_RATE = 3600  # Check every 1 hour

# Indicators
RSI_PERIOD = 14
RSI_LONG_THRESHOLD = 25
RSI_SHORT_THRESHOLD = 75
BB_PERIOD = 20
BB_STD = 2.0

# Trade levels (TP2 updated to 5% for improved profitability)
TP1_LONG = 0.015
TP2_LONG = 0.05
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.05
SL_SHORT = 0.01

# Real-world costs (Delta Exchange India)
SLIPPAGE_PCT = 0.05  # 0.05% typical slippage on BTC
COMMISSION_TAKER = 0.05  # 0.05% taker fee on entry
COMMISSION_MAKER = 0.05  # 0.05% maker fee on exit
ENTRY_COST_PCT = SLIPPAGE_PCT + COMMISSION_TAKER  # 0.10% total entry cost
EXIT_COST_PCT = SLIPPAGE_PCT + COMMISSION_MAKER   # 0.10% total exit cost

TRAIL_PCT = 0.01

# Session filtering (UTC)
SESSIONS = {
    "Asian": {"start": 0.5, "end": 4.5},
    "London": {"start": 5.5, "end": 11.5},
    "NewYork": {"start": 12.5, "end": 17.5},
}

TRADES_CSV = 'paper_trades_enhanced.csv'

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(closes, period=14):
    """Calculate RSI(14)"""
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

# ============================================================================
# SESSION FILTERING
# ============================================================================

def get_session():
    """Get current session (UTC-based IST conversion)"""
    utc_now = datetime.utcnow()
    hour_decimal = utc_now.hour + utc_now.minute / 60.0
    
    for session_name, times in SESSIONS.items():
        if times["start"] <= hour_decimal < times["end"]:
            return session_name, True
    
    return "Off-Session", False

# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_klines(limit=100):
    """Fetch 1-hour candles from Binance public API"""
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
        print(f"Error fetching data: {e}")
        return None

# ============================================================================
# TRADE MANAGEMENT
# ============================================================================

class Trade:
    """Represents a single trade"""
    
    def __init__(self, entry_price, direction, session):
        self.entry_price = entry_price
        self.entry_time = datetime.utcnow()
        self.direction = direction
        self.session = session
        self.highest_price = entry_price if direction == "LONG" else entry_price
        self.lowest_price = entry_price
        self.trail_sl = None
        self.tp1_hit = False
        
        if direction == "LONG":
            self.tp1 = entry_price * (1 + TP1_LONG)
            self.tp2 = entry_price * (1 + TP2_LONG)
            self.sl = entry_price * (1 - SL_LONG)
        else:  # SHORT
            self.tp1 = entry_price * (1 - TP1_SHORT)
            self.tp2 = entry_price * (1 - TP2_SHORT)
            self.sl = entry_price * (1 + SL_SHORT)
    
    def check_exit(self, current_price):
        """Check if trade should exit. Returns (should_exit, exit_price, exit_reason, pnl, pnl_with_fees)"""
        
        if self.direction == "LONG":
            self.highest_price = max(self.highest_price, current_price)
            
            # TP2 exit
            if current_price >= self.tp2:
                clean_pnl = (self.tp2 - self.entry_price) * LOT_SIZE
                fees = self._calculate_fees(self.entry_price, self.tp2)
                pnl_with_fees = clean_pnl - fees
                return True, self.tp2, "TP2", clean_pnl, pnl_with_fees
            
            # TP1 trail activation and trailing stop
            if current_price >= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.trail_sl = current_price * (1 - TRAIL_PCT)
            
            if self.tp1_hit:
                self.trail_sl = max(self.trail_sl, current_price * (1 - TRAIL_PCT))
                if current_price <= self.trail_sl:
                    clean_pnl = (self.trail_sl - self.entry_price) * LOT_SIZE
                    fees = self._calculate_fees(self.entry_price, self.trail_sl)
                    pnl_with_fees = clean_pnl - fees
                    return True, self.trail_sl, "TP1_Trail", clean_pnl, pnl_with_fees
            
            # Hard SL
            if current_price <= self.sl:
                clean_pnl = (self.sl - self.entry_price) * LOT_SIZE
                fees = self._calculate_fees(self.entry_price, self.sl)
                pnl_with_fees = clean_pnl - fees
                return True, self.sl, "SL", clean_pnl, pnl_with_fees
        
        else:  # SHORT
            self.lowest_price = min(self.lowest_price, current_price)
            
            # TP2 exit
            if current_price <= self.tp2:
                clean_pnl = (self.entry_price - self.tp2) * LOT_SIZE
                fees = self._calculate_fees(self.entry_price, self.tp2)
                pnl_with_fees = clean_pnl - fees
                return True, self.tp2, "TP2", clean_pnl, pnl_with_fees
            
            # TP1 trail activation and trailing stop
            if current_price <= self.tp1 and not self.tp1_hit:
                self.tp1_hit = True
                self.trail_sl = current_price * (1 + TRAIL_PCT)
            
            if self.tp1_hit:
                self.trail_sl = min(self.trail_sl, current_price * (1 + TRAIL_PCT))
                if current_price >= self.trail_sl:
                    clean_pnl = (self.entry_price - self.trail_sl) * LOT_SIZE
                    fees = self._calculate_fees(self.entry_price, self.trail_sl)
                    pnl_with_fees = clean_pnl - fees
                    return True, self.trail_sl, "TP1_Trail", clean_pnl, pnl_with_fees
            
            # Hard SL
            if current_price >= self.sl:
                clean_pnl = (self.entry_price - self.sl) * LOT_SIZE
                fees = self._calculate_fees(self.entry_price, self.sl)
                pnl_with_fees = clean_pnl - fees
                return True, self.sl, "SL", clean_pnl, pnl_with_fees
        
        return False, None, None, None, None
    
    def _calculate_fees(self, entry_price, exit_price):
        """Calculate total fees for entry and exit"""
        entry_notional = entry_price * LOT_SIZE
        exit_notional = exit_price * LOT_SIZE
        entry_cost = entry_notional * (ENTRY_COST_PCT / 100)
        exit_cost = exit_notional * (EXIT_COST_PCT / 100)
        return entry_cost + exit_cost

# ============================================================================
# TRADE JOURNAL
# ============================================================================

def init_journal():
    """Initialize trade journal CSV"""
    if not os.path.exists(TRADES_CSV):
        with open(TRADES_CSV, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Entry_Time', 'Type', 'Entry_Price', 'TP1', 'TP2', 'SL',
                'Exit_Time', 'Exit_Price', 'Status', 'P&L_USD', 'P&L_%', 'Session'
            ])

def log_trade(entry_time, trade_type, entry_price, tp1, tp2, sl, exit_time, exit_price, status, pnl_usd, pnl_pct, session):
    """Log trade to CSV"""
    with open(TRADES_CSV, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            trade_type,
            f"{entry_price:.2f}",
            f"{tp1:.2f}",
            f"{tp2:.2f}",
            f"{sl:.2f}",
            exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            f"{exit_price:.2f}",
            status,
            f"{pnl_usd:.2f}",
            f"{pnl_pct:.2f}%",
            session
        ])

# ============================================================================
# MAIN BOT
# ============================================================================

def main():
    """Main trading loop"""
    
    init_journal()
    open_trade = None
    
    print("=" * 100)
    print("ENHANCED PAPER TRADING BOT - BIDIRECTIONAL")
    print("=" * 100)
    print(f"\nStarting paper trading at {datetime.utcnow()}")
    print(f"Lot size: {LOT_SIZE} BTC")
    print(f"Refresh rate: Every {REFRESH_RATE} seconds")
    print(f"Strategy: RSI(14) + Bollinger Bands(20,2)")
    print(f"\n⚠️  IMPORTANT: All P&L values logged include fees & slippage deduction:")
    print(f"   - Slippage: {SLIPPAGE_PCT}%")
    print(f"   - Entry (Taker): {COMMISSION_TAKER}%")
    print(f"   - Exit (Maker): {COMMISSION_MAKER}%")
    print(f"   - Total entry cost: {ENTRY_COST_PCT}%")
    print(f"   - Total exit cost: {EXIT_COST_PCT}%")
    print(f"   => Logged P&L = Clean P&L - Actual Fees Paid\n")
    
    while True:
        try:
            session, session_active = get_session()
            now = datetime.utcnow()
            
            # Fetch data
            df = fetch_klines(limit=100)
            if df is None:
                print(f"[{now}] Failed to fetch data, retrying...")
                time.sleep(REFRESH_RATE)
                continue
            
            current_price = float(df.iloc[-1]['close'])
            rsi = calculate_rsi(df['close'].values)
            bb_upper, bb_mid, bb_lower = calculate_bb(df['close'].values)
            
            print(f"\n[{now}] Session: {session} | Price: ${current_price:,.0f} | RSI: {rsi:.1f} | BB: [{bb_lower:.0f}, {bb_mid:.0f}, {bb_upper:.0f}]")
            
            # Check exit for open trade
            if open_trade:
                should_exit, exit_price, exit_reason, clean_pnl, pnl_with_fees = open_trade.check_exit(current_price)
                
                if should_exit:
                    pnl_pct = (pnl_with_fees / (open_trade.entry_price * LOT_SIZE)) * 100
                    log_trade(
                        open_trade.entry_time, open_trade.direction, open_trade.entry_price,
                        open_trade.tp1, open_trade.tp2, open_trade.sl,
                        now, exit_price, exit_reason, pnl_with_fees, pnl_pct, open_trade.session
                    )
                    print(f"   [EXIT] {open_trade.direction} {exit_reason} @ ${exit_price:,.0f} | P&L (after fees): ${pnl_with_fees:+.2f} ({pnl_pct:+.2f}%)")
                    open_trade = None
            
            # Check entry signals
            if not open_trade and session_active and rsi is not None:
                # LONG: RSI < 25 + Price < Lower BB
                if rsi < RSI_LONG_THRESHOLD and current_price < bb_lower:
                    open_trade = Trade(current_price, "LONG", session)
                    print(f"   [ENTRY] LONG @ ${current_price:,.0f} | RSI: {rsi:.1f} | TP1: ${open_trade.tp1:.0f} TP2: ${open_trade.tp2:.0f} SL: ${open_trade.sl:.0f}")
                
                # SHORT: RSI > 75 + Price > Upper BB
                elif rsi > RSI_SHORT_THRESHOLD and current_price > bb_upper:
                    open_trade = Trade(current_price, "SHORT", session)
                    print(f"   [ENTRY] SHORT @ ${current_price:,.0f} | RSI: {rsi:.1f} | TP1: ${open_trade.tp1:.0f} TP2: ${open_trade.tp2:.0f} SL: ${open_trade.sl:.0f}")
            
            # Wait before next check
            time.sleep(REFRESH_RATE)
        
        except KeyboardInterrupt:
            print("\n\nBot stopped by user.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(REFRESH_RATE)

if __name__ == "__main__":
    main()
