"""
RSI 30/70 STRATEGY - HYBRID FILTER SCENARIO
SHORT: RSI > 70 only (original, unfiltered)
LONG: RSI < 30 AND price > 200 EMA (keep the filter)

Output:
1. Trade-by-trade list
2. Overall summary
3. Direction breakdown
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*200)
print("RSI 30/70 STRATEGY - HYBRID FILTER (SHORT unfiltered + LONG with 200 EMA)")
print("="*200)

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

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")

# Session filter
df['InSession'] = df.index.map(lambda x: (0.5 <= x.hour + x.minute/60 < 4.5) or 
                                          (5.5 <= x.hour + x.minute/60 < 11.5) or 
                                          (12.5 <= x.hour + x.minute/60 < 17.5))

# Parameters
ENTRY_COST_RATE = 0.0010
EXIT_COST_RATE = 0.0010
POSITION_SIZE = 0.1
RSI_LONG = 30
RSI_SHORT = 70
TP_PCT = 0.04
SL_PCT = 0.012

trades = []
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0
entry_date = None
trade_num = 0

print("\n[Starting backtest...]")

for idx in range(len(df)):
    row = df.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    ema_200 = float(row['EMA_200'])
    in_session = row['InSession'].item() if hasattr(row['InSession'], 'item') else bool(row['InSession'])
    current_date = row.name
    
    # EXIT LOGIC
    if in_trade:
        exit_triggered = False
        exit_type = None
        exit_price = 0
        
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
            # Calculate P&L
            if trade_type == 'LONG':
                gross_pnl = (exit_price - entry_price) * POSITION_SIZE
            else:
                gross_pnl = (entry_price - exit_price) * POSITION_SIZE
            
            entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
            exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
            net_pnl = gross_pnl - entry_cost - exit_cost
            
            cumulative_pnl = sum([t['Net_PnL'] for t in trades]) + net_pnl
            
            trades.append({
                'Trade_Num': trade_num,
                'Date': current_date.strftime('%Y-%m-%d %H:%M'),
                'Type': trade_type,
                'Entry_Price': entry_price,
                'Exit_Price': exit_price,
                'Result': exit_type,
                'Gross_PnL': gross_pnl,
                'Entry_Cost': entry_cost,
                'Exit_Cost': exit_cost,
                'Net_PnL': net_pnl,
                'Cumulative_PnL': cumulative_pnl,
                'Duration_hrs': (current_date - entry_date).total_seconds() / 3600,
            })
            
            trade_num += 1
            in_trade = False
    
    # ENTRY LOGIC
    if not in_trade and in_session:
        # SHORT: RSI > 70 ONLY (no filter)
        if rsi > RSI_SHORT:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            entry_date = current_date
            tp = price * (1 - TP_PCT)
            sl = price * (1 + SL_PCT)
        
        # LONG: RSI < 30 AND price > EMA_200
        elif rsi < RSI_LONG and price > ema_200:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            entry_date = current_date
            tp = price * (1 + TP_PCT)
            sl = price * (1 - SL_PCT)

# ============================================================================
# RESULTS PROCESSING
# ============================================================================

df_trades = pd.DataFrame(trades)

if len(df_trades) > 0:
    # Overall stats
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['Net_PnL'] > 0])
    losing_trades = len(df_trades[df_trades['Net_PnL'] < 0])
    breakeven_trades = len(df_trades[df_trades['Net_PnL'] == 0])
    win_rate = winning_trades / total_trades * 100
    
    total_gross = df_trades['Gross_PnL'].sum()
    total_fees = df_trades['Entry_Cost'].sum() + df_trades['Exit_Cost'].sum()
    total_net = df_trades['Net_PnL'].sum()
    
    total_wins = df_trades[df_trades['Net_PnL'] > 0]['Net_PnL'].sum()
    total_loss = abs(df_trades[df_trades['Net_PnL'] < 0]['Net_PnL'].sum())
    pf = total_wins / total_loss if total_loss > 0 else 0
    
    # Direction splits
    longs = df_trades[df_trades['Type'] == 'LONG']
    shorts = df_trades[df_trades['Type'] == 'SHORT']
    
    print("\n" + "="*200)
    print("PART 1: TRADE-BY-TRADE LIST")
    print("="*200)
    
    # Display trade list (sample - first/last trades)
    print(f"\n{'Trade':<6} {'Date':<17} {'Type':<6} {'Entry':<12} {'Exit':<12} {'Result':<4} {'Net_PnL':<12} {'Cumulative':<12}")
    print("-" * 200)
    
    # Show first 10 and last 5
    for i, (idx, trade) in enumerate(df_trades.iterrows()):
        if i < 10 or i >= len(df_trades) - 5:
            print(f"{int(trade['Trade_Num']):<6} {trade['Date']:<17} {trade['Type']:<6} "
                  f"${trade['Entry_Price']:>10.2f}  ${trade['Exit_Price']:>10.2f}  {trade['Result']:<4} "
                  f"${trade['Net_PnL']:>10.2f}  ${trade['Cumulative_PnL']:>10.2f}")
        elif i == 10:
            print("... (showing first 10 and last 5 trades, see CSV for complete list)")
    
    print("\n" + "="*200)
    print("PART 2: OVERALL SUMMARY")
    print("="*200)
    
    print(f"""
