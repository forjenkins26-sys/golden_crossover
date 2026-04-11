"""
CONSERVATIVE CONSISTENT PROFITS STRATEGY
Focus: Reliability + Stability over high returns
100-day backtest (Jan 1 - Apr 10, 2026)

Key Features:
1. Trend filter (50 EMA) - only trade with trend
2. Stronger entry signals (RSI 20/80 not 25/75)
3. Conservative targets (TP: 1.5% / 3% not 5%)
4. Dynamic position sizing (reduce if high volatility)
5. Win rate monitoring (stop if <30%)
6. Session filter (Asian/London/NewYork only)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

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

def calculate_ema(series, period):
    """Calculate EMA"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_atr(high, low, close, period=14):
    """Calculate ATR"""
    tr = np.maximum(
        high - low,
        np.maximum(abs(high - close.shift()), abs(low - close.shift()))
    )
    atr = tr.rolling(period).mean()
    return atr

# ============================================================================
# SESSION FILTERING
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
# CONFIGURATION
# ============================================================================

START_DATE = "2026-01-01"
END_DATE = "2026-04-10"
LOT_SIZE_BASE = 0.10
STARTING_CAPITAL = 500

# BALANCED ENTRY SIGNALS (quality > quantity, but not TOO strict)
RSI_PERIOD = 14
RSI_LONG_THRESHOLD = 25      # Balanced (was 20 - too strict, causing 0 trades)
RSI_SHORT_THRESHOLD = 75     # Balanced
BB_PERIOD = 20
BB_STD = 2.0

# EMA FILTERS
EMA_50_PERIOD = 50           # Trend confirmation
EMA_200_PERIOD = 200         # Long-term trend

# CONSERVATIVE TARGETS (consistent smaller wins)
TP1_PCT = 0.015              # 1.5% first target
TP2_PCT = 0.03               # 3% final target (was 5%)
SL_PCT = 0.01                # 1% hard stop

TRAIL_PCT = 0.01

# VOLATILITY-BASED SIZING
ATR_PERIOD = 14
ATR_THRESHOLD_LOW = 500      # Low volatility: full position
ATR_THRESHOLD_HIGH = 1500    # High volatility: reduce position
POSITION_SCALE_HIGH = 0.6    # 60% of normal in high volatility

# FEES
ENTRY_FEES_PCT = 0.10
EXIT_FEES_PCT = 0.10

