"""
Paper Trading Bot OPTIMIZED: Seasonal/Calendar-Based Trading
Only trades during historically profitable months (Mar 1 - Apr 10)
Implements careful position sizing and stop-loss rules
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import csv

# ============================================================================
# CONFIGURATION
# ============================================================================

# SEASONAL FILTER: Only trade these months
TRADING_START_MONTH = 3      # March
TRADING_START_DAY = 1
TRADING_END_MONTH = 4        # April
TRADING_END_DAY = 10

# Position sizing
LOT_SIZE = 0.10  # 0.1 BTC per trade
STARTING_CAPITAL = 500

# Risk management
MAX_MONTHLY_LOSS = -200      # Stop trading if monthly loss exceeds this
POSITION_RISK_PCT = 1.0      # Risk 1% per trade

# Indicators
RSI_PERIOD = 14
RSI_LONG_THRESHOLD = 25
RSI_SHORT_THRESHOLD = 75
BB_PERIOD = 20
BB_STD = 2.0
EMA_PERIOD = 200

# Exit targets
TP1_LONG = 0.015
TP2_LONG = 0.05
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.05
SL_SHORT = 0.01

TRAIL_PCT = 0.01

# Fees (Delta Exchange: 0.05% entry + 0.05% slippage on both sides)
ENTRY_FEES_PCT = 0.10
EXIT_FEES_PCT = 0.10

# Session filtering
TRADEABLE_SESSIONS = ["Asian", "London", "NewYork"]

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(series, period=14):
    """Calculate RSI"""
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

def calculate_ema(series, period=200):
    """Calculate EMA"""
    return series.ewm(span=period, adjust=False).mean()

# ============================================================================
# SESSION DETECTION
# ============================================================================

def get_session(timestamp):
    """Get trading session"""
    hour_utc = timestamp.hour
    minute_utc = timestamp.minute
    hour_decimal = hour_utc + (minute_utc / 60.0)
    
    if 0.5 <= hour_decimal < 4.5:
        return "Asian"
    elif 5.5 <= hour_decimal < 11.5:
        return "London"
    elif 12.5 <= hour_decimal < 17.5:
        return "NewYork"
    else:
        return "Off-Session"

# ============================================================================
# TRADING FILTERS
# ============================================================================

def is_trading_season(timestamp):
    """Check if currently in trading season (Mar 1 - Apr 10)"""
    month = timestamp.month
    day = timestamp.day
    
    if month < TRADING_START_MONTH or month > TRADING_END_MONTH:
        return False
    
    if month == TRADING_START_MONTH and day < TRADING_START_DAY:
        return False
    
    if month == TRADING_END_MONTH and day > TRADING_END_DAY:
        return False
    
    return True

def is_session_active(timestamp):
    """Check if session is active"""
    session = get_session(timestamp)
    return session in TRADEABLE_SESSIONS

# ============================================================================
# MAIN BOT
# ============================================================================

class SeasonalPaperTradingBot:
    def __init__(self):
        self.open_trade = None
        self.trades = []
        self.capital = STARTING_CAPITAL
        self.monthly_pnl = 0
        self.trades_this_month = []
        self.last_price = None
        self.last_timestamp = None
        
    def calculate_fees(self, entry_price, exit_price):
        """Calculate total fees for round-trip trade"""
        entry_notional = entry_price * LOT_SIZE
        exit_notional = exit_price * LOT_SIZE
        entry_cost = entry_notional * (ENTRY_FEES_PCT / 100)
        exit_cost = exit_notional * (EXIT_FEES_PCT / 100)
        return entry_cost + exit_cost
    
    def check_monthly_stop(self, timestamp):
        """Check if we've hit monthly loss limit"""
        current_month = timestamp.month
        
        # Reset monthly tracking if new month
        if self.trades_this_month and self.trades_this_month[0]['Date'][:7] != timestamp.strftime('%Y-%m'):
            self.monthly_pnl = 0
            self.trades_this_month = []
        
        # Check if hit max loss
        if self.monthly_pnl < MAX_MONTHLY_LOSS:
            return False  # Don't trade
        
        return True
    
    def process_candle(self, timestamp, price, rsi, bb_upper, bb_lower, ema_200):
        """Process one candle bar"""
        
        # Check trading conditions
        trading_season = is_trading_season(timestamp)
        session_active = is_session_active(timestamp)
        monthly_ok = self.check_monthly_stop(timestamp)
        
        # ===== CHECK EXIT CONDITIONS =====
        if self.open_trade:
            if self.open_trade['type'] == 'LONG':
                # TP2 exit
                if price >= self.open_trade['tp2']:
                    exit_price = self.open_trade['tp2']
                    fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                    pnl = (exit_price - self.open_trade['entry']) * LOT_SIZE - fees
                    
                    self.trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'LONG',
                        'Entry': f"${self.open_trade['entry']:,.0f}",
                        'Exit': f"${exit_price:,.0f}",
                        'Reason': 'TP2',
                        'Fees': f"${fees:,.2f}",
                        'P&L': f"${pnl:+,.2f}"
                    })
                    
                    self.capital += pnl
                    self.monthly_pnl += pnl
                    self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                    
                    print(f"[{timestamp}] LONG TP2  @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                    self.open_trade = None
                
                # TP1 trailing stop
                elif price >= self.open_trade['tp1']:
                    if 'trail_sl' not in self.open_trade:
                        self.open_trade['trail_sl'] = price * (1 - TRAIL_PCT)
                    else:
                        self.open_trade['trail_sl'] = max(self.open_trade['trail_sl'], price * (1 - TRAIL_PCT))
                    
                    if price <= self.open_trade['trail_sl']:
                        exit_price = self.open_trade['trail_sl']
                        fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                        pnl = (exit_price - self.open_trade['entry']) * LOT_SIZE - fees
                        
                        self.trades.append({
                            'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'Type': 'LONG',
                            'Entry': f"${self.open_trade['entry']:,.0f}",
                            'Exit': f"${exit_price:,.0f}",
                            'Reason': 'TP1_Trail',
                            'Fees': f"${fees:,.2f}",
                            'P&L': f"${pnl:+,.2f}"
                        })
                        
                        self.capital += pnl
                        self.monthly_pnl += pnl
                        self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                        
                        print(f"[{timestamp}] LONG TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                        self.open_trade = None
                
                # Hard SL
                elif price <= self.open_trade['sl']:
                    exit_price = self.open_trade['sl']
                    fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                    pnl = (exit_price - self.open_trade['entry']) * LOT_SIZE - fees
                    
                    self.trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'LONG',
                        'Entry': f"${self.open_trade['entry']:,.0f}",
                        'Exit': f"${exit_price:,.0f}",
                        'Reason': 'SL',
                        'Fees': f"${fees:,.2f}",
                        'P&L': f"${pnl:+,.2f}"
                    })
                    
                    self.capital += pnl
                    self.monthly_pnl += pnl
                    self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                    
                    print(f"[{timestamp}] LONG SL   @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                    self.open_trade = None
            
            elif self.open_trade['type'] == 'SHORT':
                # TP2 exit
                if price <= self.open_trade['tp2']:
                    exit_price = self.open_trade['tp2']
                    fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                    pnl = (self.open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    
                    self.trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'SHORT',
                        'Entry': f"${self.open_trade['entry']:,.0f}",
                        'Exit': f"${exit_price:,.0f}",
                        'Reason': 'TP2',
                        'Fees': f"${fees:,.2f}",
                        'P&L': f"${pnl:+,.2f}"
                    })
                    
                    self.capital += pnl
                    self.monthly_pnl += pnl
                    self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                    
                    print(f"[{timestamp}] SHORT TP2 @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                    self.open_trade = None
                
                # TP1 trailing stop
                elif price <= self.open_trade['tp1']:
                    if 'trail_sl' not in self.open_trade:
                        self.open_trade['trail_sl'] = price * (1 + TRAIL_PCT)
                    else:
                        self.open_trade['trail_sl'] = min(self.open_trade['trail_sl'], price * (1 + TRAIL_PCT))
                    
                    if price >= self.open_trade['trail_sl']:
                        exit_price = self.open_trade['trail_sl']
                        fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                        pnl = (self.open_trade['entry'] - exit_price) * LOT_SIZE - fees
                        
                        self.trades.append({
                            'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'Type': 'SHORT',
                            'Entry': f"${self.open_trade['entry']:,.0f}",
                            'Exit': f"${exit_price:,.0f}",
                            'Reason': 'TP1_Trail',
                            'Fees': f"${fees:,.2f}",
                            'P&L': f"${pnl:+,.2f}"
                        })
                        
                        self.capital += pnl
                        self.monthly_pnl += pnl
                        self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                        
                        print(f"[{timestamp}] SHORT TP1_TRAIL @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                        self.open_trade = None
                
                # Hard SL
                elif price >= self.open_trade['sl']:
                    exit_price = self.open_trade['sl']
                    fees = self.calculate_fees(self.open_trade['entry'], exit_price)
                    pnl = (self.open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    
                    self.trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'SHORT',
                        'Entry': f"${self.open_trade['entry']:,.0f}",
                        'Exit': f"${exit_price:,.0f}",
                        'Reason': 'SL',
                        'Fees': f"${fees:,.2f}",
                        'P&L': f"${pnl:+,.2f}"
                    })
                    
                    self.capital += pnl
                    self.monthly_pnl += pnl
                    self.trades_this_month.append({'Date': timestamp.strftime('%Y-%m-%d'), 'P&L': pnl})
                    
                    print(f"[{timestamp}] SHORT SL  @ ${exit_price:,.0f} | P&L: ${pnl:+.2f} | Capital: ${self.capital:,.2f}")
                    self.open_trade = None
        
        # ===== CHECK ENTRY CONDITIONS =====
        if not self.open_trade and trading_season and session_active and monthly_ok:
            # LONG: RSI oversold + Price at BBL
            # NOTE: During seasonal window (Mar-Apr), we DON'T use 200 EMA filter
            # because this period is historically choppy/ranging and works for mean-reversion
            if (rsi < RSI_LONG_THRESHOLD and price <= bb_lower):
                self.open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp1': price * (1 + TP1_LONG),
                    'tp2': price * (1 + TP2_LONG),
                    'sl': price * (1 - SL_LONG),
                    'entry_time': timestamp
                }
                print(f">>> LONG  ENTRY  @ ${price:,.0f} | TP1: ${self.open_trade['tp1']:,.0f} TP2: ${self.open_trade['tp2']:,.0f} SL: ${self.open_trade['sl']:,.0f}")
            
            # SHORT: RSI overbought + Price at BBU
            # NOTE: During seasonal window (Mar-Apr), we DON'T use 200 EMA filter
            elif (rsi > RSI_SHORT_THRESHOLD and price >= bb_upper):
                self.open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp1': price * (1 - TP1_SHORT),
                    'tp2': price * (1 - TP2_SHORT),
                    'sl': price * (1 + SL_SHORT),
                    'entry_time': timestamp
                }
                print(f">>> SHORT ENTRY  @ ${price:,.0f} | TP1: ${self.open_trade['tp1']:,.0f} TP2: ${self.open_trade['tp2']:,.0f} SL: ${self.open_trade['sl']:,.0f}")
    
    def run(self, start_date="2026-03-01", end_date="2026-04-10"):
        """Run the bot"""
        print(f"\n{'='*150}")
        print(f"SEASONAL PAPER TRADING BOT: {start_date} to {end_date}")
        print(f"Only trades Mar 1 - Apr 10 | Risk: 1% per trade | Position: 0.1 BTC")
        print(f"{'='*150}\n")
        
        # Download data
        df = yf.download("BTC-USD", start=start_date, end=end_date, interval="1h", progress=False)
        
        # Calculate indicators
        df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
        df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)
        df['EMA_200'] = calculate_ema(df['Close'], EMA_PERIOD)
        df = df.dropna()
        
        # Process each candle
        for idx in range(len(df)):
            row = df.iloc[idx]
            timestamp = df.index[idx]
            price = float(row['Close'])
            rsi = float(row['RSI'])
            bb_upper = float(row['BB_Upper'])
            bb_lower = float(row['BB_Lower'])
            ema_200 = float(row['EMA_200'])
            
            self.process_candle(timestamp, price, rsi, bb_upper, bb_lower, ema_200)
        
        # Summary
        print(f"\n{'='*150}")
        print(f"BACKTEST COMPLETE")
        print(f"{'='*150}")
        print(f"Starting Capital: ${STARTING_CAPITAL:,.2f}")
        print(f"Ending Capital: ${self.capital:,.2f}")
        print(f"Total P&L: ${self.capital - STARTING_CAPITAL:+,.2f} ({((self.capital - STARTING_CAPITAL) / STARTING_CAPITAL) * 100:+.1f}%)")
        print(f"Total Trades: {len(self.trades)}")
        
        if len(self.trades) > 0:
            wins = len([t for t in self.trades if float(t['P&L'].strip('$')) > 0])
            print(f"Win Rate: {wins}/{len(self.trades)} ({(wins/len(self.trades))*100:.1f}%)")

# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    bot = SeasonalPaperTradingBot()
    bot.run()
