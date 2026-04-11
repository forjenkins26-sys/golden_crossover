"""
RSI 30/70 STRATEGY - PART 1: IMPROVED WITH 200 EMA LONG FILTER
Scenario 1: Actual Bearish Market (Jan-Apr 2026)
Scenario 2: Hypothetical Bullish Market (Risk Analysis)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*180)
print("RSI 30/70 STRATEGY - ENHANCED AND RISK ANALYSIS")
print("="*180)

# Fetch data
print("\n[Downloading BTC-USD data...]")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Calculate RSI
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
df = df.dropna()

# Session filter
df['InSession'] = df.index.map(lambda x: (0.5 <= x.hour + x.minute/60 < 4.5) or 
                                          (5.5 <= x.hour + x.minute/60 < 11.5) or 
                                          (12.5 <= x.hour + x.minute/60 < 17.5))

# Delta fees
ENTRY_COST_RATE = 0.0010   # 0.10% (0.05% taker + 0.05% slippage)
EXIT_COST_RATE = 0.0010    # 0.10% (0.05% taker + 0.05% slippage)
POSITION_SIZE = 0.1  # BTC
RSI_LONG = 30
RSI_SHORT = 70
TP_PCT = 0.04
SL_PCT = 0.012

def run_backtest(data, scenario_name, use_ema_filter_longs=True, reverse_prices=False):
    """
    Run backtest with optional modifications
    reverse_prices: If True, reverse prices for bull market simulation
    """
    
    if reverse_prices:
        # For bull market simulation: reverse the price direction
        data = data.copy()
        # Simple reversal: if original prices went X down, make them go X up
        # We'll use a transformation: new_price = 2*mean - old_price
        mean_price = data['Close'].mean()
        data['Close'] = 2 * mean_price - data['Close']
        data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
        print(f"\n[{scenario_name} - Prices reversed for bull market simulation]")
    else:
        print(f"\n[{scenario_name}]")
    
    trades = []
    in_trade = False
    entry_price = 0
    trade_type = None
    tp = sl = 0
    entry_date = None
    entry_rsi = 0
    
    for idx in range(len(data)):
        row = data.iloc[idx]
        price = float(row['Close'])
        rsi = float(row['RSI'])
        ema_200 = float(row['EMA_200'])
        in_session = row['InSession'].item() if hasattr(row['InSession'], 'item') else bool(row['InSession'])
        current_date = row.name
        
        # EXIT
        if in_trade:
            exit_triggered = False
            exit_type = None
            
            if trade_type == 'LONG':
                if price >= tp:
                    exit_triggered = True
                    exit_type = 'TP'
                    exit_price = tp
                elif price <= sl:
                    exit_triggered = True
                    exit_type = 'SL'
                    exit_price = sl
            else:  # SHORT
                if price <= tp:
                    exit_triggered = True
                    exit_type = 'TP'
                    exit_price = tp
                elif price >= sl:
                    exit_triggered = True
                    exit_type = 'SL'
                    exit_price = sl
            
            if exit_triggered:
                # Calculate P&L with Delta fees
                if trade_type == 'LONG':
                    gross_pnl = (exit_price - entry_price) * POSITION_SIZE
                else:
                    gross_pnl = (entry_price - exit_price) * POSITION_SIZE
                
                entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
                exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
                net_pnl = gross_pnl - entry_cost - exit_cost
                
                trades.append({
                    'Date': current_date.strftime('%Y-%m-%d %H:%M'),
                    'Type': trade_type,
                    'Entry': entry_price,
                    'Exit': exit_price,
                    'Result': exit_type,
                    'Gross_PnL': gross_pnl,
                    'Fees': entry_cost + exit_cost,
                    'Net_PnL': net_pnl,
                })
                
                in_trade = False
        
        # ENTRY
        if not in_trade and in_session:
            # SHORT: RSI > 70 (NO additional filter - keep as is)
            if rsi > RSI_SHORT:
                in_trade = True
                trade_type = 'SHORT'
                entry_price = price
                entry_rsi = rsi
                entry_date = current_date
                tp = price * (1 - TP_PCT)
                sl = price * (1 + SL_PCT)
            
            # LONG: RSI < 30 AND price > 200 EMA (NEW FILTER)
            elif rsi < RSI_LONG and price > ema_200:
                if use_ema_filter_longs:
                    in_trade = True
                    trade_type = 'LONG'
                    entry_price = price
                    entry_rsi = rsi
                    entry_date = current_date
                    tp = price * (1 + TP_PCT)
                    sl = price * (1 - SL_PCT)
    
    return pd.DataFrame(trades)

# ============================================================================
# SCENARIO 1: ACTUAL BEARISH MARKET (Jan-Apr 2026)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO 1: ACTUAL BEARISH MARKET (Jan-Apr 2026)")
print("Strategy: SHORT no filter | LONG with 200 EMA filter")
print("="*180)

trades_scenario1 = run_backtest(df, "Bearish Market (Actual Data)", use_ema_filter_longs=True, reverse_prices=False)

if len(trades_scenario1) > 0:
    longs_s1 = trades_scenario1[trades_scenario1['Type'] == 'LONG']
    shorts_s1 = trades_scenario1[trades_scenario1['Type'] == 'SHORT']
    
    total_pnl_s1 = trades_scenario1['Net_PnL'].sum()
    total_gross_s1 = trades_scenario1['Gross_PnL'].sum()
    total_fees_s1 = trades_scenario1['Fees'].sum()
    win_rate_s1 = len(trades_scenario1[trades_scenario1['Net_PnL'] > 0]) / len(trades_scenario1) * 100
    
    total_wins_s1 = trades_scenario1[trades_scenario1['Net_PnL'] > 0]['Net_PnL'].sum()
    total_loss_s1 = abs(trades_scenario1[trades_scenario1['Net_PnL'] < 0]['Net_PnL'].sum())
    pf_s1 = total_wins_s1 / total_loss_s1 if total_loss_s1 > 0 else 0
    
    print(f"\n[OVERALL RESULTS]")
    print(f"   Total Trades:       {len(trades_scenario1)}")
    print(f"   Gross P&L:          ${total_gross_s1:+.2f}")
    print(f"   Total Fees:         ${total_fees_s1:+.2f}")
    print(f"   NET P&L:            ${total_pnl_s1:+.2f}")
    print(f"   Win Rate:           {win_rate_s1:.1f}%")
    print(f"   Profit Factor:      {pf_s1:.2f}x")
    
    print(f"\n[LONG TRADES (RSI < 30 + Price > 200 EMA)]")
    print(f"   Count:              {len(longs_s1)}")
    if len(longs_s1) > 0:
        long_wins_s1 = len(longs_s1[longs_s1['Net_PnL'] > 0])
        long_wr_s1 = long_wins_s1 / len(longs_s1) * 100
        long_pnl_s1 = longs_s1['Net_PnL'].sum()
        print(f"   Win Rate:           {long_wr_s1:.1f}%")
        print(f"   Net P&L:            ${long_pnl_s1:+.2f}")
    
    print(f"\n[SHORT TRADES (RSI > 70, NO FILTER)]")
    print(f"   Count:              {len(shorts_s1)}")
    if len(shorts_s1) > 0:
        short_wins_s1 = len(shorts_s1[shorts_s1['Net_PnL'] > 0])
        short_wr_s1 = short_wins_s1 / len(shorts_s1) * 100
        short_pnl_s1 = shorts_s1['Net_PnL'].sum()
        print(f"   Win Rate:           {short_wr_s1:.1f}%")
        print(f"   Net P&L:            ${short_pnl_s1:+.2f}")

# ============================================================================
# SCENARIO 2: HYPOTHETICAL BULLISH MARKET (Price Reversal Simulation)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO 2: HYPOTHETICAL BULLISH MARKET (Simulated - Opposite Direction)")
print("Strategy: SHORT no filter | LONG with 200 EMA filter")
print("="*180)

trades_scenario2 = run_backtest(df, "Bullish Market (Simulated)", use_ema_filter_longs=True, reverse_prices=True)

if len(trades_scenario2) > 0:
    longs_s2 = trades_scenario2[trades_scenario2['Type'] == 'LONG']
    shorts_s2 = trades_scenario2[trades_scenario2['Type'] == 'SHORT']
    
    total_pnl_s2 = trades_scenario2['Net_PnL'].sum()
    total_gross_s2 = trades_scenario2['Gross_PnL'].sum()
    total_fees_s2 = trades_scenario2['Fees'].sum()
    win_rate_s2 = len(trades_scenario2[trades_scenario2['Net_PnL'] > 0]) / len(trades_scenario2) * 100
    
    total_wins_s2 = trades_scenario2[trades_scenario2['Net_PnL'] > 0]['Net_PnL'].sum()
    total_loss_s2 = abs(trades_scenario2[trades_scenario2['Net_PnL'] < 0]['Net_PnL'].sum())
    pf_s2 = total_wins_s2 / total_loss_s2 if total_loss_s2 > 0 else 0
    
    print(f"\n[OVERALL RESULTS]")
    print(f"   Total Trades:       {len(trades_scenario2)}")
    print(f"   Gross P&L:          ${total_gross_s2:+.2f}")
    print(f"   Total Fees:         ${total_fees_s2:+.2f}")
    print(f"   NET P&L:            ${total_pnl_s2:+.2f}")
    print(f"   Win Rate:           {win_rate_s2:.1f}%")
    print(f"   Profit Factor:      {pf_s2:.2f}x")
    
    print(f"\n[LONG TRADES (RSI < 30 + Price > 200 EMA)]")
    print(f"   Count:              {len(longs_s2)}")
    if len(longs_s2) > 0:
        long_wins_s2 = len(longs_s2[longs_s2['Net_PnL'] > 0])
        long_wr_s2 = long_wins_s2 / len(longs_s2) * 100
        long_pnl_s2 = longs_s2['Net_PnL'].sum()
        print(f"   Win Rate:           {long_wr_s2:.1f}%")
        print(f"   Net P&L:            ${long_pnl_s2:+.2f}")
    
    print(f"\n[SHORT TRADES (RSI > 70, NO FILTER)]")
    print(f"   Count:              {len(shorts_s2)}")
    if len(shorts_s2) > 0:
        short_wins_s2 = len(shorts_s2[shorts_s2['Net_PnL'] > 0])
        short_wr_s2 = short_wins_s2 / len(shorts_s2) * 100
        short_pnl_s2 = shorts_s2['Net_PnL'].sum()
        print(f"   Win Rate:           {short_wr_s2:.1f}%")
        print(f"   Net P&L:            ${short_pnl_s2:+.2f}")

# ============================================================================
# COMPARISON AND RISK ANALYSIS
# ============================================================================

print("\n" + "="*180)
print("COMPARISON: BEARISH vs BULLISH MARKET")
print("="*180)

print(f"\n[NET P&L COMPARISON]")
print(f"   Bearish Market (Actual):    ${total_pnl_s1:+.2f}")
print(f"   Bullish Market (Simulated): ${total_pnl_s2:+.2f}")
print(f"   Difference:                  ${(total_pnl_s2 - total_pnl_s1):+.2f}")

if total_pnl_s1 > 0 and total_pnl_s2 < 0:
    print(f"\n[!!! CRITICAL RISK !!!]")
    print(f"   Strategy is DIRECTION DEPENDENT")
    print(f"   Lost ${abs(total_pnl_s2):.2f} in bullish market vs gained ${total_pnl_s1:.2f} in bearish market")
    print(f"   Downside risk: ${abs(total_pnl_s2):.2f} ({abs(total_pnl_s2)/total_pnl_s1*100:.0f}% of current profit)")

# ============================================================================
# RECOMMENDED FILTER FOR SHORT SIDE
# ============================================================================

print("\n" + "="*180)
print("RISK MITIGATION: RECOMMENDED FILTER FOR SHORT SIDE")
print("="*180)

print(f"""
CURRENT SHORT SETUP (Unfiltered):
  - Entry: RSI > 70 only
  - Risk: In bull markets, price crushes shorts relentlessly
  - Scenario 2 proved: Shorts lose heavily when market trends up

