"""
HYBRID FILTER STRATEGY - 2 YEAR BACKTEST
April 2024 to April 2026
LONG: RSI < 30 AND Price > 200 EMA
SHORT: RSI > 70 only (unfiltered)
"""

import pandas as pd
import numpy as np
import yfinance as yf
import warnings

warnings.filterwarnings('ignore')

print("\n" + "="*200)
print("HYBRID FILTER STRATEGY - 2 YEAR BACKTEST (Apr 2024 - Apr 2026)")
print("="*200)

# Fetch data - 2 YEARS (using daily data)
print("\n[Downloading BTC-USD data for 2 years (daily)...]")
print("[Note: Using daily timeframe. Hourly data only available for last 730 days on yfinance]")
df = yf.download("BTC-USD", start="2024-04-11", end="2026-04-10", interval="1d", progress=False)

# Calculate RSI
delta_rsi = df['Close'].diff()
gain = (delta_rsi.where(delta_rsi > 0, 0)).rolling(14).mean()
loss = (-delta_rsi.where(delta_rsi < 0, 0)).rolling(14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

df = df.dropna()

print(f"[Data loaded: {len(df)} bars from {df.index[0]} to {df.index[-1]}]")
print(f"[Total period: {(df.index[-1] - df.index[0]).days} days (~2 years)]")

# For daily data, no session filter needed - trade every day

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
            })
            
            trade_num += 1
            in_trade = False
    
    # ENTRY LOGIC
    if not in_trade:  # Daily data - trade every day, no session filter
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

print(f"\n[Total trades: {len(df_trades)}]")

