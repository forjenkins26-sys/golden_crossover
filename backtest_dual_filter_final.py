"""
RSI 30/70 STRATEGY - BOTH FILTERS IMPLEMENTED
LONG: RSI < 30 AND price > 200 EMA
SHORT: RSI > 70 AND 200 EMA slope < 0

Output:
1. Trade-by-trade detailed list (console + CSV)
2. Overall summary stats
3. Direction breakdown table
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*200)
print("RSI 30/70 STRATEGY - DUAL FILTER IMPLEMENTATION")
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
df['EMA_slope'] = (df['EMA_200'].diff(20) / 20)  # EMA slope over 20 bars

df = df.dropna()

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")

# Session filter
df['InSession'] = df.index.map(lambda x: (0.5 <= x.hour + x.minute/60 < 4.5) or 
                                          (5.5 <= x.hour + x.minute/60 < 11.5) or 
                                          (12.5 <= x.hour + x.minute/60 < 17.5))

# Parameters
ENTRY_COST_RATE = 0.0010   # 0.10%
EXIT_COST_RATE = 0.0010    # 0.10%
POSITION_SIZE = 0.1  # BTC
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
    ema_slope = float(row['EMA_slope'])
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
        # SHORT: RSI > 70 AND EMA slope < 0 (declining)
        if rsi > RSI_SHORT and ema_slope < 0:
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
    
    # Display trade list
    print(f"\n{'Trade':<6} {'Date':<17} {'Type':<6} {'Entry':<12} {'Exit':<12} {'Result':<4} {'Net_PnL':<12} {'Cumulative':<12}")
    print("-" * 200)
    
    for _, trade in df_trades.iterrows():
        print(f"{int(trade['Trade_Num']):<6} {trade['Date']:<17} {trade['Type']:<6} "
              f"${trade['Entry_Price']:>10.2f}  ${trade['Exit_Price']:>10.2f}  {trade['Result']:<4} "
              f"${trade['Net_PnL']:>10.2f}  ${trade['Cumulative_PnL']:>10.2f}")
    
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
        print(f"  ├─ Win Rate:       {long_wr:.1f}% ({long_wins} of {len(longs)})")
        print(f"  ├─ Best Trade:     ${longs['Net_PnL'].max():+.2f}")
        print(f"  ├─ Worst Trade:    ${longs['Net_PnL'].min():+.2f}")
        print(f"  └─ Net P&L:        ${long_pnl:+.2f}")
    else:
        print(f"  └─ No LONG trades taken")
    
    print(f"\nSHORT TRADES (RSI > 70 + EMA Slope < 0):")
    if len(shorts) > 0:
        short_wins = len(shorts[shorts['Net_PnL'] > 0])
        short_wr = short_wins / len(shorts) * 100
        short_pnl = shorts['Net_PnL'].sum()
        print(f"  ├─ Trade Count:    {len(shorts)}")
        print(f"  ├─ Win Rate:       {short_wr:.1f}% ({short_wins} of {len(shorts)})")
        print(f"  ├─ Best Trade:     ${shorts['Net_PnL'].max():+.2f}")
        print(f"  ├─ Worst Trade:    ${shorts['Net_PnL'].min():+.2f}")
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
            'Win Rate': f"{long_wr:.1f}%",
            'Net P&L': f"${long_pnl:+.2f}",
        })
    
    if len(shorts) > 0:
        comparison_data.append({
            'Direction': 'SHORT',
            'Trades': len(shorts),
            'Wins': len(shorts[shorts['Net_PnL'] > 0]),
            'Losses': len(shorts[shorts['Net_PnL'] < 0]),
            'Win Rate': f"{short_wr:.1f}%",
            'Net P&L': f"${short_pnl:+.2f}",
        })
    
    comparison_data.append({
        'Direction': 'TOTAL',
        'Trades': total_trades,
        'Wins': winning_trades,
        'Losses': losing_trades,
        'Win Rate': f"{win_rate:.1f}%",
        'Net P&L': f"${total_net:+.2f}",
    })
    
    df_comparison = pd.DataFrame(comparison_data)
    print("\n" + df_comparison.to_string(index=False))
    
    # ============================================================================
    # EXPORT TO CSV
    # ============================================================================
    
    # Prepare export data
    export_df = df_trades[['Trade_Num', 'Date', 'Type', 'Entry_Price', 'Exit_Price', 
                            'Result', 'Gross_PnL', 'Entry_Cost', 'Exit_Cost', 
                            'Net_PnL', 'Cumulative_PnL', 'Duration_hrs']].copy()
    
    export_df.columns = ['Trade', 'Date', 'Direction', 'Entry_Price', 'Exit_Price', 
                         'Result', 'Gross_PnL', 'Entry_Fee', 'Exit_Fee', 
                         'Net_PnL', 'Cumulative_PnL', 'Duration_Hours']
    
    # Save to desktop
    desktop_path = "D:/RSI_30_70_DUAL_FILTER_Trades.csv"
    export_df.to_csv(desktop_path, index=False)
    print(f"\n✓ Trade list exported to: {desktop_path}")
    
    # Also save in project
    project_path = "rsi_dual_filter_trades.csv"
    export_df.to_csv(project_path, index=False)
    print(f"✓ Trade list also saved to: {project_path}")
    
else:
    print("\n✗ No trades were taken during the backtest period")

print("\n" + "="*200 + "\n")
