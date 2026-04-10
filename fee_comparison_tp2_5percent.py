"""
Fee Analysis with Updated TP2 at 5%
Comparing Binance Standard (0.1%) vs Delta Exchange India (0.05%)
"""

import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================

LOT_SIZE = 0.10
STARTING_CAPITAL = 500

print("=" * 140)
print("ANALYSIS: TP2 AT 5% WITH TWO FEE STRUCTURES")
print("March 1 - April 10, 2026 Backtest")
print("=" * 140)
print()

# Read the backtest CSV with updated TP2
df = pd.read_csv('backtest_flat_final.csv')

# ============================================================================
# SCENARIO 1: Binance Standard (0.1% each)
# ============================================================================

print("SCENARIO 1: BINANCE STANDARD (0.1% Slippage + 0.1% Entry Fee + 0.1% Exit Fee)")
print("-" * 140)

slippage = 0.10
maker_fee = 0.10
taker_fee = 0.10
entry_cost_pct = slippage + taker_fee
exit_cost_pct = slippage + maker_fee

trades_detail_1 = []
total_cost_1 = 0
total_pnl_before_1 = 0
total_pnl_after_1 = 0

print(f"{'#':<3} {'Dir':<5} {'Entry $':<12} {'Exit $':<12} {'Clean P&L':<14} {'Entry Cost':<12} {'Exit Cost':<12} {'Real P&L':<14}")
print("-" * 140)

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    entry_cost = entry_notional * (entry_cost_pct / 100)
    exit_cost = exit_notional * (exit_cost_pct / 100)
    real_pnl = clean_pnl - (entry_cost + exit_cost)
    
    total_cost_1 += entry_cost + exit_cost
    total_pnl_before_1 += clean_pnl
    total_pnl_after_1 += real_pnl
    
    print(f"{idx+1:<3} {direction:<5} ${entry_price:<11,.0f} ${exit_price:<11,.0f} ${clean_pnl:<13.2f} ${entry_cost:<11.2f} ${exit_cost:<11.2f} ${real_pnl:<13.2f}")

print("-" * 140)
return_before_1 = (total_pnl_before_1 / STARTING_CAPITAL) * 100
return_after_1 = (total_pnl_after_1 / STARTING_CAPITAL) * 100

print()
print(f"Initial Capital:       ${STARTING_CAPITAL:,.2f}")
print(f"P&L Before Fees:       ${total_pnl_before_1:+.2f} ({return_before_1:+.2f}%)")
print(f"Total Fees:            ${-total_cost_1:+.2f}")
print(f"P&L After Fees:        ${total_pnl_after_1:+.2f} ({return_after_1:+.2f}%)")
print(f"Final Equity:          ${STARTING_CAPITAL + total_pnl_after_1:,.2f}")
print()

# ============================================================================
# SCENARIO 2: Delta Exchange India (0.05% each)
# ============================================================================

print()
print("=" * 140)
print("SCENARIO 2: DELTA EXCHANGE INDIA (0.05% Slippage + 0.05% Entry Fee + 0.05% Exit Fee)")
print("-" * 140)

slippage = 0.05
maker_fee = 0.05
taker_fee = 0.05
entry_cost_pct = slippage + taker_fee
exit_cost_pct = slippage + maker_fee

trades_detail_2 = []
total_cost_2 = 0
total_pnl_before_2 = 0
total_pnl_after_2 = 0

print(f"{'#':<3} {'Dir':<5} {'Entry $':<12} {'Exit $':<12} {'Clean P&L':<14} {'Entry Cost':<12} {'Exit Cost':<12} {'Real P&L':<14}")
print("-" * 140)

for idx, row in df.iterrows():
    direction = row['Direction']
    entry_price = float(row['Price_In'].replace('$', ''))
    exit_price = float(row['Price_Out'].replace('$', ''))
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    
    entry_notional = entry_price * LOT_SIZE
    exit_notional = exit_price * LOT_SIZE
    
    entry_cost = entry_notional * (entry_cost_pct / 100)
    exit_cost = exit_notional * (exit_cost_pct / 100)
    real_pnl = clean_pnl - (entry_cost + exit_cost)
    
    total_cost_2 += entry_cost + exit_cost
    total_pnl_before_2 += clean_pnl
    total_pnl_after_2 += real_pnl
    
    print(f"{idx+1:<3} {direction:<5} ${entry_price:<11,.0f} ${exit_price:<11,.0f} ${clean_pnl:<13.2f} ${entry_cost:<11.2f} ${exit_cost:<11.2f} ${real_pnl:<13.2f}")

