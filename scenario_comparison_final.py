"""
FINAL COMPARISON: ALL FOUR SCENARIOS
1H Candles - April 24, 2024 to April 10, 2026
Same RSI Period (14), Same Exit Logic, Same Fees (0.2% roundtrip)
"""

import pandas as pd

print("\n" + "="*220)
print("ULTIMATE SCENARIO COMPARISON - ALL FOUR STRATEGIES (1H DATA)")
print("="*220)

# Summary data
scenarios = {
    'Scenario 1': {
        'Name': 'Raw RSI (No Filters)',
        'Entry Logic': 'LONG: RSI<30 | SHORT: RSI>70',
        'Circuit Breaker': 'No',
        'Total Trades': 502,
        'Win Rate': 27.1,
        'Net P&L': 1470.77,
        'Profit Factor': 1.03,
        '2024 Trades': 196,
        '2024 P&L': -2614.40,
        '2025 Trades': 220,
        '2025 P&L': 3241.60,
        '2026 Trades': 86,
        '2026 P&L': 843.57,
    },
    'Scenario 2': {
        'Name': 'DUAL Filter (Both Sides)',
        'Entry Logic': 'LONG: RSI<30 & P>200E | SHORT: RSI>70 & EMA↓',
        'Circuit Breaker': 'No',
        'Total Trades': 263,
        'Win Rate': 29.3,
        'Net P&L': 3250.23,
        'Profit Factor': 1.15,
        '2024 Trades': 91,
        '2024 P&L': -393.07,
        '2025 Trades': 127,
        '2025 P&L': 2561.76,
        '2026 Trades': 45,
        '2026 P&L': 1081.54,
    },
    'Scenario 3': {
        'Name': 'HYBRID Filter (LONG Only)',
        'Entry Logic': 'LONG: RSI<30 & P>200E | SHORT: RSI>70',
        'Circuit Breaker': 'No',
        'Total Trades': 357,
        'Win Rate': 29.1,
        'Net P&L': 4804.01,
        'Profit Factor': 1.16,
        '2024 Trades': 138,
        '2024 P&L': -956.98,
        '2025 Trades': 161,
        '2025 P&L': 3249.64,
        '2026 Trades': 58,
        '2026 P&L': 2511.35,
    },
    'Scenario 4': {
        'Name': 'HYBRID + Circuit Breaker',
        'Entry Logic': 'LONG: RSI<30 & P>200E | SHORT: RSI>70',
        'Circuit Breaker': 'Yes ($500/month)',
        'Total Trades': 250,
        'Win Rate': 26.0,
        'Net P&L': -843.21,
        'Profit Factor': 0.96,
        '2024 Trades': 101,
        '2024 P&L': -1422.78,
        '2025 Trades': 100,
        '2025 P&L': -1191.12,
        '2026 Trades': 49,
        '2026 P&L': 1770.68,
    },
}

print("\n" + "="*220)
print("OVERALL COMPARISON TABLE (Apr 24 2024 - Apr 10 2026)")
print("="*220)
print()
print(f"{'Scenario':<25} {'Total Trades':<15} {'Win Rate':<15} {'Net P&L':<20} {'Profit Factor':<15}")
print("-" * 220)
for key, data in scenarios.items():
    print(f"{key:<25} {int(data['Total Trades']):<15} {data['Win Rate']:.1f}%{'':<10} ${data['Net P&L']:>+15.2f}  {data['Profit Factor']:>14.2f}x")
print()

print("\n" + "="*220)
print("YEARLY BREAKDOWN - ALL SCENARIOS")
print("="*220)
print()

# 2024
print("YEAR 2024:")
print(f"{'Scenario':<25} {'Trades':<12} {'P&L':<20}")
print("-" * 220)
for key, data in scenarios.items():
    print(f"{key:<25} {int(data['2024 Trades']):<12} ${data['2024 P&L']:>+15.2f}")
print()

# 2025
print("YEAR 2025:")
print(f"{'Scenario':<25} {'Trades':<12} {'P&L':<20}")
print("-" * 220)
for key, data in scenarios.items():
    print(f"{key:<25} {int(data['2025 Trades']):<12} ${data['2025 P&L']:>+15.2f}")
print()

# 2026
print("YEAR 2026 (Partial - Apr 24 - Apr 10):")
print(f"{'Scenario':<25} {'Trades':<12} {'P&L':<20}")
print("-" * 220)
for key, data in scenarios.items():
    print(f"{key:<25} {int(data['2026 Trades']):<12} ${data['2026 P&L']:>+15.2f}")
print()

print("\n" + "="*220)
print("KEY FINDINGS")
print("="*220)
print()

print("1. PROFITABILITY RANKING (by Net P&L):")
print("   🥇 Scenario 3 (HYBRID):        $+4,804.01  ← BEST ABSOLUTE PROFIT")
print("   🥈 Scenario 2 (DUAL):          $+3,250.23")
print("   🥉 Scenario 1 (Raw RSI):       $+1,470.77")
print("   ❌ Scenario 4 (HYBRID + CB):    $-843.21   ← WORSE THAN BREAKEVEN")
print()

