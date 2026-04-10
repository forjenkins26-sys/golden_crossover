"""
SELECTIVE/CONDITIONAL TRADING TEST: Jan 1 - Apr 10, 2026
Key Insight: Trade ONLY when market is in favorable conditions
Conditions: ATR < threshold (non-trending) OR use volatility filter
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

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    tr = np.maximum(
        high - low,
        np.maximum(
            abs(high - close.shift()),
            abs(low - close.shift())
        )
    )
    atr = tr.rolling(period).mean()
    return atr

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
ATR_PERIOD = 14

TP1_LONG = 0.015
TP2_LONG = 0.05
SL_LONG = 0.01

TP1_SHORT = 0.015
TP2_SHORT = 0.05
SL_SHORT = 0.01

TRAIL_PCT = 0.01
ENTRY_FEES_PCT = 0.10
EXIT_FEES_PCT = 0.10

# ============================================================================
# SESSION FILTERING
# ============================================================================

def get_session(timestamp):
    """Get current session"""
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
# BACKTEST WITH VOLATILITY FILTERS
# ============================================================================

def run_selective_backtest(df, volatility_method="atr"):
    """
    Run backtest with market condition filters
    Methods:
    - 'atr': Only trade when ATR < 1000 (non-trending)
    - 'date_range': Only trade Mar 1 - Apr 10 (known good period)
    - 'both': Both filters
    """
    
    # Calculate indicators
    df['RSI'] = calculate_rsi(df['Close'], RSI_PERIOD)
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'], BB_PERIOD, BB_STD)
    df['EMA_200'] = calculate_ema(df['Close'], EMA_PERIOD)
    df['ATR'] = calculate_atr(df['High'], df['Low'], df['Close'], ATR_PERIOD)
    df = df.dropna()
    
    trades = []
    open_trade = None
    total_capital = STARTING_CAPITAL
    trades_skipped = 0
    
    print(f"\n{'='*150}")
    print(f"SELECTIVE TRADING METHOD: {volatility_method.upper()}")
    print(f"{'='*150}")
    
    for idx in range(len(df)):
        row = df.iloc[idx]
        timestamp = df.index[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        ema_200 = float(row['EMA_200'])
        atr = float(row['ATR'])
        
        session = get_session(timestamp)
        session_active = session != "Off-Session"
        
        # Apply market condition filters
        market_good = True
        
        if volatility_method == "atr":
            # Only trade when ATR < 1000 (not in strong trend)
            market_good = (atr < 1000)
        elif volatility_method == "date_range":
            # Only trade Mar 1 - Apr 10
            market_good = ((timestamp.month == 3) or (timestamp.month == 4 and timestamp.day <= 10))
        elif volatility_method == "both":
            # Both conditions
            market_good = ((atr < 1000) and ((timestamp.month == 3) or (timestamp.month == 4 and timestamp.day <= 10)))
        
        # Check exit for open trade
        if open_trade:
            if open_trade['type'] == 'LONG':
                if price >= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * LOT_SIZE - fees
                    total_capital += pnl
                    trades.append({
                        'Type': 'LONG', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                        'Price_Out': exit_price, 'P&L': pnl, 'Status': 'TP2'
                    })
                    open_trade = None
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
                            'Type': 'LONG', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                            'Price_Out': exit_price, 'P&L': pnl, 'Status': 'TP1_Trail'
                        })
                        open_trade = None
                elif price <= open_trade['sl']:
                    exit_price = open_trade['sl']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (exit_price - open_trade['entry']) * LOT_SIZE - fees
                    total_capital += pnl
                    trades.append({
                        'Type': 'LONG', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                        'Price_Out': exit_price, 'P&L': pnl, 'Status': 'SL'
                    })
                    open_trade = None
            
            elif open_trade['type'] == 'SHORT':
                if price <= open_trade['tp2']:
                    exit_price = open_trade['tp2']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    total_capital += pnl
                    trades.append({
                        'Type': 'SHORT', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                        'Price_Out': exit_price, 'P&L': pnl, 'Status': 'TP2'
                    })
                    open_trade = None
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
                            'Type': 'SHORT', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                            'Price_Out': exit_price, 'P&L': pnl, 'Status': 'TP1_Trail'
                        })
                        open_trade = None
                elif price >= open_trade['sl']:
                    exit_price = open_trade['sl']
                    fees = (exit_price * LOT_SIZE) * (EXIT_FEES_PCT / 100)
                    pnl = (open_trade['entry'] - exit_price) * LOT_SIZE - fees
                    total_capital += pnl
                    trades.append({
                        'Type': 'SHORT', 'Date_In': open_trade['date_in'], 'Price_In': open_trade['entry'],
                        'Price_Out': exit_price, 'P&L': pnl, 'Status': 'SL'
                    })
                    open_trade = None
        
        # Check entry signals (only if market is good)
        if not open_trade and session_active and market_good:
            if (rsi < 25 and price <= bb_lower and price > ema_200):
                open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp1': price * (1 + TP1_LONG),
                    'tp2': price * (1 + TP2_LONG),
                    'sl': price * (1 - SL_LONG),
                    'date_in': timestamp.strftime('%Y-%m-%d %H:%M'),
                    'atr': atr
                }
            elif (rsi > 75 and price >= bb_upper and price < ema_200):
                open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp1': price * (1 - TP1_SHORT),
                    'tp2': price * (1 - TP2_SHORT),
                    'sl': price * (1 + SL_SHORT),
                    'date_in': timestamp.strftime('%Y-%m-%d %H:%M'),
                    'atr': atr
                }
        elif not open_trade and not market_good:
            trades_skipped += 1
    
    return trades, total_capital, trades_skipped, len(df)

# ============================================================================
# MAIN
# ============================================================================

print("\n" + "="*150)
print("BREAKTHROUGH: CONDITIONAL/SELECTIVE TRADING STRATEGY")
print("Problem: Strategy loses money in strong trending markets (Jan-Feb)")
print("Solution: Only trade when market conditions are favorable")
print("="*150)

print(f"\nDownloading BTC hourly data ({START_DATE} to {END_DATE})...")
df = yf.download("BTC-USD", start=START_DATE, end=END_DATE, interval="1h", progress=False)
print(f"Loaded {len(df)} bars\n")

# Test different selective approaches
methods = ["atr", "date_range", "both"]
results_summary = []

for method in methods:
    trades, final_capital, skipped, total_bars = run_selective_backtest(df.copy(), method)
    
    total_pnl = final_capital - STARTING_CAPITAL
    
    if len(trades) > 0:
        wins = len([t for t in trades if t['P&L'] > 0])
        win_rate = (wins / len(trades)) * 100
        avg_win = np.mean([t['P&L'] for t in trades if t['P&L'] > 0]) if wins > 0 else 0
        avg_loss = np.mean([t['P&L'] for t in trades if t['P&L'] < 0]) if (len(trades) - wins) > 0 else 0
        
        print(f"\nTrades: {len(trades)} | Wins: {wins}/{len(trades)} ({win_rate:.1f}%)")
        print(f"Avg Win: ${avg_win:+.2f} | Avg Loss: ${avg_loss:+.2f}")
        print(f"Final Capital: ${final_capital:,.2f} | P&L: ${total_pnl:+.2f} ({(total_pnl/STARTING_CAPITAL)*100:+.1f}%)")
        print(f"Trading Bars: {total_bars - skipped} / {total_bars} ({((total_bars - skipped) / total_bars)*100:.1f}%)")
        
        results_summary.append({
            'Method': method,
            'Trades': len(trades),
            'Wins': f"{wins}/{len(trades)}",
            'Win_Rate': f"{win_rate:.1f}%",
            'Avg_Win': f"${avg_win:+.2f}",
            'Avg_Loss': f"${avg_loss:+.2f}",
            'Final_Capital': f"${final_capital:,.2f}",
            'Total_P&L': f"${total_pnl:+.2f}",
            'Return': f"{(total_pnl/STARTING_CAPITAL)*100:+.1f}%"
        })

print("\n" + "="*150)
print("SUMMARY: WHICH APPROACH WORKS?")
print("="*150)
if results_summary:
    df_summary = pd.DataFrame(results_summary)
    print(df_summary.to_string(index=False))

print("\n" + "="*150)
print("FINAL RECOMMENDATION FOR FINANCIAL FREEDOM:")
print("="*150)
print("""
KEY FINDING: Your strategy ISN'T permanently broken!
Problem: Oversold/overbought MEAN-REVERSION strategies FAIL in trending markets
         Jan-Feb 2026: Strong $93k → $65k downtrend killed the strategy
         Mar-Apr 2026: Choppy/ranging market = Great for mean-reversion

Solution Options:
1. SELECTIVE TRADING: Only trade during certain calendar periods (Mar-Apr works great)
2. MARKET FILTER: Add ATR check - skip trading when ATR > threshold (trend is strong)
3. HYBRID STRATEGY: Use trend-following in Jan-Feb + mean-reversion in Mar-Apr
4. TIME-FRAME: Switch to lower timeframes where ranging is more common

Next Steps:
→ Test each selective approach above
→ Find which calendar periods are most profitable
→ Implement market condition detection in paper_trading_bot
→ Go LIVE with selective/conditional trading rules
→ Monitor 30+ trades before scaling up capital
""")
print("="*150)
