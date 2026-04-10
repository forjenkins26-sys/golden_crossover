"""
BTC 50/200 SMA Golden Cross Strategy
Based on exact spec provided - daily data 2021-2025
"""

import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import requests
from io import StringIO
from datetime import datetime

# ============================================================================
# 1. DATA LOADING
# ============================================================================

def load_btc_data():
    """
    Load BTC BTCUSDT daily data from CryptoDataDownload
    Returns DataFrame sliced to 2021-01-01 to 2025-12-31
    """
    print("Downloading BTC BTCUSDT daily data from CryptoDataDownload...")
    
    try:
        url = "https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_d.csv"
        response = requests.get(url)
        
        # Skip first row (metadata) and read CSV
        lines = response.text.split('\n')
        csv_data = '\n'.join(lines[1:])  # Skip first line
        
        df = pd.read_csv(StringIO(csv_data))
        
        # Parse date
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        
        # Standard column names
        df.columns = df.columns.str.lower()
        
        # Extract OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        
        # Slice to 2021-01-01 to 2025-12-31
        start_date = '2021-01-01'
        end_date = '2025-12-31'
        df = df[start_date:end_date]
        
        print(f"✓ Loaded {len(df)} days of BTC data ({df.index[0].date()} to {df.index[-1].date()})")
        print(f"  First close: ${df['close'].iloc[0]:,.2f}")
        print(f"  Last close:  ${df['close'].iloc[-1]:,.2f}")
        
        return df
    
    except Exception as e:
        print(f"✗ Error downloading data: {e}")
        print("Using fallback: yfinance...")
        return load_btc_data_yfinance()


def load_btc_data_yfinance():
    """Fallback to yfinance if CryptoDataDownload fails"""
    import yfinance as yf
    
    print("Downloading BTC data from yfinance (fallback)...")
    df = yf.download('BTC-USD', start='2021-01-01', end='2025-12-31', interval='1d', progress=False)
    
    # Handle MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Standardize column names (Backtesting.py requires capital letters)
    df = df.rename(columns={
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume'
    })
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    print(f"✓ Loaded {len(df)} days of BTC data ({df.index[0].date()} to {df.index[-1].date()})")
    print(f"  First close: ${df['Close'].iloc[0]:,.2f}")
    print(f"  Last close:  ${df['Close'].iloc[-1]:,.2f}")
    
    return df


# ============================================================================
# 2. STRATEGY DEFINITION
# ============================================================================

class BTC50_200_SMA(Strategy):
    """
    BTC 50/200 SMA Golden Cross Strategy
    
    Rules:
    - Entry: SMA50 crosses above SMA200  (Golden Cross = BUY)
    - Exit: SMA50 crosses below SMA200   (Death Cross = CLOSE)
    - Stop Loss: 15% below entry
    - Position: Long-only, full size
    """
    
    # Parameters
    fast_n = 50      # Fast SMA period
    slow_n = 200     # Slow SMA period
    stop_loss_pct = 0.15  # Stop loss 15% below entry

    def init(self):
        """Initialize indicators"""
        close = self.data.Close
        
        # Calculate SMAs using pandas rolling
        self.sma_fast = self.I(lambda x: pd.Series(x).rolling(self.fast_n).mean(), close)
        self.sma_slow = self.I(lambda x: pd.Series(x).rolling(self.slow_n).mean(), close)

    def next(self):
        """Execute strategy logic on each bar"""
        
        # Don't trade until we have enough data for the slowest MA
        if len(self.data) < self.slow_n:
            return
        
        # No position case: look for entry (Golden Cross)
        if not self.position:
            if crossover(self.sma_fast, self.sma_slow):
                # Enter long with stop loss 15% below entry
                sl_price = self.data.Close[-1] * (1 - self.stop_loss_pct)
                self.buy(sl=sl_price)
        
        # Position open case: look for exit (Death Cross)
        else:
            if crossover(self.sma_slow, self.sma_fast):
                self.position.close()


# ============================================================================
# 3. BACKTEST EXECUTION
# ============================================================================

def run_backtest(df):
    """Run the backtest and return results"""
    
    print("\n" + "=" * 80)
    print("BACKTEST CONFIGURATION")
    print("=" * 80)
    print(f"Initial Cash:       $100,000")
    print(f"Commission:         0.1% (0.001)")
    print(f"Strategy:           BTC 50/200 SMA Golden Cross (Long-only)")
    print(f"Data Range:         {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Total Bars:         {len(df)} days")
    print()
    
    # Create and configure backtest
    bt = Backtest(
        df,
        BTC50_200_SMA,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,  # No overlapping positions
    )
    
    # Run backtest
    print("Running backtest...")
    stats = bt.run()
    
    return stats, bt


def print_stats(stats):
    """Pretty print backtest statistics"""
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: BTC 50/200 SMA Golden Cross (2021-2025)")
    print("=" * 80)
    
    print("\nCAPITAL & RETURNS:")
    print(f"  Initial Cash:               ${100_000:>12,.2f}")
    print(f"  Final Value:                ${stats['Equity Final [$]']:>12,.2f}")
    print(f"  Total Return:               {stats['Return [%]']:>12.2f}%")
    
    print("\nTRADE STATISTICS:")
    print(f"  Total Trades:               {int(stats['# Trades']):>12}")
    if stats.get('# Trades', 0) > 0:
        print(f"  Win Rate:                   {stats['Win Rate [%]']:>12.2f}%")
        print(f"  Best Trade:                 {stats['Best Trade [%]']:>12.2f}%")
        print(f"  Worst Trade:                {stats['Worst Trade [%]']:>12.2f}%")
        print(f"  Avg Trade:                  {(stats['Return [%]'] / stats['# Trades']):>12.2f}%")
        # Only print Avg Trade Duration if it's available
        if 'Avg. Trade Length' in stats.index:
            print(f"  Avg Trade Duration:         {str(stats['Avg. Trade Length']):>12}")
    
    print("\nRISK METRICS:")
    print(f"  Max Drawdown:               {stats['Max. Drawdown [%]']:>12.2f}%")
    
    if 'Sharpe Ratio' in stats.index:
        print(f"  Sharpe Ratio:               {stats['Sharpe Ratio']:>12.2f}")
    
    print("\n" + "=" * 80 + "\n")


# ============================================================================
# 4. SAVE RESULTS
# ============================================================================

def save_results(bt, filename='btc_50_200_backtest.html'):
    """Save equity curve plot to HTML"""
    print(f"Saving equity curve plot to {filename}...")
    try:
        bt.plot(filename=filename, title='BTC 50/200 SMA Golden Cross (2021-2025)')
        print(f"✓ Saved: {filename}")
    except Exception as e:
        print(f"Note: Could not save plot ({e})")


# ============================================================================
# 5. MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BTC 50/200 SMA GOLDEN CROSS BACKTEST (2021-2025)")
    print("=" * 80 + "\n")
    
    # Load data
    df = load_btc_data()
    
    # Run backtest
    stats, bt = run_backtest(df)
    
    # Print results
    print_stats(stats)
    
    # Save plot
    save_results(bt)
    
    # Print raw stats for reference
    print("\nDETAILED STATISTICS:")
    print(stats)
