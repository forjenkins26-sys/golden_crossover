"""
THREE STRATEGY COMPARISON
Comparing backtest results on same BTC data (Jan 1 - Apr 10, 2026)
"""

import pandas as pd

print("\n" + "="*220)
print("RSI 30/70 STRATEGY - THREE SCENARIO COMPARISON")
print("="*220)

# Strategy 1: Original (No filters at all)
# From earlier session: paper_trading_rsi_30_70.py
strategy_1 = {
    'Name': 'ORIGINAL (Unfiltered)',
    'LONG_Filter': 'RSI < 30 only',
    'SHORT_Filter': 'RSI > 70 only',
    'Total_Trades': 80,
    'Winning_Trades': 25,
    'Losing_Trades': 55,
    'Win_Rate': 31.2,
    'Gross_PnL': 2375.85,
    'Total_Fees': 1187.00,
    'Net_PnL': 1188.86,
    'Profit_Factor': 1.61,
    'Long_Trades': 37,
    'Long_Wins': 8,
    'Long_WR': 21.6,
    'Long_PnL': -973.82,
    'Short_Trades': 43,
    'Short_Wins': 17,
    'Short_WR': 39.5,
    'Short_PnL': 2162.68,
}

# Strategy 2: Dual Filter
# From backtest_dual_filter_final.py
strategy_2 = {
    'Name': 'DUAL FILTER (Both filtered)',
    'LONG_Filter': 'RSI < 30 AND Price > 200 EMA',
    'SHORT_Filter': 'RSI > 70 AND EMA Slope < 0',
    'Total_Trades': 39,
    'Winning_Trades': 13,
    'Losing_Trades': 26,
    'Win_Rate': 33.3,
    'Gross_PnL': 1472.33,
    'Total_Fees': 570.81,
    'Net_PnL': 901.52,
    'Profit_Factor': 1.34,
    'Long_Trades': 12,
    'Long_Wins': 4,
    'Long_WR': 33.3,
    'Long_PnL': 163.48,
    'Short_Trades': 27,
    'Short_Wins': 9,
    'Short_WR': 33.3,
    'Short_PnL': 738.04,
}

# Strategy 3: Hybrid Filter
# From backtest_hybrid_filter.py
strategy_3 = {
    'Name': 'HYBRID FILTER (SHORT unfiltered)',
    'LONG_Filter': 'RSI < 30 AND Price > 200 EMA',
    'SHORT_Filter': 'RSI > 70 only',
    'Total_Trades': 52,
    'Winning_Trades': 20,
    'Losing_Trades': 32,
    'Win_Rate': 38.5,
    'Gross_PnL': 3099.14,
    'Total_Fees': 778.63,
    'Net_PnL': 2320.51,
    'Profit_Factor': 1.69,
    'Long_Trades': 4,
    'Long_Wins': 3,
    'Long_WR': 75.0,
    'Long_PnL': 685.07,
    'Short_Trades': 48,
    'Short_Wins': 17,
    'Short_WR': 35.4,
    'Short_PnL': 1635.44,
}

strategies = [strategy_1, strategy_2, strategy_3]

# ============================================================================
# MAIN COMPARISON TABLE
# ============================================================================

print("\n" + "="*220)
print("MAIN COMPARISON - OVERALL METRICS")
print("="*220)

comparison_data = []
for s in strategies:
    comparison_data.append({
        'Strategy': s['Name'],
        'Total Trades': s['Total_Trades'],
        'Win Rate': f"{s['Win_Rate']:.1f}%",
        'Gross P&L': f"${s['Gross_PnL']:+.2f}",
        'Total Fees': f"${s['Total_Fees']:+.2f}",
        'Net P&L': f"${s['Net_PnL']:+.2f}",
        'Profit Factor': f"{s['Profit_Factor']:.2f}x",
    })

df_comparison = pd.DataFrame(comparison_data)
print("\n" + df_comparison.to_string(index=False))

# ============================================================================
# NET P&L RANKING
# ============================================================================

print("\n" + "="*220)
print("NET P&L RANKING (Most Important)")
print("="*220)

pnl_ranking = sorted(strategies, key=lambda x: x['Net_PnL'], reverse=True)
print("\n")
for i, s in enumerate(pnl_ranking, 1):
    print(f"{i}. {s['Name']:<40} ${s['Net_PnL']:>10.2f}  "
          f"({s['Total_Trades']:2d} trades, {s['Win_Rate']:5.1f}% WR)")

# ============================================================================
# WIN RATE RANKING
# ============================================================================

print("\n" + "="*220)
print("WIN RATE RANKING (Quality of Entries)")
print("="*220)

wr_ranking = sorted(strategies, key=lambda x: x['Win_Rate'], reverse=True)
print("\n")
for i, s in enumerate(wr_ranking, 1):
    print(f"{i}. {s['Name']:<40} {s['Win_Rate']:>5.1f}%  "
          f"({s['Winning_Trades']:2d} of {s['Total_Trades']} trades)")

# ============================================================================
# PROFIT FACTOR RANKING
# ============================================================================

print("\n" + "="*220)
print("PROFIT FACTOR RANKING (Risk/Reward Balance)")
print("="*220)

pf_ranking = sorted(strategies, key=lambda x: x['Profit_Factor'], reverse=True)
print("\n")
for i, s in enumerate(pf_ranking, 1):
    print(f"{i}. {s['Name']:<40} {s['Profit_Factor']:>5.2f}x  "
          f"(Wins: ${sum([t.get('Winning_Trades', 0) for t in strategies if t==s]):>8} | "
          f"Losses: ${sum([t.get('Losing_Trades', 0) for t in strategies if t==s]):>8})")

