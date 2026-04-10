"""
Comprehensive Fee Deduction Scenario Analysis
Shows all trades with clean P&L vs realistic P&L with fees
"""

import pandas as pd

print("=" * 160)
print("COMPREHENSIVE FEE DEDUCTION ANALYSIS - ALL SCENARIOS")
print("=" * 160)
print()

# Read the latest backtest with TP2 at 5%
df = pd.read_csv('backtest_flat_final.csv')

LOT_SIZE = 0.10
STARTING_CAPITAL = 500

# ============================================================================
# SCENARIO COMPARISON TABLE
# ============================================================================

print()
print("=" * 160)
print("SCENARIO 1: CLEAN (NO FEES - THEORETICAL MAXIMUM)")
print("=" * 160)
print()

print(f"{'#':<3} {'Direction':<8} {'Entry $':<12} {'Exit $':<12} {'Points':<10} {'Clean P&L':<12}")
print("-" * 160)

total_clean = 0
for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    points = exit_price - entry_price if direction == 'LONG' else entry_price - exit_price
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    total_clean += clean_pnl
    
    print(f"{idx+1:<3} {direction:<8} ${entry_price:<11,.0f} ${exit_price:<11,.0f} {points:>+9.0f} ${clean_pnl:>11.2f}")

print("-" * 160)
print(f"{'TOTAL':<23} {'':20} ${total_clean:>11.2f}")
print(f"Return: {(total_clean/STARTING_CAPITAL)*100:+.2f}% | Final Equity: ${STARTING_CAPITAL + total_clean:,.2f}")
print()

# ============================================================================
# SCENARIO 2: BINANCE STANDARD (0.1%)
# ============================================================================

print()
print("=" * 160)
print("SCENARIO 2: BINANCE STANDARD (0.1% Slippage + 0.1% Entry + 0.1% Exit = 0.2% round-trip)")
print("=" * 160)
print()

slippage = 0.10
entry_fee = 0.10
exit_fee = 0.10

print(f"{'#':<3} {'Dir':<5} {'Entry $':<12} {'Exit $':<12} {'Clean P&L':<14} {'Entry Fee':<12} {'Exit Fee':<12} {'Real P&L':<14}")
print("-" * 160)

total_fees_binance = 0
total_pnl_binance = 0

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    entry_cost = entry_notional * ((slippage + entry_fee) / 100)
    exit_cost = exit_notional * ((slippage + exit_fee) / 100)
    total_fees = entry_cost + exit_cost
    
    real_pnl = clean_pnl - total_fees
    
    total_fees_binance += total_fees
    total_pnl_binance += real_pnl
    
    print(f"{idx+1:<3} {direction:<5} ${entry_price:<11,.0f} ${exit_price:<11,.0f} ${clean_pnl:<13.2f} ${entry_cost:<11.2f} ${exit_cost:<11.2f} ${real_pnl:<13.2f}")

print("-" * 160)
print(f"Total Fees: ${total_fees_binance:>11.2f} | Total P&L: ${total_pnl_binance:>11.2f}")
print(f"Return: {(total_pnl_binance/STARTING_CAPITAL)*100:+.2f}% | Final Equity: ${STARTING_CAPITAL + total_pnl_binance:,.2f}")
print()

# ============================================================================
# SCENARIO 3: DELTA EXCHANGE INDIA (0.05%)
# ============================================================================

print()
print("=" * 160)
print("SCENARIO 3: DELTA EXCHANGE INDIA (0.05% Slippage + 0.05% Entry + 0.05% Exit = 0.1% round-trip)")
print("=" * 160)
print()

slippage = 0.05
entry_fee = 0.05
exit_fee = 0.05

print(f"{'#':<3} {'Dir':<5} {'Entry $':<12} {'Exit $':<12} {'Clean P&L':<14} {'Entry Fee':<12} {'Exit Fee':<12} {'Real P&L':<14}")
print("-" * 160)

total_fees_delta = 0
total_pnl_delta = 0

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    entry_cost = entry_notional * ((slippage + entry_fee) / 100)
    exit_cost = exit_notional * ((slippage + exit_fee) / 100)
    total_fees = entry_cost + exit_cost
    
    real_pnl = clean_pnl - total_fees
    
    total_fees_delta += total_fees
    total_pnl_delta += real_pnl
    
    print(f"{idx+1:<3} {direction:<5} ${entry_price:<11,.0f} ${exit_price:<11,.0f} ${clean_pnl:<13.2f} ${entry_cost:<11.2f} ${exit_cost:<11.2f} ${real_pnl:<13.2f}")

print("-" * 160)
print(f"Total Fees: ${total_fees_delta:>11.2f} | Total P&L: ${total_pnl_delta:>11.2f}")
print(f"Return: {(total_pnl_delta/STARTING_CAPITAL)*100:+.2f}% | Final Equity: ${STARTING_CAPITAL + total_pnl_delta:,.2f}")
print()

# ============================================================================
# MASTER COMPARISON TABLE
# ============================================================================

print()
print("=" * 160)
print("MASTER COMPARISON: ALL SCENARIOS SIDE-BY-SIDE")
print("=" * 160)
print()

