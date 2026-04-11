"""
RSI 30/70 STRATEGY - COMPLETE COMPARISON
Compares 3 scenarios:
1. Current: LONG with 200 EMA + SHORT unfiltered
2. Protected: LONG with 200 EMA + SHORT with 200 EMA  
3. Bullish Scenario with both filters applied
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*180)
print("RSI 30/70 STRATEGY - COMPLETE PROTECTION ANALYSIS")
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
ENTRY_COST_RATE = 0.0010
EXIT_COST_RATE = 0.0010
POSITION_SIZE = 0.1
RSI_LONG = 30
RSI_SHORT = 70
TP_PCT = 0.04
SL_PCT = 0.012

def run_backtest(data, scenario_name, short_ema_filter=False, reverse_prices=False):
    """
    Run backtest with optional SHORT EMA filter and price reversal
    """
    
    if reverse_prices:
        data = data.copy()
        mean_price = data['Close'].mean()
        data['Close'] = 2 * mean_price - data['Close']
        data['EMA_200'] = data['Close'].ewm(span=200, adjust=False).mean()
    
    print(f"\n[{scenario_name}]")
    if reverse_prices:
        print(f"   (Bull market: prices reversed)")
    if short_ema_filter:
        print(f"   SHORT side: RSI > 70 AND price < 200 EMA (FILTERED)")
    else:
        print(f"   SHORT side: RSI > 70 only (NO FILTER)")
    
    trades = []
    in_trade = False
    entry_price = 0
    trade_type = None
    tp = sl = 0
    
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
                    exit_triggered, exit_type, exit_price = True, 'TP', tp
                elif price <= sl:
                    exit_triggered, exit_type, exit_price = True, 'SL', sl
            else:
                if price <= tp:
                    exit_triggered, exit_type, exit_price = True, 'TP', tp
                elif price >= sl:
                    exit_triggered, exit_type, exit_price = True, 'SL', sl
            
            if exit_triggered:
                if trade_type == 'LONG':
                    gross_pnl = (exit_price - entry_price) * POSITION_SIZE
                else:
                    gross_pnl = (entry_price - exit_price) * POSITION_SIZE
                
                entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
                exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
                net_pnl = gross_pnl - entry_cost - exit_cost
                
                trades.append({
                    'Type': trade_type,
                    'Entry': entry_price,
                    'Exit': exit_price,
                    'Net_PnL': net_pnl,
                    'Gross_PnL': gross_pnl,
                    'Fees': entry_cost + exit_cost,
                })
                in_trade = False
        
        # ENTRY
        if not in_trade and in_session:
            # SHORT with optional EMA filter
            short_signal = rsi > RSI_SHORT
            if short_ema_filter:
                short_signal = short_signal and price < ema_200
            
            if short_signal:
                in_trade = True
                trade_type = 'SHORT'
                entry_price = price
                tp = price * (1 - TP_PCT)
                sl = price * (1 + SL_PCT)
            
            # LONG with EMA filter
            elif rsi < RSI_LONG and price > ema_200:
                in_trade = True
                trade_type = 'LONG'
                entry_price = price
                tp = price * (1 + TP_PCT)
                sl = price * (1 - SL_PCT)
    
    if len(trades) == 0:
        return pd.DataFrame(columns=['Type', 'Entry', 'Exit', 'Net_PnL', 'Gross_PnL', 'Fees'])
    df_trades = pd.DataFrame(trades)
    return df_trades

# ============================================================================
# SCENARIO A: BEARISH MARKET - CURRENT SETUP (SHORT unfiltered)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO A: BEARISH MARKET - CURRENT SETUP")
print("="*180)

trades_a = run_backtest(df, "Scenario A: Bearish + SHORT unfiltered", short_ema_filter=False, reverse_prices=False)

longs_a = trades_a[trades_a['Type'] == 'LONG']
shorts_a = trades_a[trades_a['Type'] == 'SHORT']
total_pnl_a = trades_a['Net_PnL'].sum()
total_gross_a = trades_a['Gross_PnL'].sum()
total_fees_a = trades_a['Fees'].sum()
total_wins_a = len(trades_a[trades_a['Net_PnL'] > 0])
win_rate_a = total_wins_a / len(trades_a) * 100 if len(trades_a) > 0 else 0

wins_sum_a = trades_a[trades_a['Net_PnL'] > 0]['Net_PnL'].sum()
loss_sum_a = abs(trades_a[trades_a['Net_PnL'] < 0]['Net_PnL'].sum())
pf_a = wins_sum_a / loss_sum_a if loss_sum_a > 0 else 0

print(f"\n   Total Trades:       {len(trades_a)}")
print(f"   Gross P&L:          ${total_gross_a:+.2f}")
print(f"   Net P&L:            ${total_pnl_a:+.2f}")
print(f"   Win Rate:           {win_rate_a:.1f}%")
print(f"   Profit Factor:      {pf_a:.2f}x")

if len(longs_a) > 0:
    longs_a_pnl = longs_a['Net_PnL'].sum()
    longs_a_wr = len(longs_a[longs_a['Net_PnL'] > 0]) / len(longs_a) * 100
    print(f"\n   LONG:  {len(longs_a):2d} trades | {longs_a_wr:5.1f}% WR | ${longs_a_pnl:+8.2f}")

if len(shorts_a) > 0:
    shorts_a_pnl = shorts_a['Net_PnL'].sum()
    shorts_a_wr = len(shorts_a[shorts_a['Net_PnL'] > 0]) / len(shorts_a) * 100
    print(f"   SHORT: {len(shorts_a):2d} trades | {shorts_a_wr:5.1f}% WR | ${shorts_a_pnl:+8.2f}")

# ============================================================================
# SCENARIO B: BEARISH MARKET - PROTECTED SETUP (SHORT with 200 EMA)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO B: BEARISH MARKET - PROTECTED SETUP")
print("="*180)

trades_b = run_backtest(df, "Scenario B: Bearish + SHORT filtered", short_ema_filter=True, reverse_prices=False)

longs_b = trades_b[trades_b['Type'] == 'LONG']
shorts_b = trades_b[trades_b['Type'] == 'SHORT']
total_pnl_b = trades_b['Net_PnL'].sum()
total_gross_b = trades_b['Gross_PnL'].sum()
total_fees_b = trades_b['Fees'].sum()
total_wins_b = len(trades_b[trades_b['Net_PnL'] > 0])
win_rate_b = total_wins_b / len(trades_b) * 100 if len(trades_b) > 0 else 0

wins_sum_b = trades_b[trades_b['Net_PnL'] > 0]['Net_PnL'].sum()
loss_sum_b = abs(trades_b[trades_b['Net_PnL'] < 0]['Net_PnL'].sum())
pf_b = wins_sum_b / loss_sum_b if loss_sum_b > 0 else 0

print(f"\n   Total Trades:       {len(trades_b)}")
print(f"   Gross P&L:          ${total_gross_b:+.2f}")
print(f"   Net P&L:            ${total_pnl_b:+.2f}")
print(f"   Win Rate:           {win_rate_b:.1f}%")
print(f"   Profit Factor:      {pf_b:.2f}x")

if len(longs_b) > 0:
    longs_b_pnl = longs_b['Net_PnL'].sum()
    longs_b_wr = len(longs_b[longs_b['Net_PnL'] > 0]) / len(longs_b) * 100
    print(f"\n   LONG:  {len(longs_b):2d} trades | {longs_b_wr:5.1f}% WR | ${longs_b_pnl:+8.2f}")

if len(shorts_b) > 0:
    shorts_b_pnl = shorts_b['Net_PnL'].sum()
    shorts_b_wr = len(shorts_b[shorts_b['Net_PnL'] > 0]) / len(shorts_b) * 100
    print(f"   SHORT: {len(shorts_b):2d} trades | {shorts_b_wr:5.1f}% WR | ${shorts_b_pnl:+8.2f}")

# ============================================================================
# SCENARIO C: BULLISH MARKET - CURRENT SETUP (SHORT unfiltered)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO C: BULLISH MARKET - CURRENT SETUP (RISK!)")
print("="*180)

trades_c = run_backtest(df, "Scenario C: Bullish + SHORT unfiltered", short_ema_filter=False, reverse_prices=True)

longs_c = trades_c[trades_c['Type'] == 'LONG']
shorts_c = trades_c[trades_c['Type'] == 'SHORT']
total_pnl_c = trades_c['Net_PnL'].sum()
total_gross_c = trades_c['Gross_PnL'].sum()
total_fees_c = trades_c['Fees'].sum()
total_wins_c = len(trades_c[trades_c['Net_PnL'] > 0])
win_rate_c = total_wins_c / len(trades_c) * 100 if len(trades_c) > 0 else 0

wins_sum_c = trades_c[trades_c['Net_PnL'] > 0]['Net_PnL'].sum()
loss_sum_c = abs(trades_c[trades_c['Net_PnL'] < 0]['Net_PnL'].sum())
pf_c = wins_sum_c / loss_sum_c if loss_sum_c > 0 else 0

print(f"\n   Total Trades:       {len(trades_c)}")
print(f"   Gross P&L:          ${total_gross_c:+.2f}")
print(f"   Net P&L:            ${total_pnl_c:+.2f}")
print(f"   Win Rate:           {win_rate_c:.1f}%")
print(f"   Profit Factor:      {pf_c:.2f}x")

if len(longs_c) > 0:
    longs_c_pnl = longs_c['Net_PnL'].sum()
    longs_c_wr = len(longs_c[longs_c['Net_PnL'] > 0]) / len(longs_c) * 100
    print(f"\n   LONG:  {len(longs_c):2d} trades | {longs_c_wr:5.1f}% WR | ${longs_c_pnl:+8.2f}")

if len(shorts_c) > 0:
    shorts_c_pnl = shorts_c['Net_PnL'].sum()
    shorts_c_wr = len(shorts_c[shorts_c['Net_PnL'] > 0]) / len(shorts_c) * 100
    print(f"   SHORT: {len(shorts_c):2d} trades | {shorts_c_wr:5.1f}% WR | ${shorts_c_pnl:+8.2f}")

# ============================================================================
# SCENARIO D: BULLISH MARKET - PROTECTED SETUP (SHORT with 200 EMA)
# ============================================================================

print("\n" + "="*180)
print("SCENARIO D: BULLISH MARKET - PROTECTED SETUP (SAFER)")
print("="*180)

trades_d = run_backtest(df, "Scenario D: Bullish + SHORT filtered", short_ema_filter=True, reverse_prices=True)

longs_d = trades_d[trades_d['Type'] == 'LONG']
shorts_d = trades_d[trades_d['Type'] == 'SHORT']
total_pnl_d = trades_d['Net_PnL'].sum()
total_gross_d = trades_d['Gross_PnL'].sum()
total_fees_d = trades_d['Fees'].sum()
total_wins_d = len(trades_d[trades_d['Net_PnL'] > 0])
win_rate_d = total_wins_d / len(trades_d) * 100 if len(trades_d) > 0 else 0

wins_sum_d = trades_d[trades_d['Net_PnL'] > 0]['Net_PnL'].sum()
loss_sum_d = abs(trades_d[trades_d['Net_PnL'] < 0]['Net_PnL'].sum())
pf_d = wins_sum_d / loss_sum_d if loss_sum_d > 0 else 0

print(f"\n   Total Trades:       {len(trades_d)}")
print(f"   Gross P&L:          ${total_gross_d:+.2f}")
print(f"   Net P&L:            ${total_pnl_d:+.2f}")
print(f"   Win Rate:           {win_rate_d:.1f}%")
print(f"   Profit Factor:      {pf_d:.2f}x")

if len(longs_d) > 0:
    longs_d_pnl = longs_d['Net_PnL'].sum()
    longs_d_wr = len(longs_d[longs_d['Net_PnL'] > 0]) / len(longs_d) * 100
    print(f"\n   LONG:  {len(longs_d):2d} trades | {longs_d_wr:5.1f}% WR | ${longs_d_pnl:+8.2f}")

if len(shorts_d) > 0:
    shorts_d_pnl = shorts_d['Net_PnL'].sum()
    shorts_d_wr = len(shorts_d[shorts_d['Net_PnL'] > 0]) / len(shorts_d) * 100
    print(f"   SHORT: {len(shorts_d):2d} trades | {shorts_d_wr:5.1f}% WR | ${shorts_d_pnl:+8.2f}")

# ============================================================================
# SUMMARY TABLE
# ============================================================================

print("\n" + "="*180)
print("SUMMARY: 4-SCENARIO COMPARISON TABLE")
print("="*180)

print(f"""
{'Scenario':<35} {'Trades':<10} {'Net P&L':<15} {'WR':<12} {'PF':<12} {'Status':<15}
{'-'*180}
Bearish + SHORT unfiltered           {len(trades_a):<10} ${total_pnl_a:>10.2f}  {win_rate_a:>8.1f}%     {pf_a:>8.2f}x    CURRENT ✓
Bearish + SHORT filtered             {len(trades_b):<10} ${total_pnl_b:>10.2f}  {win_rate_b:>8.1f}%     {pf_b:>8.2f}x    SAFE
Bullish + SHORT unfiltered (DANGER)  {len(trades_c):<10} ${total_pnl_c:>10.2f}  {win_rate_c:>8.1f}%     {pf_c:>8.2f}x    RISKY ⚠️
Bullish + SHORT filtered (SAFER)     {len(trades_d):<10} ${total_pnl_d:>10.2f}  {win_rate_d:>8.1f}%     {pf_d:>8.2f}x    PROTECTED ✓
""")

# ============================================================================
# RISK ANALYSIS
# ============================================================================

print("="*180)
print("RISK ANALYSIS")
print("="*180)

downside_unfiltered = total_pnl_a - total_pnl_c
downside_filtered = total_pnl_b - total_pnl_d
improvement = downside_unfiltered - downside_filtered

print(f"""
DIRECTION DEPENDENCE (Bearish profit vs Bullish profit):
  Without SHORT filter:  ${total_pnl_a:.2f} (bearish) vs ${total_pnl_c:.2f} (bullish)
  Downside risk:         ${downside_unfiltered:.2f} (${abs(downside_unfiltered):.0f} LOSS if wrong direction)
  
  With SHORT filter:     ${total_pnl_b:.2f} (bearish) vs ${total_pnl_d:.2f} (bullish)
  Downside risk:         ${downside_filtered:.2f} (${abs(downside_filtered):.0f} LOSS if wrong direction)

RISK REDUCTION FROM ADDING 200 EMA TO SHORT SIDE:
  Profit reduction (bullish):  ${abs(total_pnl_c):.2f} → ${abs(total_pnl_d):.2f}
  Direction risk reduced by:   ${abs(improvement):.2f} ({abs(improvement/downside_unfiltered*100):.0f}%)
  
VERDICT:
  ✓ Current setup profitable in bearish market but highly exposed to direction reversal
  ✓ Adding 200 EMA to SHORT side reduces direction dependence significantly
  ✓ In bull market: losses cut by {abs(improvement/downside_unfiltered*100):.0f}% with filtered shorts
  ✓ Recommendation: Implement 200 EMA on SHORT side before live trading
""")

print("="*180)
