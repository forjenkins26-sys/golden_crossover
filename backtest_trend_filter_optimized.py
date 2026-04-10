"""
OPTIMIZED BACKTEST: January 1 - April 10, 2026 (100 days)
NEW: Added 200 EMA Trend Filter + Testing 4 Variants
Strategy: RSI(14) + Bollinger Bands(20,2) + 200 EMA Trend Filter
Goal: Transform mean-reversion strategy into trend-aligned system
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

def calculate_ema(series, period=200):
    """Calculate EMA"""
    return series.ewm(span=period, adjust=False).mean()

# ============================================================================
# SESSION FILTERING
# ============================================================================

def get_session(timestamp):
    """Get current session based on UTC time"""
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
# CONFIG
# ============================================================================

START_DATE = "2026-01-01"
END_DATE = "2026-04-10"
LOT_SIZE = 0.10
STARTING_CAPITAL = 500

RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
EMA_PERIOD = 200

TP1_LONG = 0.015
TP2_LONG = 0.05
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.05
SL_SHORT = 0.01

TRAIL_PCT = 0.01

# Fee simulation (Delta Exchange: 0.05% entry + 0.05% slippage = 0.10%, same on exit)
ENTRY_FEES_PCT = 0.10
EXIT_FEES_PCT = 0.10

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_backtest(df, rsi_long_threshold, rsi_short_threshold, sl_pct, use_trend_filter=True):
    """
    Run backtest with specified parameters
    
    Args:
        df: DataFrame with OHLC data
        rsi_long_threshold: RSI threshold for LONG entry (e.g., 25)
        rsi_short_threshold: RSI threshold for SHORT entry (e.g., 75)
        sl_pct: Stop loss percentage (e.g., 0.01 for 1%)
        use_trend_filter: Whether to use 200 EMA trend filter
    
    Returns:
        List of trades and final capital
    """
    
    # Calculate indicators
    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)
    df['EMA_200'] = calculate_ema(df['Close'], EMA_PERIOD)
    df = df.dropna()
    
    trades = []
    open_trade = None
    total_capital = STARTING_CAPITAL
    
    print(f"\n{'='*160}")
    print(f"RSI Thresholds: {rsi_long_threshold}/{rsi_short_threshold} | SL: {sl_pct*100:.1f}% | Trend Filter: {use_trend_filter}")
    print(f"{'='*160}")
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        timestamp = df.index[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        ema_200 = float(row['EMA_200'])
        
        session = get_session(timestamp)
        session_active = session != "Off-Session"
        
        # Check exit for open trade
        if open_trade:
            if open_trade['type'] == 'LONG':
                # TP2 exit
                if price >= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * LOT_SIZE - fees
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'LONG',
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"{open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"{exit_price:.2f}",
                        'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                        'Fees': f"{fees:+.2f}",
                        'Net_P&L': f"{pnl:+.2f}",
                        'Status': 'TP2',
                        'Session': open_trade['session'],
                        'EMA_200': f"{open_trade['ema_200']:.2f}"
                    })
                    open_trade = None
                
                # TP1 trailing stop
                elif price >= open_trade['tp1']:
                    if 'trail_sl' not in open_trade:
                        open_trade['trail_sl'] = price * (1 - TRAIL_PCT)
                    else:
                        open_trade['trail_sl'] = max(open_trade['trail_sl'], price * (1 - TRAIL_PCT))
                    
                    if price <= open_trade['trail_sl']:
                        exit_price = open_trade['trail_sl']
                        fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                        pnl = (exit_price - open_trade['entry']) * LOT_SIZE - fees
                        total_capital += pnl
                        
                        trades.append({
                            'Direction': 'LONG',
                            'Date_In': open_trade['date_in'],
                            'Time_In': open_trade['time_in'],
                            'Price_In': f"{open_trade['entry']:.2f}",
                            'Date_Out': timestamp.strftime('%Y-%m-%d'),
                            'Time_Out': timestamp.strftime('%H:%M'),
                            'Price_Out': f"{exit_price:.2f}",
                            'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                            'Fees': f"{fees:+.2f}",
                            'Net_P&L': f"{pnl:+.2f}",
                            'Status': 'TP1_Trail',
                            'Session': open_trade['session'],
                            'EMA_200': f"{open_trade['ema_200']:.2f}"
                        })
                        open_trade = None
                
                # Hard SL
                elif price <= open_trade['sl']:
                    exit_price = open_trade['sl']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * LOT_SIZE - fees
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'LONG',
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"{open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"{exit_price:.2f}",
                        'PTS': f"{exit_price - open_trade['entry']:+.2f}",
                        'Fees': f"{fees:+.2f}",
                        'Net_P&L': f"{pnl:+.2f}",
                        'Status': 'SL',
                        'Session': open_trade['session'],
                        'EMA_200': f"{open_trade['ema_200']:.2f}"
                    })
                    open_trade = None
            
            elif open_trade['type'] == 'SHORT':
                # TP2 exit
                if price <= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'SHORT',
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"{open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"{exit_price:.2f}",
                        'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                        'Fees': f"{fees:+.2f}",
                        'Net_P&L': f"{pnl:+.2f}",
                        'Status': 'TP2',
                        'Session': open_trade['session'],
                        'EMA_200': f"{open_trade['ema_200']:.2f}"
                    })
                    open_trade = None
                
                # TP1 trailing stop
                elif price <= open_trade['tp1']:
                    if 'trail_sl' not in open_trade:
                        open_trade['trail_sl'] = price * (1 + TRAIL_PCT)
                    else:
                        open_trade['trail_sl'] = min(open_trade['trail_sl'], price * (1 + TRAIL_PCT))
                    
                    if price >= open_trade['trail_sl']:
                        exit_price = open_trade['trail_sl']
                        fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                        pnl = (open_trade['entry'] - exit_price) * LOT_SIZE - fees
                        total_capital += pnl
                        
                        trades.append({
                            'Direction': 'SHORT',
                            'Date_In': open_trade['date_in'],
                            'Time_In': open_trade['time_in'],
                            'Price_In': f"{open_trade['entry']:.2f}",
                            'Date_Out': timestamp.strftime('%Y-%m-%d'),
                            'Time_Out': timestamp.strftime('%H:%M'),
                            'Price_Out': f"{exit_price:.2f}",
                            'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                            'Fees': f"{fees:+.2f}",
                            'Net_P&L': f"{pnl:+.2f}",
                            'Status': 'TP1_Trail',
                            'Session': open_trade['session'],
                            'EMA_200': f"{open_trade['ema_200']:.2f}"
                        })
                        open_trade = None
                
                # Hard SL
                elif price >= open_trade['sl']:
                    exit_price = open_trade['sl']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    total_capital += pnl
                    
                    trades.append({
                        'Direction': 'SHORT',
                        'Date_In': open_trade['date_in'],
                        'Time_In': open_trade['time_in'],
                        'Price_In': f"{open_trade['entry']:.2f}",
                        'Date_Out': timestamp.strftime('%Y-%m-%d'),
                        'Time_Out': timestamp.strftime('%H:%M'),
                        'Price_Out': f"{exit_price:.2f}",
                        'PTS': f"{open_trade['entry'] - exit_price:+.2f}",
                        'Fees': f"{fees:+.2f}",
                        'Net_P&L': f"{pnl:+.2f}",
                        'Status': 'SL',
                        'Session': open_trade['session'],
                        'EMA_200': f"{open_trade['ema_200']:.2f}"
                    })
                    open_trade = None
        
        # Check entry signals
        if not open_trade and session_active:
            # LONG: RSI oversold + Price at BBL + PRICE > 200 EMA (uptrend)
            long_signal = (rsi < rsi_long_threshold and price <= bb_lower)
            if use_trend_filter:
                long_signal = long_signal and (price > ema_200)
            
            if long_signal:
                entry_fees = (price * LOT_SIZE) * (ENTRY_FEES_PCT / 100)
                open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp1': price * (1 + TP1_LONG),
                    'tp2': price * (1 + TP2_LONG),
                    'sl': price * (1 - sl_pct),
                    'date_in': timestamp.strftime('%Y-%m-%d'),
                    'time_in': timestamp.strftime('%H:%M'),
                    'session': session,
                    'ema_200': ema_200
                }
            
            # SHORT: RSI overbought + Price at BBU + PRICE < 200 EMA (downtrend)
            short_signal = (rsi > rsi_short_threshold and price >= bb_upper)
            if use_trend_filter:
                short_signal = short_signal and (price < ema_200)
            
            if short_signal:
                entry_fees = (price * LOT_SIZE) * (ENTRY_FEES_PCT / 100)
                open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp1': price * (1 - TP1_SHORT),
                    'tp2': price * (1 - TP2_SHORT),
                    'sl': price * (1 + sl_pct),
                    'date_in': timestamp.strftime('%Y-%m-%d'),
                    'time_in': timestamp.strftime('%H:%M'),
                    'session': session,
                    'ema_200': ema_200
                }
    
    return trades, total_capital

# ============================================================================
# MAIN BACKTEST
# ============================================================================

print("\n" + "="*160)
print("OPTIMIZED BACKTEST: January 1 - April 10, 2026 (100 Days)")
print("Testing 4 Variants: Trend Filter Impact Analysis")
print("="*160)

# Download data once
print(f"\nDownloading BTC hourly data ({START_DATE} to {END_DATE})...")
df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
print(f"Loaded {len(df)} bars\n")

# Test variants
variants = [
    ("No Trend Filter (Baseline)", False, 25, 75, 0.01),
    ("200 EMA Filter + RSI 25/75", True, 25, 75, 0.01),
    ("200 EMA Filter + RSI 30/70", True, 30, 70, 0.01),
    ("200 EMA Filter + RSI 25/75 + 1.5% SL", True, 25, 75, 0.015),
]

results = []

for variant_name, use_filter, rsi_long, rsi_short, sl in variants:
    trades, final_capital = run_backtest(df.copy(), rsi_long, rsi_short, sl, use_filter)
    
    total_pnl = final_capital - STARTING_CAPITAL
    
    if len(trades) > 0:
        longs = [t for t in trades if t['Direction'] == 'LONG']
        shorts = [t for t in trades if t['Direction'] == 'SHORT']
        
        long_wins = len([t for t in longs if float(t['Net_P&L'].strip('$')) > 0])
        short_wins = len([t for t in shorts if float(t['Net_P&L'].strip('$')) > 0])
        total_wins = long_wins + short_wins
        
        win_rate = (total_wins / len(trades)) * 100 if len(trades) > 0 else 0
        
        results.append({
            'Variant': variant_name,
            'Trades': len(trades),
            'Longs': len(longs),
            'Shorts': len(shorts),
            'Wins': total_wins,
            'Win_Rate': f"{win_rate:.1f}%",
            'Final_Capital': f"${final_capital:,.2f}",
            'Total_P&L': f"${total_pnl:+.2f}",
            'Return_%': f"{(total_pnl/STARTING_CAPITAL)*100:+.1f}%"
        })
        
        print(f"\n{'─'*160}")
        print(f"VARIANT: {variant_name}")
        print(f"{'─'*160}")
        print(f"Trades: {len(trades)} | Longs: {len(longs)} | Shorts: {len(shorts)}")
        print(f"Wins: {total_wins}/{len(trades)} ({win_rate:.1f}%)")
        print(f"Final Capital: ${final_capital:,.2f} | P&L: ${total_pnl:+.2f} ({(total_pnl/STARTING_CAPITAL)*100:+.1f}%)\n")
        
        # Print last 10 trades
        print("Last 10 trades:")
        for trade in trades[-10:]:
            print(f"  {trade['Direction']:5} {trade['Date_In']} {trade['Time_In']} → {trade['Date_Out']} {trade['Time_Out']} | " + \
                  f"In: ${float(trade['Price_In']):,.0f} Out: ${float(trade['Price_Out']):,.0f} | " + \
                  f"PTS: {trade['PTS']:>6} | Net P&L: {trade['Net_P&L']:>8} | {trade['Status']:10} | EMA: {trade['EMA_200']}")

# ============================================================================
# SUMMARY COMPARISON
# ============================================================================

print("\n" + "="*160)
print("COMPARISON SUMMARY")
print("="*160)

summary_df = pd.DataFrame(results)
print(summary_df.to_string(index=False))

print("\n" + "="*160)
print("KEY INSIGHTS:")
print("="*160)
print("1. TREND FILTER IMPACT: Does 200 EMA reduce losing trades?")
print("2. RSI TUNING: Does 30/70 work better than 25/75?")
print("3. STOP LOSS: Does 1.5% SL work better than 1%?")
print("4. RECOMMENDATION: Which variant has best risk-adjusted returns?")
print("="*160)