Total Trades:              {total_trades}
├─ Winning Trades:        {winning_trades}
├─ Losing Trades:         {losing_trades}
└─ Breakeven Trades:      {breakeven_trades}

Win Rate:                  {win_rate:.1f}%

Gross P&L:                 ${total_gross:+.2f}
Total Fees Paid:           ${total_fees:+.2f}
NET P&L:                   ${total_net:+.2f}

Profit Factor:             {pf:.2f}x
""")
    
    print("="*200)
    print("PART 3: DIRECTION BREAKDOWN")
    print("="*200)
    
    print(f"\nLONG TRADES (RSI < 30 + Price > 200 EMA):")
    if len(longs) > 0:
        long_wins = len(longs[longs['Net_PnL'] > 0])
        long_wr = long_wins / len(longs) * 100
        long_pnl = longs['Net_PnL'].sum()
        print(f"  ├─ Trade Count:    {len(longs)}")
        print(f"  ├─ Wins / Losses:  {long_wins} / {len(longs) - long_wins}")
        print(f"  ├─ Win Rate:       {long_wr:.1f}%")
        print(f"  └─ Net P&L:        ${long_pnl:+.2f}")
    else:
        print(f"  └─ No LONG trades taken")
    
    print(f"\nSHORT TRADES (RSI > 70, NO FILTER):")
    if len(shorts) > 0:
        short_wins = len(shorts[shorts['Net_PnL'] > 0])
        short_wr = short_wins / len(shorts) * 100
        short_pnl = shorts['Net_PnL'].sum()
        print(f"  ├─ Trade Count:    {len(shorts)}")
        print(f"  ├─ Wins / Losses:  {short_wins} / {len(shorts) - short_wins}")
        print(f"  ├─ Win Rate:       {short_wr:.1f}%")
        print(f"  └─ Net P&L:        ${short_pnl:+.2f}")
    else:
        print(f"  └─ No SHORT trades taken")
    
    print("\n" + "="*200)
    print("DIRECTION COMPARISON TABLE")
    print("="*200)
    
    comparison_data = []
    if len(longs) > 0:
        comparison_data.append({
            'Direction': 'LONG',
            'Trades': len(longs),
            'Wins': len(longs[longs['Net_PnL'] > 0]),
            'Losses': len(longs[longs['Net_PnL'] < 0]),
            'Win_Rate': f"{long_wr:.1f}%",
            'Net_PnL': f"${long_pnl:+.2f}",
        })
    
    if len(shorts) > 0:
        comparison_data.append({
            'Direction': 'SHORT',
            'Trades': len(shorts),
            'Wins': len(shorts[shorts['Net_PnL'] > 0]),
            'Losses': len(shorts[shorts['Net_PnL'] < 0]),
            'Win_Rate': f"{short_wr:.1f}%",
            'Net_PnL': f"${short_pnl:+.2f}",
        })
    
    comparison_data.append({
        'Direction': 'TOTAL',
        'Trades': total_trades,
        'Wins': winning_trades,
        'Losses': losing_trades,
        'Win_Rate': f"{win_rate:.1f}%",
        'Net_PnL': f"${total_net:+.2f}",
    })
    
    df_comparison = pd.DataFrame(comparison_data)
    print("\n" + df_comparison.to_string(index=False))
    
    # ============================================================================
    # EXPORT TO CSV
    # ============================================================================
    
    export_df = df_trades[['Trade_Num', 'Date', 'Type', 'Entry_Price', 'Exit_Price', 
                            'Result', 'Gross_PnL', 'Entry_Cost', 'Exit_Cost', 
                            'Net_PnL', 'Cumulative_PnL', 'Duration_hrs']].copy()
    
    export_df.columns = ['Trade', 'Date', 'Direction', 'Entry_Price', 'Exit_Price', 
                         'Result', 'Gross_PnL', 'Entry_Fee', 'Exit_Fee', 
                         'Net_PnL', 'Cumulative_PnL', 'Duration_Hours']
    
    project_path = "rsi_hybrid_filter_trades.csv"
    export_df.to_csv(project_path, index=False)
    print(f"\n✓ Trade list exported to: {project_path}")
    
    # Store results for comparison
    hybrid_results = {
        'Total_Trades': total_trades,
        'Winning_Trades': winning_trades,
        'Win_Rate': win_rate,
        'Gross_PnL': total_gross,
        'Total_Fees': total_fees,
        'Net_PnL': total_net,
        'Profit_Factor': pf,
        'Long_Trades': len(longs),
        'Short_Trades': len(shorts),
        'Long_PnL': longs['Net_PnL'].sum() if len(longs) > 0 else 0,
        'Short_PnL': shorts['Net_PnL'].sum() if len(shorts) > 0 else 0,
    }
    
    # Save to Python file for comparison script
    import json
    with open('hybrid_results.json', 'w') as f:
        json.dump(hybrid_results, f, indent=2)
    
else:
    print("\n✗ No trades were taken during the backtest period")

print("\n" + "="*200 + "\n")
