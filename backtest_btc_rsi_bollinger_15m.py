"""
BTC 15-Min RSI + Bollinger Band Mean-Reversion Backtest
Target: 15-20 trades/month, 1-2% per trade, consistent profits
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. DATA LOADING (15-MIN BARS)
# ============================================================================

def load_btc_15m(days_back=60):
    """Load BTC 15-min bars from yfinance"""
    print(f"Downloading BTC 15-min data (last {days_back} days)...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    try:
        df = yf.download(
            'BTC-USD', 
            start=start_date.date(), 
            end=end_date.date(), 
            interval='15m', 
            progress=False
        )
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Ensure proper capitalization
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        print(f"✓ Loaded {len(df)} 15-min bars ({df.index[0]} to {df.index[-1]})")
        print(f"  Data spans: {len(df) / 96:.1f} days ({len(df) / (96 * 5):.1f} weeks)")
        print(f"  First close: ${df['Close'].iloc[0]:,.2f}")
        print(f"  Last close:  ${df['Close'].iloc[-1]:,.2f}")
        
        return df
    
    except Exception as e:
        print(f"✗ Error downloading data: {e}")
        return None


# ============================================================================
# 2. INDICATORS
# ============================================================================

def calculate_rsi(series, period=14):
    """Calculate RSI(14)"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_bollinger_bands(series, period=20, num_std=2):
    """Calculate Bollinger Bands"""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


# ============================================================================
# 3. STRATEGY
# ============================================================================

class RSIBollingerMeanReversion(Strategy):
    """
    RSI + Bollinger Band Mean-Reversion
    
    Entry:
      - RSI(14) < 30 (oversold)
      - Close < Lower Bollinger Band (20, 2)
    
    Exit:
      - TP: +2.5% (quick scalp)
      - SL: -1.5% (tight risk)
      - Max hold: 24 bars (6 hours on 15-min)
    """
    
    # Parameters
    rsi_period = 14
    rsi_oversold = 30
    bb_period = 20
    bb_std = 2.0
    tp_pct = 0.025  # +2.5%
    sl_pct = 0.015  # -1.5%
    max_hold_bars = 24  # 6 hours on 15-min
    
    def init(self):
        # Precompute indicators
        close = pd.Series(self.data.Close)
        
        # RSI(14)
        self.rsi = self.I(calculate_rsi, close, self.rsi_period)
        
        # Bollinger Bands (20, 2)
        upper, sma, lower = calculate_bollinger_bands(close, self.bb_period, self.bb_std)
        self.bb_upper = self.I(lambda x: upper, close)
        self.bb_lower = self.I(lambda x: lower, close)
        self.bb_sma = self.I(lambda x: sma, close)
        
        # Track entry price and bars held
        self.entry_price = None
        self.bars_since_entry = 0
    
    def next(self):
        # Update bars held
        if self.position:
            self.bars_since_entry += 1
        
        # Exit conditions
        if self.position:
            current_price = self.data.Close[-1]
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            
            # TP: +2.5%
            if pnl_pct >= self.tp_pct:
                self.position.close()
                return
            
            # SL: -1.5%
            if pnl_pct <= -self.sl_pct:
                self.position.close()
                return
            
            # Max hold: 24 bars (6 hours)
            if self.bars_since_entry >= self.max_hold_bars:
                self.position.close()
                return
        
        # Entry condition: RSI < 30 AND Price < Lower BB
        if not self.position:
            if self.rsi[-1] < self.rsi_oversold and self.data.Close[-1] < self.bb_lower[-1]:
                # Buy 1 full Bitcoin (backtesting.py will handle fractional shares)
                self.buy()
                self.entry_price = self.data.Close[-1]
                self.bars_since_entry = 0


# ============================================================================
# 4. BACKTEST EXECUTION
# ============================================================================

def run_backtest(df):
    """Run the backtest"""
    
    print("\n" + "=" * 80)
    print("BACKTEST CONFIGURATION - BTC 15-Min RSI + Bollinger Mean-Reversion")
    print("=" * 80)
    print(f"Initial Cash:                $100,000")
    print(f"Commission:                  0.1% (0.001)")
    print(f"Timeframe:                   15-min")
    print(f"Strategy:                    RSI(14) < 30 + Lower Bollinger Band")
    print(f"TP/SL:                       +2.5% / -1.5%")
    print(f"Max Hold:                    24 bars (6 hours)")
    print(f"Data Range:                  {df.index[0]} to {df.index[-1]}")
    print(f"Total Bars:                  {len(df)}")
    print()
    
    bt = Backtest(
        df,
        RSIBollingerMeanReversion,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
    )
    
    print("Running backtest...")
    stats = bt.run()
    
    return stats, bt, df