print("2. WIN RATE RANKING:")
print("   🥇 Scenario 2 (DUAL):          29.3%")
print("   🥈 Scenario 3 (HYBRID):        29.1%")
print("   🥉 Scenario 1 (Raw RSI):       27.1%")
print("   ❌ Scenario 4 (HYBRID + CB):    26.0%")
print()

print("3. PROFIT FACTOR RANKING:")
print("   🥇 Scenario 3 (HYBRID):        1.16x")
print("   🥈 Scenario 2 (DUAL):          1.15x")
print("   🥉 Scenario 1 (Raw RSI):       1.03x")
print("   ❌ Scenario 4 (HYBRID + CB):    0.96x  ← MONEY LOSING")
print()

print("4. TRADE VOLUME RANKING:")
print("   🥇 Scenario 1 (Raw RSI):       502 trades  ← Most opportunities")
print("   🥈 Scenario 3 (HYBRID):        357 trades  ← Good balance")
print("   🥉 Scenario 2 (DUAL):          263 trades  ← Selective")
print("   ❌ Scenario 4 (HYBRID + CB):    250 trades  ← Too defensive")
print()

print("5. YEAR-BY-YEAR ANALYSIS:")
print()
print("   2024 (Choppy Market):")
print("   - All scenarios LOST money in 2024:")
print("     S1: -$2,614 | S2: -$393 | S3: -$957 | S4: -$1,423")
print("   - BEST performer: Scenario 2 (DUAL)")
print()
print("   2025 (Trending Up):")
print("   - Scenario 4 is UNPROFITABLE even in bull market:")
print("     S1: +$3,242 | S2: +$2,562 | S3: +$3,250 | S4: -$1,191")
print("   - BEST performers: Scenario 1 or Scenario 3")
print()
print("   2026 (YTD):")
print("   - Scenario 4 finally profitable, but still worst overall:")
print("     S1: +$844 | S2: +$1,082 | S3: +$2,511 | S4: +$1,771")
print("   - BEST performer: Scenario 3")
print()

print("\n" + "="*220)
print("CRITICAL FINDING: CIRCUIT BREAKER CATASTROPHIC FAILURE")
print("="*220)
print()
print("⚠️  THE MONTHLY CIRCUIT BREAKER DESTROYS PROFITABILITY!")
print()
print("   Scenario 3 (No CB):      $+4,804.01")
print("   Scenario 4 (With CB):    $-843.21")
print("   Loss from CB:            -$5,647.22")
print()
print("The circuit breaker triggered 17 times (May, Jul, Sep, Oct, Nov 2024 etc)")
print("Each trigger blocked entries for the REST OF MONTH, missing subsequent wins.")
print()
print("CONCLUSION: Circuit breaker with $500 limit is TOO AGGRESSIVE for 1H data.")
print("The strategy's intra-month volatility is too high to sustain a $500 daily loss limit.")
print()

print("\n" + "="*220)
print("FINAL VERDICT")
print("="*220)
print()
print("🏆 WINNER: SCENARIO 3 - HYBRID FILTER (LONG FILTERED, SHORT UNFILTERED)")
print()
print("Scenario 3 Performance:")
print("  ✅ Highest profit: $+4,804.01 (48% more than DUAL, 226% more than Raw RSI)")
print("  ✅ Win rate: 29.1% (nearly tied with DUAL)")
print("  ✅ Profit factor: 1.16x (best)")
print("  ✅ 357 trades across 2 years = statistically reliable")
print("  ✅ Balanced trade frequency for active management")
print("  ✅ Dominates 2025-2026 bull market")
print("  ✅ Accepts 2024 loss (-$957) as market condition, not strategy failure")
print()

print("Why Scenario 2 (DUAL) is Runner-Up:")
print("  ✅ Best win rate: 29.3%")
print("  ✅ Lowest losses in bad market: -$393 in 2024")
print("  ❌ $1.5B lower profit than Scenario 3 (32% less absolute money)")
print("  ❌ Only 263 trades (smaller sample size)")
print("  ❌ Filters out TOO MANY profitable opportunities")
print()

print("Why Scenario 1 (Raw RSI) Underperforms:")
print("  ❌ Massive 2024 loss: -$2,614 (2.7x worse than HYBRID)")
print("  ❌ Lowest profit factor: 1.03x (barely break-even quality)")
print("  ❌ 502 trades but low quality = worse risk/reward")
print("  ✅ No filters = maximum trade opportunities")
print()

print("Why Scenario 4 (Circuit Breaker) FAILS:")
print("  ❌ UNPROFITABLE: -$843.21")
print("  ❌ Circuit breaker triggered 17 times!")
print("  ❌ Blocked entries into WINNING markets")
print("  ❌ Lost $5,647 compared to Scenario 3")
print("  ❌ Even 2025 bull market turned unprofitable (-$1,191)")
print("  ✅ CONCLUSION: Circuit breaker is counterproductive for hourly trading")
print()

print("="*220 + "\n")