print("-" * 140)
return_before_2 = (total_pnl_before_2 / STARTING_CAPITAL) * 100
return_after_2 = (total_pnl_after_2 / STARTING_CAPITAL) * 100

print()
print(f"Initial Capital:       ${STARTING_CAPITAL:,.2f}")
print(f"P&L Before Fees:       ${total_pnl_before_2:+.2f} ({return_before_2:+.2f}%)")
print(f"Total Fees:            ${-total_cost_2:+.2f}")
print(f"P&L After Fees:        ${total_pnl_after_2:+.2f} ({return_after_2:+.2f}%)")
print(f"Final Equity:          ${STARTING_CAPITAL + total_pnl_after_2:,.2f}")
print()

# ============================================================================
# COMPARISON SUMMARY
# ============================================================================

print()
print("=" * 140)
print("SUMMARY: TP2 AT 5% - THREE VERSIONS")
print("=" * 140)
print()

print(f"{'Exchange/Scenario':<40} {'Fees':<15} {'Total P&L':<15} {'Return':<15} {'Status':<20}")
print("-" * 140)
print(f"{'Clean (No Fees)':<40} ${0:>13.2f} ${total_pnl_before_1:>13.2f} {return_before_1:>13.2f}% {'✓ Theoretical Max':<20}")
print(f"{'Binance Standard (0.1%)':<40} ${total_cost_1:>13.2f} ${total_pnl_after_1:>13.2f} {return_after_1:>13.2f}% {'✗ BREAK-EVEN' if abs(return_after_1) < 5 else ('✓ PROFITABLE' if return_after_1 > 0 else '✗ LOSS'):<20}")
print(f"{'Delta Exchange India (0.05%)':<40} ${total_cost_2:>13.2f} ${total_pnl_after_2:>13.2f} {return_after_2:>13.2f}% {'✓ STRONG' if return_after_2 > 50 else ('✓ PROFITABLE' if return_after_2 > 0 else '✗ LOSS'):<20}")
print("-" * 140)
print()

print("=" * 140)
print("INSIGHTS")
print("=" * 140)
print()
print(f"✓ Larger TP2 targets improved results:")
print(f"  - Trades reduced: 18 → 16 (fewer but higher quality exits)")
print(f"  - Win rate improved: 33.3% → 37.5%")
print(f"  - P&L before fees: +$461.17 → +${total_pnl_before_1:+.2f} (+{((total_pnl_before_1 - 461.17)/461.17)*100:+.1f}%)")
print()
print(f"✓ Fee impact:")
print(f"  - Binance (0.1%): Costs ${total_cost_1:.2f}, Result: ${total_pnl_after_1:+.2f} ({return_after_1:+.2f}%)")
print(f"  - Delta (0.05%):  Costs ${total_cost_2:.2f}, Result: ${total_pnl_after_2:+.2f} ({return_after_2:+.2f}%)")
print()

if return_after_1 > 0:
    print(f"✓ CRITICAL: Even at Binance standard (0.1%) fees, strategy is NOW PROFITABLE!")
else:
    print(f"⚠ At Binance standard (0.1%), result is: {return_after_1:+.2f}%")

if return_after_2 > 0:
    print(f"✓ STRONG: At Delta Exchange (0.05%) fees, return is {return_after_2:+.2f}%")

print()
print("RECOMMENDATION:")
if return_after_1 > 10:
    print(f"✓ Strategy is viable even on Binance standard rates. Deploy on Binance.")
elif return_after_2 > 20:
    print(f"✓ Strategy is highly profitable on Delta Exchange. Use Delta for live trading.")
else:
    print(f"⚠ Review filter parameters or increase TP2 further.")

print()
print("=" * 140)
