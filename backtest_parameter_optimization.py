"""
PROFESSIONAL PARAMETER OPTIMIZATION
Test multiple combinations systematically to find BEST profitable logic
Like real traders do: test, measure, optimize, repeat
"""

import pandas as pd
import numpy as np
import yfinance as yf
from itertools import product

# ============================================================================
# INDICATORS (Same as before)
# ============================================================================

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=20, num_std=2.0):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def get_session(timestamp):
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
# BACKTEST WITH PARAMETERS
# ============================================================================

def backtest_with_params(df, rsi_long, rsi_short, tp1_pct, tp2_pct, sl_pct, use_200_ema=True, session_filter=True):
    """
    Backtest with specific parameters
    Returns: (total_pnl, num_trades, win_rate, profit_factor, max_dd)
    """
    
    df_copy = df.copy()
    df_copy['RSI'] = calculate_rsi(df_copy['Close'], 14)
    df_copy['BB_Upper'], df_copy['BB_Mid'], df_copy['BB_Lower'] = calculate_bollinger_bands(df_copy['Close'], 20, 2.0)
    df_copy['EMA_200'] = calculate_ema(df_copy['Close'], 200)
    df_copy = df_copy.dropna()
    
    trades = []
    open_trade = None
    total_capital = 500
    
    for idx in range(len(df_copy)):
        row = df_copy.iloc[idx]
        timestamp = df_copy.index[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        bb_upper = float(row['BB_Upper'])
        bb_lower = float(row['BB_Lower'])
        ema_200 = float(row['EMA_200'])
        
        # Session filter
        session = get_session(timestamp)
        session_active = session != "Off-Session" if session_filter else True
        
        # Exit logic
        if open_trade:
            if open_trade['type'] == 'LONG':
                if price >= open_trade['tp2']:
                    pnl = (open_trade['tp2'] - open_trade['entry']) * 0.1 - 0.02 * 0.1
                    total_capital += pnl
                    trades.append({'pnl': pnl, 'type': 'win'})
                    open_trade = None
                elif price <= open_trade['sl']:
                    pnl = (open_trade['sl'] - open_trade['entry']) * 0.1 - 0.02 * 0.1
                    total_capital += pnl
                    trades.append({'pnl': pnl, 'type': 'loss'})
                    open_trade = None
            elif open_trade['type'] == 'SHORT':
                if price <= open_trade['tp2']:
                    pnl = (open_trade['entry'] - open_trade['tp2']) * 0.1 - 0.02 * 0.1
                    total_capital += pnl
                    trades.append({'pnl': pnl, 'type': 'win'})
                    open_trade = None
                elif price >= open_trade['sl']:
                    pnl = (open_trade['entry'] - open_trade['sl']) * 0.1 - 0.02 * 0.1
                    total_capital += pnl
                    trades.append({'pnl': pnl, 'type': 'loss'})
                    open_trade = None
        
        # Entry logic
        if not open_trade and session_active:
            long_signal = (rsi < rsi_long and price <= bb_lower)
            if use_200_ema:
                long_signal = long_signal and (price > ema_200)
            
            if long_signal:
                open_trade = {
                    'type': 'LONG',
                    'entry': price,
                    'tp2': price * (1 + tp2_pct),
                    'sl': price * (1 - sl_pct)
                }
            
            short_signal = (rsi > rsi_short and price >= bb_upper)
            if use_200_ema:
                short_signal = short_signal and (price < ema_200)
            
            if short_signal:
                open_trade = {
                    'type': 'SHORT',
                    'entry': price,
                    'tp2': price * (1 - tp2_pct),
                    'sl': price * (1 + sl_pct)
                }
    
    # Calculate metrics
    if len(trades) == 0:
        return 0, 0, 0, 0, 0
    
    pnls = [t['pnl'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    
    total_pnl = sum(pnls)
    win_rate = (wins / len(trades)) * 100 if len(trades) > 0 else 0
    
    total_wins = sum(p for p in pnls if p > 0)
    total_losses = abs(sum(p for p in pnls if p < 0))
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    # Max drawdown
    cumulative = []
    cum = 0
    for p in pnls:
        cum += p
        cumulative.append(cum)
    
    max_dd = 0
    peak = 0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    
    return total_pnl, len(trades), win_rate, profit_factor, max_dd

# ============================================================================
# MAIN OPTIMIZATION
# ============================================================================

print("\n" + "="*200)
print("PROFESSIONAL PARAMETER OPTIMIZATION: Finding Best Combination")
print("="*200)

# Download data once
print("\nDownloading BTC data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)
print(f"Loaded {len(df)} bars\n")

# Parameter combinations to test
rsi_long_options = [20, 25, 30]      # Different RSI thresholds for LONG
rsi_short_options = [70, 75, 80]     # Different RSI thresholds for SHORT
tp_combinations = [
    (0.015, 0.03),   # Tight: 1.5% / 3%
    (0.015, 0.05),   # Current: 1.5% / 5%
    (0.02, 0.04),    # Medium: 2% / 4%
    (0.02, 0.06),    # Wide: 2% / 6%
]
sl_options = [0.005, 0.008, 0.01, 0.015, 0.02]  # Different stop loss %
ema_options = [True, False]  # With/without 200 EMA filter
session_filter_options = [True]  # Session filter always on

# Track results
results = []

total_tests = (len(rsi_long_options) * len(rsi_short_options) * len(tp_combinations) * 
               len(sl_options) * len(ema_options) * len(session_filter_options))

print(f"Testing {total_tests} parameter combinations...\n")

test_count = 0
for rsi_long, rsi_short, (tp1, tp2), sl, use_ema, use_session in product(
    rsi_long_options, rsi_short_options, tp_combinations, 
    sl_options, ema_options, session_filter_options
):
    test_count += 1
    
    pnl, trades, win_rate, pf, max_dd = backtest_with_params(
        df, rsi_long, rsi_short, tp1, tp2, sl, use_ema, use_session
    )
    
    if trades > 0:  # Only store if we got trades
        results.append({
            'RSI_Long': rsi_long,
            'RSI_Short': rsi_short,
            'TP1%': f"{tp1*100:.1f}",
            'TP2%': f"{tp2*100:.1f}",
            'SL%': f"{sl*100:.1f}",
            'EMA_Filter': 'Yes' if use_ema else 'No',
            'Trades': trades,
            'P&L': f"${pnl:+.2f}",
            'Win%': f"{win_rate:.1f}%",
            'ProfitFactor': f"{pf:.2f}",
            'MaxDD': f"${max_dd:+.2f}",
            'Score': pnl * pf if pf > 0 else pnl  # Reward high profit + high profit factor
        })
    
    if test_count % 50 == 0:
        print(f"  ... {test_count}/{total_tests} tests completed")

# Sort by score (best first)
results_sorted = sorted(results, key=lambda x: x['Score'], reverse=True)

print(f"\n{'='*200}")
print("TOP 15 BEST PARAMETER COMBINATIONS (Sorted by Score)")
print(f"{'='*200}\n")

results_df = pd.DataFrame(results_sorted[:15])
print(results_df.to_string(index=False))

print(f"\n{'='*200}")
print("TOP COMBINATION ANALYSIS")
print(f"{'='*200}\n")

if len(results_sorted) > 0:
    top = results_sorted[0]
    print(f"🏆 BEST STRATEGY:")
    print(f"  RSI Thresholds: LONG < {top['RSI_Long']}, SHORT > {top['RSI_Short']}")
    print(f"  Targets: TP1 @ {top['TP1%']}, TP2 @ {top['TP2%']}")
    print(f"  Stop Loss: {top['SL%']}")
    print(f"  200 EMA Filter: {top['EMA_Filter']}")
    print(f"\n  Results:")
    print(f"    Trades: {top['Trades']}")
    print(f"    P&L: {top['P&L']}")
    print(f"    Win Rate: {top['Win%']}")
    print(f"    Profit Factor: {top['ProfitFactor']}")
    print(f"    Max Drawdown: {top['MaxDD']}")
    print(f"    Score: {top['Score']:.2f}")

print(f"\n{'='*200}")
print("COMPARISON: Original vs Top 5 Variants")
print(f"{'='*200}\n")

comparison_data = {
    'Strategy': ['Original (25/75, 5%, 1%)', 'Conservative (25/75, 3%, 1%)', 'Seasonal Only (Mar-Apr)'] + 
                [f"Rank #{i+1}" for i in range(5)],
    'P&L': ['+$518.63', '-$310.62', '+$518.63'] + [results_sorted[i]['P&L'] for i in range(min(5, len(results_sorted)))],
    'Win%': ['37.5%', '20%', '37.5%'] + [results_sorted[i]['Win%'] for i in range(min(5, len(results_sorted)))],
}

comp_df = pd.DataFrame(comparison_data)
print(comp_df.to_string(index=False))

print(f"\n{'='*200}")
print("KEY INSIGHTS")
print(f"{'='*200}")
print("""
What professional traders look for:
1. Profit Factor > 1.5 (total wins >> total losses)
2. Win Rate > 35% (with proper position sizing)
3. Max Drawdown < 30% (can recover quickly)
4. Consistent trades > 20 (proves it's not luck)
5. Score = P&L × Profit Factor (balances profit AND consistency)

Your job: Pick the top strategy that has:
  ✓ Positive P&L
  ✓ Profit Factor > 1.5
  ✓ At least 15+ trades
  ✓ Drawdown < 40%
""")

print("="*200)