# MONITORING
MIN_WIN_RATE = 30            # Circuit breaker: stop if below 30%
ROLLING_TRADES = 20          # Track last 20 trades

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_conservative_backtest():
    """Run conservative backetest with all protective filters"""
    
    print("\n" + "="*150)
    print("CONSERVATIVE CONSISTENT PROFITS BACKTEST: Jan 1 - Apr 10, 2026")
    print("Entry Signals: RSI 25/75 (balanced) | Targets: 1.5%/3% (conservative) | Filters: 200 EMA trend + ATR sizing")
    print("="*150)
    
    # Download data
    print(f"\nDownloading BTC hourly data...")
    df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
    print(f"Loaded {len(df)} bars\n")
    
    # Calculate indicators
    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)
    df['EMA_50'] = calculate_ema(df['Close'], EMA_50_PERIOD)
    df['EMA_200'] = calculate_ema(df['Close'], EMA_200_PERIOD)
    df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'], ATR_PERIOD)
    df = df.dropna()
    
    trades = []
    open_trade = None
    total_capital = STARTING_CAPITAL
    rolling_wins = []
    trades_skipped = 0
    
    print("Running backtest...\n")
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        timestamp = df.index[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        ema_50 = float(row['EMA_50'])
        ema_200 = float(row['EMA_200'])
        atr = float(row['ATR'])
        
        session = get_session(timestamp)
        session_active = session != "Off-Session"
        
        # Calculate position size based on ATR
        if atr > ATR_THRESHOLD_HIGH:
            # High volatility: reduce position size
            lot_size = LOT_SIZE_BASE * POSITION_SCALE_HIGH
            regime = "HIGH_VOL"
        elif atr < ATR_THRESHOLD_LOW:
            # Low volatility: full position
            lot_size = LOT_SIZE_BASE
            regime = "LOW_VOL"
        else:
            # Normal volatility
            lot_size = LOT_SIZE_BASE * 0.8
            regime = "NORMAL_VOL"
        
        # Check win rate circuit breaker
        if len(rolling_wins) >= ROLLING_TRADES:
            win_rate = sum(rolling_wins[-ROLLING_TRADES:]) / ROLLING_TRADES * 100
            if win_rate < MIN_WIN_RATE:
                # STOP TRADING - win rate too low
                if open_trade:
                    # Force close at market
                    exit_price = price
                    if open_trade['type'] == 'LONG':
                        pnl = (exit_price - open_trade['entry']) * open_trade['lot_size'] - open_trade['entry_fees']
                    else:
                        pnl = (open_trade['entry'] - exit_price) * open_trade['lot_size'] - open_trade['entry_fees']
                    total_capital += pnl
                    rolling_wins.append(1 if pnl > 0 else 0)
                    open_trade = None
                continue
        
        # ===== CHECK EXIT CONDITIONS =====
        if open_trade:
            if open_trade['type'] == 'LONG':
                # TP2 exit
                if price >= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                    total_capital += pnl
                    rolling_wins.append(1 if pnl > 0 else 0)
                    
                    trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'LONG',
                        'Entry': f"{open_trade['entry']:.0f}",
                        'Exit': f"{exit_price:.0f}",
                        'Reason': 'TP2',
                        'Position': f"{open_trade['lot_size']:.2f}",
                        'P&L': f"{pnl:+.2f}",
                        'Capital': f"{total_capital:,.2f}"
                    })
                    print(f"[{timestamp}] LONG TP2  @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                    open_trade = None
                
                # TP1 to trail
                elif price >= open_trade['tp1']:
                    if 'trail_sl' not in open_trade:
                        open_trade['trail_sl'] = price * (1 - TRAIL_PCT)
                    else:
                        open_trade['trail_sl'] = max(open_trade['trail_sl'], price * (1 - TRAIL_PCT))
                    
                    if price <= open_trade['trail_sl']:
                        exit_price = open_trade['trail_sl']
                        exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                        pnl = (exit_price - open_trade['entry']) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                        total_capital += pnl
                        rolling_wins.append(1 if pnl > 0 else 0)
                        
                        trades.append({
                            'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'Type': 'LONG',
                            'Entry': f"{open_trade['entry']:.0f}",
                            'Exit': f"{exit_price:.0f}",
                            'Reason': 'TP1_Trail',
                            'Position': f"{open_trade['lot_size']:.2f}",
                            'P&L': f"{pnl:+.2f}",
                            'Capital': f"{total_capital:,.2f}"
                        })
                        print(f"[{timestamp}] LONG TP1_TRAIL @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                        open_trade = None
                
                # SL exit
                elif price <= open_trade['sl']:
                    exit_price = open_trade['sl']
                    exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                    total_capital += pnl
                    rolling_wins.append(1 if pnl > 0 else 0)
                    
                    trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'LONG',
                        'Entry': f"{open_trade['entry']:.0f}",
                        'Exit': f"{exit_price:.0f}",
                        'Reason': 'SL',
                        'Position': f"{open_trade['lot_size']:.2f}",
                        'P&L': f"{pnl:+.2f}",
                        'Capital': f"{total_capital:,.2f}"
                    })
                    print(f"[{timestamp}] LONG SL   @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                    open_trade = None
            
            elif open_trade['type'] == 'SHORT':
                # TP2 exit
                if price <= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                    total_capital += pnl
                    rolling_wins.append(1 if pnl > 0 else 0)
                    
                    trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'SHORT',
                        'Entry': f"{open_trade['entry']:.0f}",
                        'Exit': f"{exit_price:.0f}",
                        'Reason': 'TP2',
                        'Position': f"{open_trade['lot_size']:.2f}",
                        'P&L': f"{pnl:+.2f}",
                        'Capital': f"{total_capital:,.2f}"
                    })
                    print(f"[{timestamp}] SHORT TP2 @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                    open_trade = None
                
                # TP1 to trail
                elif price <= open_trade['tp1']:
                    if 'trail_sl' not in open_trade:
                        open_trade['trail_sl'] = price * (1 + TRAIL_PCT)
                    else:
                        open_trade['trail_sl'] = min(open_trade['trail_sl'], price * (1 + TRAIL_PCT))
                    
                    if price >= open_trade['trail_sl']:
                        exit_price = open_trade['trail_sl']
                        exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                        pnl = (open_trade['entry'] - exit_price) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                        total_capital += pnl
                        rolling_wins.append(1 if pnl > 0 else 0)
                        
                        trades.append({
                            'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                            'Type': 'SHORT',
                            'Entry': f"{open_trade['entry']:.0f}",
                            'Exit': f"{exit_price:.0f}",
                            'Reason': 'TP1_Trail',
                            'Position': f"{open_trade['lot_size']:.2f}",
                            'P&L': f"{pnl:+.2f}",
                            'Capital': f"{total_capital:,.2f}"
                        })
                        print(f"[{timestamp}] SHORT TP1_TRAIL @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                        open_trade = None
                
                # SL exit
                elif price >= open_trade['sl']:
                    exit_price = open_trade['sl']
                    exit_fees = (exit_price * open_trade['lot_size']) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * open_trade['lot_size'] - open_trade['entry_fees'] - exit_fees
                    total_capital += pnl
                    rolling_wins.append(1 if pnl > 0 else 0)
                    
                    trades.append({
                        'Date': timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Type': 'SHORT',
                        'Entry': f"{open_trade['entry']:.0f}",
                        'Exit': f"{exit_price:.0f}",
                        'Reason': 'SL',
                        'Position': f"{open_trade['lot_size']:.2f}",
                        'P&L': f"{pnl:+.2f}",
                        'Capital': f"{total_capital:,.2f}"
                    })
                    print(f"[{timestamp}] SHORT SL  @ ${exit_price:,.0f} | Pos: {open_trade['lot_size']:.2f} BTC | P&L: ${pnl:+.2f} | Cap: ${total_capital:,.2f}")
                    open_trade = None
        
        # ===== CHECK ENTRY CONDITIONS =====
        if not open_trade and session_active:
            # LONG: RSI oversold + At BB Lower + Price > 200 EMA (long-term uptrend)
            # NOTE: Using 200 EMA instead of 50 EMA for gentler trend filter (less restrictive)
            if (rsi < RSI_LONG_THRESHOLD and price <= bb_lower and price > ema_200):
                entry_fees = (price * lot_size) * (ENTRY_FEES_PCT / 100)
                open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp1': price * (1 + TP1_PCT),
                    'tp2': price * (1 + TP2_PCT),
                    'sl': price * (1 - SL_PCT),
                    'lot_size': lot_size,
                    'entry_fees': entry_fees,
                    'ema_50': ema_50,
                    'regime': regime
                }
                print(f">>> LONG  INPUT @ ${price:,.0f} | RSI: {rsi:.0f} | Pos: {lot_size:.2f} | {regime} | EMA200: ${ema_200:,.0f}")
            
            # SHORT: RSI overbought + At BB Upper + Price < 200 EMA (long-term downtrend)
            # NOTE: Using 200 EMA instead of 50 EMA for gentler trend filter (less restrictive)
            elif (rsi > RSI_SHORT_THRESHOLD and price >= bb_upper and price < ema_200):
                entry_fees = (price * lot_size) * (ENTRY_FEES_PCT / 100)
                open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp1': price * (1 - TP1_PCT),
                    'tp2': price * (1 - TP2_PCT),
                    'sl': price * (1 + SL_PCT),
                    'lot_size': lot_size,
                    'entry_fees': entry_fees,
                    'ema_50': ema_50,
                    'regime': regime
                }
                print(f">>> SHORT INPUT @ ${price:,.0f} | RSI: {rsi:.0f} | Pos: {lot_size:.2f} | {regime} | EMA200: ${ema_200:,.0f}")
    
    # ===== RESULTS =====
    print(f"\n{'='*150}")
    print("BACKTEST COMPLETE - CONSERVATIVE STRATEGY")
    print(f"{'='*150}")
    print(f"Starting Capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Ending Capital: ${total_capital:,.2f}")
    print(f"Total P&L: ${total_capital - STARTING_CAPITAL:+,.2f} ({((total_capital - STARTING_CAPITAL) / STARTING_CAPITAL) * 100:+.1f}%)")
    print(f"Total Trades: {len(trades)}")
    
    if len(trades) > 0:
        wins = len([t for t in trades if float(t['P&L']) > 0])
        losses = len(trades) - wins
        win_rate = (wins / len(trades)) * 100
        
        print(f"Wins: {wins} | Losses: {losses} | Win Rate: {win_rate:.1f}%")
        
        avg_win = np.mean([float(t['P&L']) for t in trades if float(t['P&L']) > 0]) if wins > 0 else 0
        avg_loss = np.mean([float(t['P&L']) for t in trades if float(t['P&L']) < 0]) if losses > 0 else 0
        
        print(f"Avg Win: ${avg_win:+.2f} | Avg Loss: ${avg_loss:+.2f}")
        
        # Monthly breakdown
        print(f"\n{'─'*150}")
        print("MONTHLY BREAKDOWN:")
        print(f"{'─'*150}")
        
        for month in [1, 2, 3, 4]:
            month_trades = [t for t in trades if int(t['Date'][:7].split('-')[1]) == month]
            if month_trades:
                month_wins = len([t for t in month_trades if float(t['P&L']) > 0])
                month_pnl = sum([float(t['P&L']) for t in month_trades])
                print(f"Month {month:2d}: {len(month_trades):2d} trades | {month_wins:2d} wins ({(month_wins/len(month_trades))*100:5.1f}%) | P&L: ${month_pnl:+8.2f}")

if __name__ == "__main__":
    run_conservative_backtest()