# ============================================================================
# DIRECTIONAL ANALYSIS
# ============================================================================

print("\n" + "="*220)
print("DIRECTIONAL ANALYSIS - LONG vs SHORT PERFORMANCE")
print("="*220)

for s in strategies:
    print(f"\n{s['Name']}:")
    print(f"LONG Trades ({s['LONG_Filter']}):")
    print(f"  Count:       {s['Long_Trades']} trades")
    print(f"  Win Rate:    {s['Long_WR']:.1f}%")
    print(f"  Net P&L:     ${s['Long_PnL']:+.2f}")
    print(f"\nSHORT Trades ({s['SHORT_Filter']}):")
    print(f"  Count:       {s['Short_Trades']} trades")
    print(f"  Win Rate:    {s['Short_WR']:.1f}%")
    print(f"  Net P&L:     ${s['Short_PnL']:+.2f}")

# ============================================================================
# SUMMARY & RECOMMENDATION
# ============================================================================

print("\n" + "="*220)
print("ANALYSIS & VERDICT")
print("="*220)

best_pnl = max(strategies, key=lambda x: x['Net_PnL'])
best_wr = max(strategies, key=lambda x: x['Win_Rate'])
best_pf = max(strategies, key=lambda x: x['Profit_Factor'])

print(f"""
🏆 BEST NET P&L:        {best_pnl['Name']:<30} ${best_pnl['Net_PnL']:>10.2f}
🎯 BEST WIN RATE:       {best_wr['Name']:<30} {best_wr['Win_Rate']:>9.1f}%
⚖️  BEST PROFIT FACTOR:  {best_pf['Name']:<30} {best_pf['Profit_Factor']:>9.2f}x


KEY OBSERVATIONS:
═══════════════════════════════════════════════════════════════════════════════════════════════════

1. NET P&L COMPARISON:
   ✓ HYBRID outperforms by ${best_pnl['Net_PnL'] - strategy_1['Net_PnL']:.2f} vs Original
   ✓ HYBRID outperforms by ${best_pnl['Net_PnL'] - strategy_2['Net_PnL']:.2f} vs Dual Filter
   
2. TRADE VOLUME:
   ✓ ORIGINAL: 80 trades (high activity, mean-reversion heavy)
   ✓ DUAL:     39 trades (selective, both sides filtered)
   ✓ HYBRID:   52 trades (balanced - only LONG filtered)

3. WIN RATE QUALITY:
   ✓ HYBRID:   38.5% (best) - Indicates good entry timing
   ✓ DUAL:     33.3% (good) - But lower volume/opportunity
   ✓ ORIGINAL: 31.2% (weakest) - No filters, noisy entries

4. DIRECTIONAL DEPENDENCE:
   
   ORIGINAL: Relies heavily on SHORTS (+$2,162.68) 
            LONG side losing (-$973.82) = RISKY in bull market
            
   HYBRID:   Similar structure, but LONG side was already filtered
            Better LONG WR (75%) shows filter working
            SHORT side still strong (+$1,635.44)
            
   DUAL:     Both sides protected by filters
            More balanced P&L distribution
            But fewer opportunities captured

5. RISK PROFILE:
   ✓ ORIGINAL: Highest risk - unfiltered entries, trend-dependent
   ✓ HYBRID:   Medium risk - LONG protected, SHORT trend-exposed
   ✓ DUAL:     Lowest risk - Both sides filtered, more conservative

6. PROFIT CONSISTENCY:
   ✓ HYBRID:   1.69x Profit Factor (strong)
   ✓ ORIGINAL: 1.61x Profit Factor (very good)
   ✓ DUAL:     1.34x Profit Factor (acceptable)


DECISION MATRIX:
═══════════════════════════════════════════════════════════════════════════════════════════════════

Strategy        Net P&L    Win Rate   Profit Fac   Trades   Recommendation
────────────────────────────────────────────────────────────────────────────────────────────────
ORIGINAL        +1,188.86  31.2%      1.61x        80       ⚠️ Risky - no protections
DUAL            +901.52    33.3%      1.34x        39       ⚠️ Too conservative
HYBRID          +2,320.51  38.5%      1.69x        52       ✅ BEST BALANCE


FINAL VERDICT FOR PAPER TRADING:
═════════════════════════════════════════════════════════════════════════════════════════════════════

→ RECOMMEND: HYBRID FILTER STRATEGY

WHY:
   1. Highest net PnL ($2,320.51) - 95% gain vs Original, 157% vs Dual
   2. Best win rate (38.5%) - More confident entries
   3. Best profit factor (1.69x) - Optimal risk/reward
   4. Good middle ground - Protects LONG but allows SHORT opportunities
   5. Balanced trade volume (52) - Not over-trading like Original, not under-trading like Dual

HYBRID FILTER CONFIG FOR PAPER TRADING:
════════════════════════════════════════
   ✓ LONG:   RSI < 30 AND Price > 200 EMA
   ✓ SHORT:  RSI > 70 (unfiltered)
   
   This gives you:
   • Strong directional conviction for LONGS (must be in uptrend)
   • Flexibility to capture SHORT momentum (proven effective)
   • 4 LONG trades with 75% win rate (high quality)
   • 48 SHORT trades with 35.4% win rate (good volume)
   • $2,320 net profit on historical data = solid baseline

NEXT STEP:
   Deploy HYBRID FILTER to paper trading for 2-4 weeks.
   If it maintains similar profit factor and win rate, move to real money.

═════════════════════════════════════════════════════════════════════════════════════════════════════
""")

print("="*220 + "\n")
