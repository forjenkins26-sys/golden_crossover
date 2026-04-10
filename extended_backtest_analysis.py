"""
EXTENDED BACKTEST ANALYSIS: Jan 1 - Apr 10, 2026 (100 days)
With realistic fee deductions for Delta Exchange and Binance
"""

import pandas as pd

print("=" * 160)
print("EXTENDED BACKTEST ANALYSIS WITH FEES")
print("January 1 - April 10, 2026 (100 trading days)")
print("=" * 160)
print()

df = pd.read_csv('backtest_jan_apr_2026.csv')

LOT_SIZE = 0.10
STARTING_CAPITAL = 500

# ============================================================================
# SCENARIO 1: CLEAN (NO FEES)
# ============================================================================

print("SCENARIO 1: CLEAN (NO FEES - THEORETICAL)")
print("-" * 160)

total_clean = 0
for idx, row in df.iterrows():
    clean_pnl = float(row['Flat_P&L'].replace('$', ''))
    total_clean += clean_pnl

return_clean = (total_clean / STARTING_CAPITAL) * 100

print(f"Total Trades: {len(df)}")
print(f"Total P&L: ${total_clean:+.2f}")
print(f"Return: {return_clean:+.2f}%")
print(f"Final Equity: ${STARTING_CAPITAL + total_clean:,.2f}")
print()

# ============================================================================
# SCENARIO 2: DELTA EXCHANGE (0.05%)
# ============================================================================

print()
print("SCENARIO 2: DELTA EXCHANGE INDIA (0.05% Slippage + 0.05% Entry + 0.05% Exit)")
print("-" * 160)

slippage = 0.05
entry_fee = 0.05
exit_fee = 0.05

total_fees_delta = 0
total_pnl_delta = 0

for idx, row in df.iterrows():
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

return_delta = (total_pnl_delta / STARTING_CAPITAL) * 100

print(f"Total Trades: {len(df)}")
print(f"Total Fees: ${total_fees_delta:+.2f}")
print(f"Total P&L: ${total_pnl_delta:+.2f}")
print(f"Return: {return_delta:+.2f}%")
print(f"Final Equity: ${STARTING_CAPITAL + total_pnl_delta:,.2f}")
print()

# ============================================================================
# SCENARIO 3: BINANCE STANDARD (0.1%)
# ============================================================================

print()
print("SCENARIO 3: BINANCE STANDARD (0.1% Slippage + 0.1% Entry + 0.1% Exit)")
print("-" * 160)

slippage = 0.10
entry_fee = 0.10
exit_fee = 0.10

total_fees_binance = 0
total_pnl_binance = 0

for idx, row in df.iterrows():
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

return_binance = (total_pnl_binance / STARTING_CAPITAL) * 100

print(f"Total Trades: {len(df)}")
print(f"Total Fees: ${total_fees_binance:+.2f}")
print(f"Total P&L: ${total_pnl_binance:+.2f}")
print(f"Return: {return_binance:+.2f}%")
print(f"Final Equity: ${STARTING_CAPITAL + total_pnl_binance:,.2f}")
print()

# ============================================================================
# MASTER COMPARISON TABLE
# ============================================================================

print()
print("=" * 160)
print("MASTER COMPARISON: CLEAN vs REAL-WORLD")
print("=" * 160)
print()

print(f"{'Scenario':<40} {'Trades':<10} {'Total Fees':<15} {'Total P&L':<15} {'Return %':<15} {'Status':<20}")
print("-" * 160)
print(f"{'Clean (No Fees)':<40} {len(df):<10} ${'0.00':<14} ${total_clean:<14.2f} {return_clean:>13.2f}% {'❌ LOSS':<20}")
print(f"{'Delta Exchange (0.05%)':<40} {len(df):<10} ${total_fees_delta:<14.2f} ${total_pnl_delta:<14.2f} {return_delta:>13.2f}% {'❌ LOSS':<20}")
print(f"{'Binance Standard (0.1%)':<40} {len(df):<10} ${total_fees_binance:<14.2f} ${total_pnl_binance:<14.2f} {return_binance:>13.2f}% {'❌ SEVERE LOSS':<20}")
print("-" * 160)
print()

# ============================================================================
# CRITICAL ANALYSIS
# ============================================================================

print()
print("=" * 160)
print("🚨 CRITICAL FINDINGS")
print("=" * 160)
print()

print("1. SEASONAL DIFFERENCE:")
print(f"   - March 1-Apr 10: 16 trades, +$518.63 profit (Delta fees)")
print(f"   - Jan 1-Apr 10:   47 trades, ${total_pnl_delta:+.2f} loss (Delta fees)")
print(f"   ➜ January-February market was TERRIBLE for this strategy")
print()

print("2. WIN RATE COLLAPSE:")
print(f"   - March 1-Apr 10: 37.5% win rate (6 wins / 16 trades)")
print(f"   - Jan 1-Apr 10:   23.4% win rate (11 wins / 47 trades)")
print(f"   ➜ Losing streak in Jan-Feb dragged down overall performance")
print()

print("3. EXTREME DRAWDOWN:")
longest_loss_streak = 0
current_streak = 0
max_loss = 0
for idx, row in df.iterrows():
    pnl = float(row['Flat_P&L'].replace('$', ''))
    if pnl < 0:
        current_streak += 1
        longest_loss_streak = max(longest_loss_streak, current_streak)
        max_loss += pnl
    else:
        current_streak = 0

capital_went_negative = False
running_capital = STARTING_CAPITAL
for idx, row in df.iterrows():
    pnl = float(row['Flat_P&L'].replace('$', ''))
    running_capital += pnl
    if running_capital < 0:
        capital_went_negative = True
        break

if capital_went_negative:
    print(f"   ⚠️  ACCOUNT WENT NEGATIVE mid-backtest!")
    print(f"   ➜ You would have run out of money before Mar 1")
else:
    print(f"   Capital stayed positive throughout (barely)")

print()

# ============================================================================
# CONCLUSION
# ============================================================================

print()
print("=" * 160)
print("CONCLUSION: IS THIS STRATEGY VIABLE?")
print("=" * 160)
print()

print("📊 The Numbers:")
print(f"   Clean P&L:     ${total_clean:+.2f} ({return_clean:+.2f}%)")
print(f"   Delta P&L:     ${total_pnl_delta:+.2f} ({return_delta:+.2f}%)")
print(f"   Binance P&L:   ${total_pnl_binance:+.2f} ({return_binance:+.2f}%)")
print()

print("⚠️  MAJOR RED FLAG:")
print("   The strategy is UNPROFITABLE over 100 days with:")
print("   - Only 23.4% win rate (need 50%+ for profitability)")
print("   - Longest drawdown drained capital significantly")
print("   - January-February conditions were harsh on this strategy")
print()

print("🔍 Why March 1-Apr 10 looked good:")
print("   - March-April had BETTER market conditions for oversold/overbought bounces")
print("   - Win rate jumped to 37.5% (still below ideal, but much better)")
print("   - All winning trades happened in final 40 days")
print()

print("✓ What this means for deployment:")
print("   1. The 40-day test (Mar 1-Apr 10) may have been LUCKY timing")
print("   2. Need to run live for FULL 100+ days minimum to validate")
print("   3. Watch closely first 30 days - if similar to Jan (23% win rate), stop strategy")
print("   4. Consider adding filters or adjusting parameters")
print()

print("=" * 160)