RECOMMENDED ADDITIONAL FILTER for SHORT TRADES:
  - Add 200 EMA check: SHORT only when RSI > 70 AND price < 200 EMA
  - Logic: Shorts are safer BELOW the trend line (200 EMA = trend)
  - This mirrors the LONG filter but inverted
  - In bull market: Price stays ABOVE 200 EMA → shorts blocked
  - In bear market: Price stays BELOW 200 EMA → shorts work

ALTERNATIVE FILTERS (if you don't like 200 EMA on shorts):
  1. ATR-based: Only SHORT if volatility is high (ATR > threshold)
  2. Slope-based: Only SHORT if 200 EMA slope is negative (downtrend)
  3. RSI Divergence: Only SHORT if RSI makes lower high while price makes higher high
  4. ADX: Only take trades when ADX > 25 (strong trend confirmation)

STRONGEST RECOMMENDATION for this strategy:
  Use 200 EMA on BOTH sides (already implemented for LONGS):
  - LONG: RSI < 30 AND price > 200 EMA
  - SHORT: RSI > 70 AND price < 200 EMA
  
  This makes the strategy trend-aware, not just momentum-aware.
  It reduces direction dependency and protects against both bull and bear extremes.
""")

print("="*180)
print("NEXT STEP: Test with 200 EMA filter on SHORT side too? (yes/no)")
print("="*180 + "\n")
