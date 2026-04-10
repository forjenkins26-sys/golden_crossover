"""
Backtest P&L Recalculation with Real-World Slippage & Fees
March 1 - April 10, 2026
"""

import pandas as pd
import csv

# ============================================================================
# REAL-WORLD COSTS
# ============================================================================

# Slippage: BTC is highly liquid, typically 0.05-0.10% on market orders
SLIPPAGE_PCT = 0.10

# Binance Fees: 0.10% maker/taker (standard, can be lower with VIP)
MAKER_FEE_PCT = 0.10
TAKER_FEE_PCT = 0.10

# Total cost per trade (entry + exit):
# Entry cost = (entry_price * LOT * slippage%) + (entry_price * LOT * fee%)
# Exit cost = (exit_price * LOT * slippage%) + (exit_price * LOT * fee%)
ENTRY_COST_PCT = SLIPPAGE_PCT + TAKER_FEE_PCT  # Market order = taker
EXIT_COST_PCT = SLIPPAGE_PCT + MAKER_FEE_PCT   # Exit back to cash = maker

LOT_SIZE = 0.10
STARTING_CAPITAL = 500

print("=" * 130)
print("BACKTEST P&L WITH REAL-WORLD SLIPPAGE & FEES")
print("March 1 - April 10, 2026")
print("=" * 130)
print()
print("Cost Structure:")
print(f"  Slippage: {SLIPPAGE_PCT}% (0.05-0.10% typical for BTC)")
print(f"  Entry Fee (Taker): {TAKER_FEE_PCT}% (taking liquidity on entry)")
print(f"  Exit Fee (Maker): {MAKER_FEE_PCT}% (providing liquidity on exit)")
print(f"  Total Entry Cost: {ENTRY_COST_PCT}%")
print(f"  Total Exit Cost: {EXIT_COST_PCT}%")
print()

# Read the backtest CSV
df = pd.read_csv('backtest_flat_final.csv')

trades_detail = []
total_cost_from_trades = 0
total_pnl_before_costs = 0
total_pnl_after_costs = 0

print(f"{'#':<3} {'Dir':<5} {'Entry Price':<15} {'Exit Price':<15} {'P&L (Clean)':<15} {'Entry Cost':<15} {'Exit Cost':<15} {'P&L (Real)':<15}")
print("-" * 130)

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    # Calculate real-world costs
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    entry_cost = entry_notional * (ENTRY_COST_PCT / 100)
    exit_cost = exit_notional * (EXIT_COST_PCT / 100)
    total_cost = entry_cost + exit_cost
    
    # Real P&L = Clean P&L - Costs
    real_pnl = clean_pnl - total_cost
    
    total_cost_from_trades += total_cost
    total_pnl_before_costs += clean_pnl
    total_pnl_after_costs += real_pnl
    
    trades_detail.append({
        'num': idx + 1,
        'direction': direction,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'clean_pnl': clean_pnl,
        'entry_cost': entry_cost,
        'exit_cost': exit_cost,
        'total_cost': total_cost,
        'real_pnl': real_pnl
    })
    
    print(f"{idx+1:<3} {direction:<5} ${entry_price:<14,.0f} ${exit_price:<14,.0f} ${clean_pnl:<14.2f} ${entry_cost:<14.2f} ${exit_cost:<14.2f} ${real_pnl:<14.2f}")

print("-" * 130)

# Summary
print()
print("=" * 130)
print("SUMMARY: CLEAN vs REAL-WORLD P&L")
print("=" * 130)
print()

total_trades = len(df)
winning_before = sum(1 for t in trades_detail if t['clean_pnl'] > 0)
winning_after = sum(1 for t in trades_detail if t['real_pnl'] > 0)
losing_after = total_trades - winning_after

long_trades = sum(1 for t in trades_detail if t['direction'] == 'LONG')
short_trades = sum(1 for t in trades_detail if t['direction'] == 'SHORT')

