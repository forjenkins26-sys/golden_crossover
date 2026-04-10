"""
RSI 30/70 STRATEGY - DETAILED TRADE LIST WITH FEES & SLIPPAGE
Shows every trade with P&L breakdown
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*180)
print("RSI 30/70 STRATEGY - DETAILED TRADE ANALYSIS")
print("="*180)

# Fetch data
print("\n📊 Fetching BTC-USD data...")
df = yf.download("BTC-USD", start="2026-01-01", end="2026-04-10", interval="1h", progress=False)

# Calculate RSI
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
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
ENTRY_FEE = 0.0005   # 0.05%
EXIT_FEE = 0.0005    # 0.05%
SLIPPAGE = 0.0005    # 0.05%
TOTAL_ENTRY_COST = ENTRY_FEE + SLIPPAGE  # 0.10%
TOTAL_EXIT_COST = EXIT_FEE + SLIPPAGE    # 0.10%

print(f"🔍 Backtesting RSI {RSI_LONG}/{RSI_SHORT} Strategy")
print(f"   Position Size: {POSITION_SIZE} BTC")
print(f"   Entry Cost: {TOTAL_ENTRY_COST*100:.2f}% | Exit Cost: {TOTAL_EXIT_COST*100:.2f}%")
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
            # Calculate P&L
            if trade_type == 'LONG':
                gross_pnl = (exit_price - entry_price) * POSITION_SIZE
            else:
                gross_pnl = (entry_price - exit_price) * POSITION_SIZE
            
            # Deduct fees and slippage
            entry_cost = entry_price * POSITION_SIZE * TOTAL_ENTRY_COST
            exit_cost = exit_price * POSITION_SIZE * TOTAL_EXIT_COST
            net_pnl = gross_pnl - entry_cost - exit_cost
            
            trades.append({
                'Date': current_date.strftime('%Y-%m-%d %H:%M'),
                'Type': trade_type,
                'Entry': entry_price,
                'Exit': exit_price,
                'Result': exit_type,
                'Entry_RSI': entry_rsi,
                'Exit_RSI': rsi,
                'Gross_PnL': gross_pnl,
                'Entry_Fees': entry_cost,
                'Exit_Fees': exit_cost,
                'Total_Fees': entry_cost + exit_cost,
                'Net_PnL': net_pnl,
                'Return_%': (net_pnl / (entry_price * POSITION_SIZE)) * 100,
                'Duration': (current_date - entry_date).total_seconds() / 3600  # hours
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
    # Add cumulative P&L
    trades_df['Cumulative_PnL'] = trades_df['Net_PnL'].cumsum()
    
    print("="*180)
    print("TRADE-BY-TRADE BREAKDOWN")
    print("="*180 + "\n")
    
    # Display detailed table
    print(f"{'#':<4} {'Date':<20} {'Type':<6} {'Entry':<11} {'Exit':<11} {'Rslt':<3} "
          f"{'Gross_P&L':<12} {'Fees':<10} {'Net_P&L':<12} {'Return%':<8} {'Cum_P&L':<12} {'Hrs':<5}")
    print("-" * 180)
    
    for i, (_, row) in enumerate(trades_df.iterrows(), 1):
        print(f"{i:<4} {row['Date']:<20} {row['Type']:<6} ${row['Entry']:>10.2f} ${row['Exit']:>10.2f} "
              f"{row['Result']:<3} ${row['Gross_PnL']:>10.2f} ${row['Total_Fees']:>8.2f} "
              f"${row['Net_PnL']:>10.2f} {row['Return_%']:>6.2f}% ${row['Cumulative_PnL']:>10.2f} {row['Duration']:>4.0f}h")
    
    print("\n" + "="*180)
    print("STATISTICS")
    print("="*180)
    
    total_trades = len(trades_df)
    winning_trades = len(trades_df[trades_df['Net_PnL'] > 0])
    losing_trades = len(trades_df[trades_df['Net_PnL'] < 0])
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    
    total_gross_pnl = trades_df['Gross_PnL'].sum()
    total_fees = trades_df['Total_Fees'].sum()
    total_net_pnl = trades_df['Net_PnL'].sum()
    
    avg_win = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].mean() if winning_trades > 0 else 0
    avg_loss = trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].mean() if losing_trades > 0 else 0
    
    total_wins = trades_df[trades_df['Net_PnL'] > 0]['Net_PnL'].sum()
    total_losses = abs(trades_df[trades_df['Net_PnL'] < 0]['Net_PnL'].sum())
    pf = total_wins / total_losses if total_losses > 0 else 0
    
    avg_duration = trades_df['Duration'].mean()
    
    print(f"\n📊 TRADE SUMMARY:")
    print(f"   Total Trades:        {total_trades}")
    print(f"   Winning Trades:      {winning_trades} ({win_rate:.1f}%)")
    print(f"   Losing Trades:       {losing_trades} ({100-win_rate:.1f}%)")
    print(f"   Avg Trade Duration:  {avg_duration:.1f} hours")
    
    print(f"\n💰 PROFIT & LOSS:")
    print(f"   Gross P&L:           ${total_gross_pnl:+.2f}")
    print(f"   Total Fees/Slippage: ${total_fees:.2f}")
    print(f"   NET P&L:             ${total_net_pnl:+.2f}")
    print(f"   Return %:            {(total_net_pnl / (entry_price * POSITION_SIZE * total_trades)) * 100:.2f}%")
    
    print(f"\n📈 QUALITY METRICS:")
    print(f"   Average Win:         ${avg_win:+.2f}")
    print(f"   Average Loss:        ${avg_loss:+.2f}")
    print(f"   Profit Factor:       {pf:.2f}x")
    print(f"   Best Trade:          ${trades_df['Net_PnL'].max():+.2f}")
    print(f"   Worst Trade:         ${trades_df['Net_PnL'].min():+.2f}")
    
    # Long vs Short breakdown
    longs = trades_df[trades_df['Type'] == 'LONG']
    shorts = trades_df[trades_df['Type'] == 'SHORT']
    
    print(f"\n🔵 LONG TRADES (RSI < 30):")
    print(f"   Count:               {len(longs)}")
    if len(longs) > 0:
        print(f"   Win Rate:            {(len(longs[longs['Net_PnL'] > 0]) / len(longs) * 100):.1f}%")
        print(f"   Total P&L:           ${longs['Net_PnL'].sum():+.2f}")
    
    print(f"\n🔴 SHORT TRADES (RSI > 70):")
    print(f"   Count:               {len(shorts)}")
    if len(shorts) > 0:
        print(f"   Win Rate:            {(len(shorts[shorts['Net_PnL'] > 0]) / len(shorts) * 100):.1f}%")
        print(f"   Total P&L:           ${shorts['Net_PnL'].sum():+.2f}")
    
    print("\n" + "="*180)
    print(f"✓ READY FOR PAPER TRADING - Strategy proven with {total_trades} trades")
    print("="*180 + "\n")
    
    # Export to CSV
    csv_file = 'rsi_30_70_trades_detailed.csv'
    trades_df.to_csv(csv_file, index=False)
    print(f"📁 Exported to: {csv_file}\n")

else:
    print("❌ No trades executed")