if len(df_trades) > 0:
    # Overall stats
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['Net_PnL'] > 0])
    losing_trades = len(df_trades[df_trades['Net_PnL'] < 0])
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
    print("YEARLY BREAKDOWN")
    print("="*200)
    
    df_trades['Year'] = pd.to_datetime(df_trades['Date']).dt.year
    
    yearly_summary = []
    for year in sorted(df_trades['Year'].unique()):
        year_data = df_trades[df_trades['Year'] == year]
        trades_count = len(year_data)
        wins = (year_data['Net_PnL'] > 0).sum()
        wr = wins / trades_count * 100 if trades_count > 0 else 0
        pnl = year_data['Net_PnL'].sum()
        
        yearly_summary.append({
            'Year': year,
            'Trades': trades_count,
            'Wins': wins,
            'Losses': trades_count - wins,
            'Win Rate': f"{wr:.1f}%",
            'Net P&L': f"${pnl:+.2f}",
        })
    
    if yearly_summary:
        df_yearly = pd.DataFrame(yearly_summary)
        print("\n" + df_yearly.to_string(index=False))
    
    print("\n" + "="*200)
    print("MONTHLY BREAKDOWN - ALL MONTHS")
    print("="*200)
    
    df_trades['MonthYear'] = pd.to_datetime(df_trades['Date']).dt.to_period('M')
    
    monthly_summary = []
    for month in sorted(df_trades['MonthYear'].unique()):
        month_data = df_trades[df_trades['MonthYear'] == month]
        trades_count = len(month_data)
        wins = (month_data['Net_PnL'] > 0).sum()
        wr = wins / trades_count * 100 if trades_count > 0 else 0
        pnl = month_data['Net_PnL'].sum()
        
        monthly_summary.append({
            'Month': str(month),
            'Trades': trades_count,
            'Wins': wins,
            'Losses': trades_count - wins,
            'WR%': f"{wr:.1f}%",
            'Net_PnL': f"${pnl:+.2f}",
        })
    
    if monthly_summary:
        df_monthly = pd.DataFrame(monthly_summary)
        print("\n" + df_monthly.to_string(index=False))
    
    print("\n" + "="*200)
    print("OVERALL SUMMARY - 2 YEARS (Apr 2024 - Apr 2026)")
    print("="*200)
    
    print(f"""
Total Period:              {(df.index[-1] - df.index[0]).days} days (~2 years)
Data Points:               {len(df)} hourly bars

TRADE STATISTICS:
  Total Trades:            {total_trades}
  Winning Trades:          {winning_trades}
  Losing Trades:           {losing_trades}
  Win Rate:                {win_rate:.1f}%

PROFITABILITY:
  Gross P&L:               ${total_gross:+.2f}
  Total Fees Paid:         ${total_fees:+.2f}
  NET P&L:                 ${total_net:+.2f}
  
  Profit Factor:           {pf:.2f}x
  Avg Win:                 ${total_wins / winning_trades:+.2f} (per winning trade)
  Avg Loss:                ${-total_loss / losing_trades:+.2f} (per losing trade)
  Risk/Reward Ratio:       1:{total_wins / (total_loss if total_loss > 0 else 1):.2f}
""")
    
    print("="*200)
    print("DIRECTION BREAKDOWN")
    print("="*200)
    
    print(f"\nLONG TRADES (RSI < 30 + Price > 200 EMA):")
    if len(longs) > 0:
        long_wins = len(longs[longs['Net_PnL'] > 0])
        long_wr = long_wins / len(longs) * 100
        long_pnl = longs['Net_PnL'].sum()
        print(f"  Trades:        {len(longs)}")
        print(f"  Wins/Losses:   {long_wins} / {len(longs) - long_wins}")
        print(f"  Win Rate:      {long_wr:.1f}%")
        print(f"  Net P&L:       ${long_pnl:+.2f}")
    else:
        print(f"  No LONG trades")
    
    print(f"\nSHORT TRADES (RSI > 70, unfiltered):")
    if len(shorts) > 0:
        short_wins = len(shorts[shorts['Net_PnL'] > 0])
        short_wr = short_wins / len(shorts) * 100
        short_pnl = shorts['Net_PnL'].sum()
        print(f"  Trades:        {len(shorts)}")
        print(f"  Wins/Losses:   {short_wins} / {len(shorts) - short_wins}")
        print(f"  Win Rate:      {short_wr:.1f}%")
        print(f"  Net P&L:       ${short_pnl:+.2f}")
    else:
        print(f"  No SHORT trades")
    
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
    # VERDICT
    # ============================================================================
    
    print("\n" + "="*200)
    print("2-YEAR PROFITABILITY VERDICT")
    print("="*200)
    
    if total_net > 0:
        print(f"""
YES - PROFITABLE OVER 2 YEARS!

Results Summary:
  Net Profit:        ${total_net:+.2f}
  Total Trades:      {total_trades}
  Win Rate:          {win_rate:.1f}%
  Profit Factor:     {pf:.2f}x
  
Status: VALIDATED - Ready for paper trading
""")
    else:
        print(f"""
NOT PROFITABLE over 2 years.

Results Summary:
  Net Loss:       ${total_net:+.2f}
  Trades:         {total_trades}
  Win Rate:       {win_rate:.1f}%
  Profit Factor:  {pf:.2f}x
""")
    
    print("="*200)
    
    # Export - monthly summary
    df_monthly_export = pd.DataFrame(monthly_summary)
    monthly_path = "rsi_hybrid_2year_monthly_summary.csv"
    df_monthly_export.to_csv(monthly_path, index=False)
    print(f"\nMonthly summary exported to: {monthly_path}")
    
    # Export - yearly summary
    df_yearly_export = pd.DataFrame(yearly_summary)
    yearly_path = "rsi_hybrid_2year_yearly_summary.csv"
    df_yearly_export.to_csv(yearly_path, index=False)
    print(f"Yearly summary exported to: {yearly_path}")
    
    # Export - all trades
    export_df = df_trades[['Trade_Num', 'Date', 'Type', 'Entry_Price', 'Exit_Price', 
                            'Result', 'Net_PnL', 'Cumulative_PnL']].copy()
    export_df.columns = ['Trade', 'Date', 'Direction', 'Entry_Price', 'Exit_Price', 
                         'Result', 'Net_PnL', 'Cumulative_PnL']
    
    trades_path = "rsi_hybrid_2year_all_trades.csv"
    export_df.to_csv(trades_path, index=False)
    print(f"All trades exported to: {trades_path}\n")
    
else:
    print("\n*** No trades were taken during the 2 year period ***\n")

print("="*200 + "\n")
