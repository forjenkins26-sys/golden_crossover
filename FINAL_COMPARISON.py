"""
THREE STRATEGY COMPARISON - FINAL
Comparing all three strategies side by side
"""

import pandas as pd

print("\n" + "="*200)
print("RSI 30/70 STRATEGY - THREE SCENARIO COMPARISON & FINAL VERDICT")
print("="*200)

# Strategy 1: Original (No filters)
strategy_1 = {
    'Name': 'ORIGINAL (Unfiltered)',
    'LONG': 'RSI < 30 only',
    'SHORT': 'RSI > 70 only',
    'Total_Trades': 80,
    'Win_Rate': 31.2,
    'Net_PnL': 1188.86,
    'Profit_Factor': 1.61,
    'Long_Trades': 37,
    'Long_WR': 21.6,
    'Long_PnL': -973.82,
    'Short_Trades': 43,
    'Short_WR': 39.5,
    'Short_PnL': 2162.68,
}

# Strategy 2: Dual Filter
strategy_2 = {
    'Name': 'DUAL FILTER (Both filtered)',
    'LONG': 'RSI < 30 AND Price > 200 EMA',
    'SHORT': 'RSI > 70 AND EMA Slope < 0',
    'Total_Trades': 39,
    'Win_Rate': 33.3,
    'Net_PnL': 901.52,
    'Profit_Factor': 1.34,
    'Long_Trades': 12,
    'Long_WR': 33.3,
    'Long_PnL': 163.48,
    'Short_Trades': 27,
    'Short_WR': 33.3,
    'Short_PnL': 738.04,
}

# Strategy 3: Hybrid Filter
strategy_3 = {
    'Name': 'HYBRID FILTER (SHORT unfiltered)',
    'LONG': 'RSI < 30 AND Price > 200 EMA',
    'SHORT': 'RSI > 70 only',
    'Total_Trades': 52,
    'Win_Rate': 38.5,
    'Net_PnL': 2320.51,
    'Profit_Factor': 1.69,
    'Long_Trades': 4,
    'Long_WR': 75.0,
    'Long_PnL': 685.07,
    'Short_Trades': 48,
    'Short_WR': 35.4,
    'Short_PnL': 1635.44,
}

strategies = [strategy_1, strategy_2, strategy_3]

# ============================================================================
print("\nMAIN COMPARISON - OVERALL METRICS")
print("="*200)

comparison_rows = []
for s in strategies:
    comparison_rows.append({
        'Strategy': s['Name'],
        'Trades': s['Total_Trades'],
        'Win Rate': f"{s['Win_Rate']:.1f}%",
        'Net PnL': f"${s['Net_PnL']:+.2f}",
        'Profit Factor': f"{s['Profit_Factor']:.2f}x",
    })

df = pd.DataFrame(comparison_rows)
print("\n" + df.to_string(index=False))

# ============================================================================
print("\n\nNET P&L RANKING (Most Important)")
print("="*200)

pnl_ranking = sorted(strategies, key=lambda x: x['Net_PnL'], reverse=True)
for i, s in enumerate(pnl_ranking, 1):
    print(f"{i}. {s['Name']:<40} ${s['Net_PnL']:>10.2f}  (WR: {s['Win_Rate']:.1f}%)")

# ============================================================================
print("\n\nWIN RATE RANKING")
print("="*200)

wr_ranking = sorted(strategies, key=lambda x: x['Win_Rate'], reverse=True)
for i, s in enumerate(wr_ranking, 1):
    print(f"{i}. {s['Name']:<40} {s['Win_Rate']:>5.1f}%")

# ============================================================================
print("\n\nPROFIT FACTOR RANKING")
print("="*200)

pf_ranking = sorted(strategies, key=lambda x: x['Profit_Factor'], reverse=True)
for i, s in enumerate(pf_ranking, 1):
    print(f"{i}. {s['Name']:<40} {s['Profit_Factor']:>5.2f}x")

# ============================================================================
print("\n\nDIRECTIONAL ANALYSIS")
print("="*200)

for s in strategies:
    print(f"\n{s['Name']}:")
    print(f"  LONG ({s['LONG']}):")
    print(f"    Trades: {s['Long_Trades']}, Win Rate: {s['Long_WR']:.1f}%, PnL: ${s['Long_PnL']:+.2f}")
    print(f"  SHORT ({s['SHORT']}):")
    print(f"    Trades: {s['Short_Trades']}, Win Rate: {s['Short_WR']:.1f}%, PnL: ${s['Short_PnL']:+.2f}")

# ============================================================================
print("\n\n" + "="*200)
print("FINAL VERDICT")
print("="*200)

print(f"""
*** KEY FINDINGS:

1. NET P&L:
   - HYBRID:   $2,320.51 (95% better than Original, 157% better than Dual)
   - ORIGINAL: $1,188.86
   - DUAL:     $  901.52

2. WIN RATE:
   - HYBRID:   38.5% (Best quality entries)
   - DUAL:     33.3%
   - ORIGINAL: 31.2%

3. PROFIT FACTOR:
   - HYBRID:   1.69x (Healthy risk/reward)
   - ORIGINAL: 1.61x (Good)
   - DUAL:     1.34x (Acceptable)

4. TRADE VOLUME:
   - ORIGINAL: 80 trades (Over-trading?)
   - HYBRID:   52 trades (Balanced)
   - DUAL:     39 trades (Too conservative)

5. DIRECTIONAL DEPENDENCE:
   - ORIGINAL: LONGS losing (-$974), SHORTS carrying (+$2,163) = Risky in bull market
   - HYBRID:   LONGS filtered with 75% WR (+$685), SHORTS strong (+$1,635) = Good balance
   - DUAL:     Both protected, fewer opportunities = Too cautious


RECOMMENDED STRATEGY FOR PAPER TRADING: HYBRID FILTER
=====================================================

Configuration:
  - LONG:  RSI < 30 AND Price > 200 EMA (filtered)
  - SHORT: RSI > 70 only (unfiltered)

Why HYBRID wins:
  1. Highest net profit on historical data ($2,320.51)
  2. Best win rate (38.5%) - highest conviction entries
  3. Best profit factor (1.69x) - optimal reward/risk
  4. Balanced between opportunity and protection
  5. Only 4 LONG trades but all high quality (75% WR)
  6. 48 SHORT trades capturing real momentum (35.4% WR)

Next Steps:
  1. Deploy HYBRID to paper trading immediately
  2. Run for 2-4 weeks (target 30+ trades minimum)
  3. Monitor: Win rate, profit factor, daily limits
  4. If paper trading validates, move to real money with small capital

""")

print("="*200 + "\n")
