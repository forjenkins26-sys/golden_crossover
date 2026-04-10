"""
RSI 30/70 STRATEGY - DELTA EXCHANGE FEE CALCULATION
Recalculates trades with actual Delta Exchange fees
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*180)
print("RSI 30/70 STRATEGY - DELTA EXCHANGE FEE STRUCTURE")
print("="*180)

# Delta Exchange fees structure
MAKER_FEE = 0.0001    # 0.01% maker
TAKER_FEE = 0.0005    # 0.05% taker
ENTRY_SLIPPAGE = 0.0005   # 0.05% entry slippage
EXIT_SLIPPAGE = 0.0005    # 0.05% exit slippage

# Assume market orders (paying taker fee + slippage)
ENTRY_COST_RATE = TAKER_FEE + ENTRY_SLIPPAGE  # 0.10%
EXIT_COST_RATE = TAKER_FEE + EXIT_SLIPPAGE    # 0.10%

print(f"\n[DELTA EXCHANGE FEE STRUCTURE]")
print(f"   Maker Fee:           0.01%")
print(f"   Taker Fee:           0.05%")
print(f"   Entry Slippage:      0.05%")
print(f"   Exit Slippage:       0.05%")
print(f"   Entry Cost (Taker):  {ENTRY_COST_RATE*100:.2f}% ({TAKER_FEE*100:.2f}% fee + {ENTRY_SLIPPAGE*100:.2f}% slippage)")
print(f"   Exit Cost (Taker):   {EXIT_COST_RATE*100:.2f}% ({TAKER_FEE*100:.2f}% fee + {EXIT_SLIPPAGE*100:.2f}% slippage)")
print(f"   Round-trip Cost:     {(ENTRY_COST_RATE + EXIT_COST_RATE)*100:.2f}%\n")

# Fetch data
print("[Fetching BTC-USD data...]")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Calculate RSI
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df = df.dropna()

# Session filter
df['InSession'] = df.index.map(lambda x: (0.5 <= x.hour + x.minute/60 < 4.5) or 
                                          (5.5 <= x.hour + x.minute/60 < 11.5) or 
                                          (12.5 <= x.hour + x.minute/60 < 17.5))

# Settings
RSI_LONG = 30
RSI_SHORT = 70
TP_PCT = 0.04
SL_PCT = 0.012
POSITION_SIZE = 0.1  # BTC

print(f"[Backtesting RSI {RSI_LONG}/{RSI_SHORT} Strategy]")
print(f"   Position Size: {POSITION_SIZE} BTC")
print(f"   Take Profit: {TP_PCT*100:.1f}% | Stop Loss: {SL_PCT*100:.2f}%\n")

trades = []
in_trade = False
entry_price = 0
trade_type = None
tp = sl = 0
entry_date = None
entry_rsi = 0

for idx in range(len(df)):
    row = df.iloc[idx]
    price = float(row['Close'])
    rsi = float(row['RSI'])
    in_session = row['InSession'].item() if hasattr(row['InSession'], 'item') else bool(row['InSession'])
    current_date = row.name
    
    # EXIT
    if in_trade:
        exit_triggered = False
        exit_type = None
        
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
            # Calculate P&L with Delta fees
            if trade_type == 'LONG':
                gross_pnl = (exit_price - entry_price) * POSITION_SIZE
            else:
                gross_pnl = (entry_price - exit_price) * POSITION_SIZE
            
            # Entry cost: Taker fee + slippage on entry price
            entry_cost = entry_price * POSITION_SIZE * ENTRY_COST_RATE
            
            # Exit cost: Taker fee + slippage on exit price
            exit_cost = exit_price * POSITION_SIZE * EXIT_COST_RATE
            
            # Net P&L
            net_pnl = gross_pnl - entry_cost - exit_cost
            
            trades.append({
                'Date': current_date.strftime('%Y-%m-%d %H:%M'),
                'Type': trade_type,
                'Entry_Price': entry_price,
                'Exit_Price': exit_price,
                'Result': exit_type,
                'Entry_RSI': entry_rsi,
                'Exit_RSI': rsi,
                'Gross_PnL': gross_pnl,
                'Entry_Cost': entry_cost,
                'Exit_Cost': exit_cost,
                'Total_Cost': entry_cost + exit_cost,
                'Net_PnL': net_pnl,
                'Return_%': (net_pnl / (entry_price * POSITION_SIZE)) * 100,
                'Duration_hrs': (current_date - entry_date).total_seconds() / 3600
            })
            
            in_trade = False
    
    # ENTRY
    if not in_trade and in_session:
        # LONG: RSI < 30
        if rsi < RSI_LONG:
            in_trade = True
            trade_type = 'LONG'
            entry_price = price
            entry_rsi = rsi
            entry_date = current_date
            tp = price * (1 + TP_PCT)
            sl = price * (1 - SL_PCT)
        
        # SHORT: RSI > 70
        elif rsi > RSI_SHORT:
            in_trade = True
            trade_type = 'SHORT'
            entry_price = price
            entry_rsi = rsi
            entry_date = current_date
            tp = price * (1 - TP_PCT)
            sl = price * (1 + SL_PCT)

# Convert to DataFrame
trades_df = pd.DataFrame(trades)

if len(trades_df) > 0:
    trades_df['Cumulative_PnL'] = trades_df['Net_PnL'].cumsum()
    
    print("="*180)
    print("DELTA EXCHANGE - ALL 80 TRADES WITH FEES")
    print("="*180 + "\n")
    
    # Display detailed table
    print(f"{'#':<3} {'Date':<19} {'Type':<6} {'Entry':<11} {'Exit':<11} {'Rslt':<3} "
          f"{'Gross P&L':<12} {'Entry Fee':<11} {'Exit Fee':<10} {'Total Cost':<12} {'Net P&L':<12} "
          f"{'Return%':<8} {'Cum P&L':<12}")
    print("-" * 180)
    
    for i, (_, row) in enumerate(trades_df.iterrows(), 1):
        print(f"{i:<3} {row['Date']:<19} {row['Type']:<6} ${row['Entry_Price']:>10.2f} "
              f"${row['Exit_Price']:>10.2f} {row['Result']:<3} ${row['Gross_PnL']:>10.2f} "
              f"${row['Entry_Cost']:>9.2f} ${row['Exit_Cost']:>8.2f} ${row['Total_Cost']:>10.2f} "
              f"${row['Net_PnL']:>10.2f} {row['Return_%']:>6.2f}% ${row['Cumulative_PnL']:>10.2f}")
    
    print("\n" + "="*180)
    print("FEES BREAKDOWN - DELTA EXCHANGE")
    print("="*180)
    
    total_trades = len(trades_df)
    total_entry_cost = trades_df['Entry_Cost'].sum()
    total_exit_cost = trades_df['Exit_Cost'].sum()
    total_cost = trades_df['Total_Cost'].sum()
    total_gross_pnl = trades_df['Gross_PnL'].sum()
    total_net_pnl = trades_df['Net_PnL'].sum()
    
    print(f"\n[COST STRUCTURE]")
    print(f"   Total Trades:             {total_trades}")
    print(f"   Total Entry Costs:        ${total_entry_cost:+.2f} ({total_entry_cost/total_gross_pnl*100:.1f}% of gross profit)")
    print(f"   Total Exit Costs:         ${total_exit_cost:+.2f} ({total_exit_cost/total_gross_pnl*100:.1f}% of gross profit)")
    print(f"   TOTAL FEES & SLIPPAGE:    ${total_cost:+.2f} ({total_cost/total_gross_pnl*100:.1f}% of gross profit)")
    
    print(f"\n[PROFIT & LOSS]")
    print(f"   Gross P&L (before fees):  ${total_gross_pnl:+.2f}")
    print(f"   Less: Total Costs:        ${-total_cost:.2f}")
    print(f"   NET P&L (after fees):     ${total_net_pnl:+.2f}")
    print(f"   Profit Margin:            {(total_net_pnl/total_gross_pnl)*100:.1f}%")
    
    # Statistics
    winning_trades = len(trades_df[trades_df['Net_PnL'] > 0])
    losing_trades = len(trades_df[trades_df['Net_PnL'] < 0])
    win_rate = (winning_trades / total_trades) * 100
    
    total_wins = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].sum()
    total_losses = abs(trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].sum())
    pf = total_wins / total_losses if total_losses > 0 else 0
    
    avg_win = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].mean() if losing_trades > 0 else 0
    
    print(f"\n[PERFORMANCE METRICS]")
    print(f"   Total Trades:             {total_trades}")
    print(f"   Winning Trades:           {winning_trades} ({win_rate:.1f}%)")
    print(f"   Losing Trades:            {losing_trades} ({100-win_rate:.1f}%)")
    print(f"   Average Win:              ${avg_win:+.2f}")
    print(f"   Average Loss:             ${avg_loss:+.2f}")
    print(f"   Profit Factor:            {pf:.2f}x")
    print(f"   Best Trade:               ${trades_df['Net_PnL'].max():+.2f}")
    print(f"   Worst Trade:              ${trades_df['Net_PnL'].min():+.2f}")
    
    # Long vs Short
    longs = trades_df[trades_df['Type'] == 'LONG']
    shorts = trades_df[trades_df['Type'] == 'SHORT']
    
    print(f"\n[LONG TRADES (RSI < 30)]")
    print(f"   Count:                    {len(longs)}")
    if len(longs) > 0:
        long_wr = (len(longs[longs['Net_PnL'] > 0]) / len(longs) * 100)
        print(f"   Win Rate:                 {long_wr:.1f}%")
        print(f"   Total P&L:                ${longs['Net_PnL'].sum():+.2f}")
        print(f"   Total Fees:               ${longs['Total_Cost'].sum():.2f}")
    
    print(f"\n[SHORT TRADES (RSI > 70)]")
    print(f"   Count:                    {len(shorts)}")
    if len(shorts) > 0:
        short_wr = (len(shorts[shorts['Net_PnL'] > 0]) / len(shorts) * 100)
        print(f"   Win Rate:                 {short_wr:.1f}%")
        print(f"   Total P&L:                ${shorts['Net_PnL'].sum():+.2f}")
        print(f"   Total Fees:               ${shorts['Total_Cost'].sum():.2f}")
    
    print("\n" + "="*180)
    print("DELTA EXCHANGE ANALYSIS COMPLETE")
    print("="*180 + "\n")
    
    # Export to CSV
    csv_file = 'delta_exchange_trades.csv'
    trades_df.to_csv(csv_file, index=False)
    print(f"Export file: {csv_file}\n")
    
    # Fee comparison
    print("="*180)
    print("COST COMPARISON")
    print("="*180)
    print(f"Assumed costs (0.20% round-trip):    ${total_trades * (entry_price * POSITION_SIZE * 0.002):.2f}")
    print(f"Actual Delta costs (0.20% + 0.10%): ${total_cost:.2f}")
    print("="*180 + "\n")

else:
    print("❌ No trades executed")