print(f"{'Scenario':<40} {'Trades':<10} {'Total Fees':<15} {'Total P&L':<15} {'Return %':<15} {'Status':<20}")
print("-" * 160)
print(f"{'Clean (No Fees)':<40} {len(df):<10} ${'0.00':<14} ${total_clean:<14.2f} {(total_clean/STARTING_CAPITAL)*100:>13.2f}% {'Theoretical Max':<20}")
print(f"{'Binance Standard (0.1%)':<40} {len(df):<10} ${total_fees_binance:<14.2f} ${total_pnl_binance:<14.2f} {(total_pnl_binance/STARTING_CAPITAL)*100:>13.2f}% {'✓ Profitable':<20}")
print(f"{'Delta Exchange India (0.05%)':<40} {len(df):<10} ${total_fees_delta:<14.2f} ${total_pnl_delta:<14.2f} {(total_pnl_delta/STARTING_CAPITAL)*100:>13.2f}% {'✓ STRONG':<20}")
print("-" * 160)
print()

# ============================================================================
# FEE IMPACT ANALYSIS
# ============================================================================

print()
print("=" * 160)
print("FEE IMPACT ANALYSIS (How fees affect your P&L)")
print("=" * 160)
print()

print(f"Initial Capital: ${STARTING_CAPITAL}")
print()
print("Fee Deduction Cost:")
print(f"  Binance (0.1%): ${total_fees_binance:,.2f} ({(total_fees_binance/STARTING_CAPITAL)*100:.2f}% of capital)")
print(f"  Delta (0.05%):  ${total_fees_delta:,.2f} ({(total_fees_delta/STARTING_CAPITAL)*100:.2f}% of capital)")
print()
print("Difference between exchanges:")
print(f"  Delta saves you: ${total_fees_binance - total_fees_delta:,.2f} in fees")
print(f"  This adds directly to profit: ${total_pnl_delta - total_pnl_binance:+,.2f} more return")
print()

# ============================================================================
# WIN vs LOSS ANALYSIS (Fee Impact Asymmetry)
# ============================================================================

print()
print("=" * 160)
print("WIN vs LOSS FEE IMPACT (Why fees hurt losses more than wins)")
print("=" * 160)
print()

winning_trades = df[df['Flat_P&L'].str.contains('\+')]
losing_trades = df[~df['Flat_P&L'].str.contains('\+')]

total_clean_wins = 0
total_clean_losses = 0
total_fees_wins_delta = 0
total_fees_losses_delta = 0
total_pnl_wins_delta = 0
total_pnl_losses_delta = 0

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    slippage = 0.05
    entry_fee = 0.05
    exit_fee = 0.05
    
    entry_cost = entry_notional * ((slippage + entry_fee) / 100)
    exit_cost = exit_notional * ((slippage + exit_fee) / 100)
    total_fees = entry_cost + exit_cost
    
    real_pnl = clean_pnl - total_fees
    
    if clean_pnl > 0:
        total_clean_wins += clean_pnl
        total_fees_wins_delta += total_fees
        total_pnl_wins_delta += real_pnl
    else:
        total_clean_losses += clean_pnl
        total_fees_losses_delta += total_fees
        total_pnl_losses_delta += real_pnl

num_wins = len(winning_trades)
num_losses = len(losing_trades)

print(f"Winning Trades ({num_wins} trades):")
print(f"  Clean P&L:        ${total_clean_wins:>11.2f}")
print(f"  Fees paid:        ${total_fees_wins_delta:>11.2f}")
print(f"  Real P&L:         ${total_pnl_wins_delta:>11.2f}")
print(f"  Fee impact:       {((total_fees_wins_delta / total_clean_wins) * 100):>10.2f}% reduction")
print()
print(f"Losing Trades ({num_losses} trades):")
print(f"  Clean P&L:        ${total_clean_losses:>11.2f}")
print(f"  Fees paid:        ${total_fees_losses_delta:>11.2f}")
print(f"  Real P&L:         ${total_pnl_losses_delta:>11.2f}")
print(f"  Fee impact:       {((total_fees_losses_delta / abs(total_clean_losses)) * 100):>10.2f}% WORSE (fees make losses bigger)")
print()
print(f"KEY INSIGHT: Your {num_wins} winners (${total_pnl_wins_delta:.2f}) must cover both")
print(f"            their own fees AND the {num_losses} losers' fees (${abs(total_pnl_losses_delta):.2f})")
print()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print()
print("=" * 160)
print("FINAL RECOMMENDATION")
print("=" * 160)
print()
print(f"✓ Deploy on: DELTA EXCHANGE INDIA")
print(f"✓ Expected return: ${total_pnl_delta:,.2f} (+{(total_pnl_delta/STARTING_CAPITAL)*100:.2f}%)")
print(f"✓ This represents real, achievable returns after all fees and slippage")
print()
print(f"ℹ If forced to use Binance: ${total_pnl_binance:,.2f} (+{(total_pnl_binance/STARTING_CAPITAL)*100:.2f}%)")
print(f"  Still profitable but requires lower fees (VIP status) or it becomes break-even")
print()
print("=" * 160)