print(f"Initial Capital:           ${STARTING_CAPITAL:,.2f}")
print()
print(f"BACKTEST RESULTS (Clean Prices - NO Slippage/Fees):")
print(f"  Total P&L:               ${total_pnl_before_costs:+.2f}")
print(f"  Final Equity:            ${STARTING_CAPITAL + total_pnl_before_costs:,.2f}")
print(f"  Return:                  {(total_pnl_before_costs/STARTING_CAPITAL)*100:+.2f}%")
print()
print(f"REAL-WORLD RESULTS (With Slippage & Fees):")
print(f"  Total Slippage+Fees:     ${-total_cost_from_trades:,.2f} ({(total_cost_from_trades/STARTING_CAPITAL)*100:.2f}% of capital)")
print(f"  Total P&L:               ${total_pnl_after_costs:+.2f}")
print(f"  Final Equity:            ${STARTING_CAPITAL + total_pnl_after_costs:,.2f}")
print(f"  Return:                  {(total_pnl_after_costs/STARTING_CAPITAL)*100:+.2f}%")
print()
print(f"IMPACT OF COSTS:")
print(f"  P&L Reduction:           ${total_pnl_before_costs - total_pnl_after_costs:,.2f}")
print(f"  Return Reduction:        {((total_pnl_before_costs/STARTING_CAPITAL)*100) - ((total_pnl_after_costs/STARTING_CAPITAL)*100):.2f} percentage points")
print()
print(f"TRADE QUALITY:")
print(f"  Total Trades:            {total_trades}")
print(f"  LONG Trades:             {long_trades}")
print(f"  SHORT Trades:            {short_trades}")
print(f"  Wins (before costs):     {winning_before}")
print(f"  Wins (after costs):      {winning_after}")
print(f"  Losses (after costs):    {losing_after}")
print(f"  Win Rate:                {(winning_after/total_trades)*100:.1f}%")
print()

# Profitability analysis
print("=" * 130)
print("TRADE-BY-TRADE COST IMPACT")
print("=" * 130)
print()

# Which trades turn from wins to losses?
flipped_trades = []
for t in trades_detail:
    if t['clean_pnl'] > 0 and t['real_pnl'] <= 0:
        flipped_trades.append(t)
    elif t['clean_pnl'] > 0 and t['real_pnl'] > 0:
        pass  # Still winning
    elif t['clean_pnl'] < 0 and t['real_pnl'] < 0:
        pass  # Still losing

if flipped_trades:
    print(f"Trades that FLIP from winners to losers due to costs: {len(flipped_trades)}")
    print()
    for t in flipped_trades:
        print(f"  Trade #{t['num']} ({t['direction']}): Clean P&L ${t['clean_pnl']:+.2f} → Real P&L ${t['real_pnl']:+.2f} (Cost: ${-t['total_cost']:,.2f})")
else:
    print("No trades flip from winners to losers due to costs ✓")

print()
print("=" * 130)
print("SENSITIVITY ANALYSIS: Different Fee Structures")
print("=" * 130)
print()

fee_scenarios = [
    ("Binance Standard (0.1% each)", 0.10, 0.10, 0.10),
    ("Binance with VIP 1 (0.075%)", 0.075, 0.075, 0.10),
    ("Binance with VIP 3 (0.05%)", 0.05, 0.05, 0.10),
    ("Binance with VIP 9 (0.02%)", 0.02, 0.02, 0.10),
    ("Very High Slippage (0.3%)", 0.30, 0.10, 0.10),
]

for scenario_name, slip, maker, taker in fee_scenarios:
    total_cost_scenario = 0
    total_pnl_scenario = 0
    
    for t in trades_detail:
        entry_cost = t['entry_price'] * LOT_SIZE * ((slip + taker) / 100)
        exit_cost = t['exit_price'] * LOT_SIZE * ((slip + maker) / 100)
        pnl_scenario = t['clean_pnl'] - (entry_cost + exit_cost)
        
        total_cost_scenario += entry_cost + exit_cost
        total_pnl_scenario += pnl_scenario
    
    return_scenario = (total_pnl_scenario / STARTING_CAPITAL) * 100
    
    print(f"{scenario_name:<40} P&L: ${total_pnl_scenario:+8.2f} | Return: {return_scenario:+6.2f}% | Costs: ${-total_cost_scenario:8.2f}")

print()
print("=" * 130)