def print_stats(stats, df):
    """Print backtest statistics"""
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: BTC 15-Min RSI + Bollinger Mean-Reversion")
    print("=" * 80)
    
    # Calculate metrics
    num_bars = len(df)
    num_days = num_bars / 96  # 96 bars per day (24h * 4 = 96 15-min bars)
    num_weeks = num_days / 7
    num_months = num_days / 30
    
    num_trades = int(stats['# Trades'])
    trades_per_day = num_trades / num_days if num_days > 0 else 0
    trades_per_week = num_trades / num_weeks if num_weeks > 0 else 0
    trades_per_month = num_trades / num_months if num_months > 0 else 0
    
    print("\nCAPITAL & RETURNS:")
    print(f"  Initial Cash:               ${100_000:>12,.2f}")
    print(f"  Final Value:                ${stats['Equity Final [$]']:>12,.2f}")
    print(f"  Total Return:               {stats['Return [%]']:>12.2f}%")
    if 'CAGR [%]' in stats.index:
        print(f"  Return/Month (annualized):  {stats['Return [%]'] / num_months:>12.2f}%")
    
    print("\nTRADE STATISTICS:")
    print(f"  Total Trades:               {num_trades:>12}")
    print(f"  Trades/Day:                 {trades_per_day:>12.2f}")
    print(f"  Trades/Week:                {trades_per_week:>12.2f}")
    print(f"  Trades/Month (extrapolated):{trades_per_month:>12.2f}")
    
    if num_trades > 0:
        print(f"  Win Rate:                   {stats['Win Rate [%]']:>12.2f}%")
        print(f"  Best Trade:                 {stats['Best Trade [%]']:>12.2f}%")
        print(f"  Worst Trade:                {stats['Worst Trade [%]']:>12.2f}%")
        if 'Avg. Trade [%]' in stats.index:
            print(f"  Avg Trade:                  {stats['Avg. Trade [%]']:>12.2f}%")
        if 'Profit Factor' in stats.index:
            print(f"  Profit Factor:              {stats['Profit Factor']:>12.2f}x")
        if 'Avg. Trade Duration' in stats.index:
            print(f"  Avg Hold Time:              {str(stats['Avg. Trade Duration']):>12}")
    
    print("\nRISK METRICS:")
    print(f"  Max Drawdown:               {stats['Max. Drawdown [%]']:>12.2f}%")
    if 'Sharpe Ratio' in stats.index:
        print(f"  Sharpe Ratio:               {stats['Sharpe Ratio']:>12.2f}")
    
    print("\nEXPECTED MONTHLY PROFIT (at different position sizes):")
    if num_trades > 0 and num_months > 0:
        avg_profit_per_trade = stats['Return [%]'] / num_trades
        monthly_return_pct = (avg_profit_per_trade * trades_per_month)
        
        capital_needed_1k_monthly = 100_000
        profit_per_month_100k = capital_needed_1k_monthly * (stats['Return [%]'] / 100) / num_months
        position_size_1k = 1_000 / (avg_profit_per_trade * 0.01)
        
        print(f"  Avg Profit/Trade:           {avg_profit_per_trade:>12.3f}%")
        print(f"  Expected Monthly % Return:  {monthly_return_pct:>12.2f}%")
        print(f"  With $100k capital:         ${profit_per_month_100k:>12,.2f}/month")
        print(f"  Position size for $1k/mo:   ${position_size_1k:>12,.2f}")
    
    print("\n" + "=" * 80 + "\n")


# ============================================================================
# 5. MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BTC 15-MIN RSI + BOLLINGER BAND MEAN-REVERSION BACKTEST")
    print("=" * 80 + "\n")
    
    # Load data (60 days = ~240 trading hours = ~960 15-min bars)
    df = load_btc_15m(days_back=60)
    
    if df is not None and len(df) > 100:
        # Run backtest
        stats, bt, df = run_backtest(df)
        
        # Print results
        print_stats(stats, df)
        
        # Full stats
        print("DETAILED STATISTICS:")
        print(stats)
    else:
        print("✗ Failed to load data or insufficient bars")
