"""
BTC 20/50 SMA Golden Cross Strategy - Test A
Shorter MA period for more frequent signals vs 50/200
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
    """Load BTC BTCUSDT daily data from CryptoDataDownload"""
    print("Downloading BTC BTCUSDT daily data from CryptoDataDownload...")
    
    try:
        url = "https://www.cryptodatadownload.com/cdd/Binance_BTCUSDT_d.csv"
        response = requests.get(url)
        lines = response.text.split('\n')
        csv_data = '\n'.join(lines[1:])
        
        df = pd.read_csv(StringIO(csv_data))
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        df.sort_index(inplace=True)
        # Rename to proper capitalization for backtesting.py
        df = df.rename(columns={
            col: col.capitalize() if col.lower() in ['open', 'high', 'low', 'close', 'volume'] else col
            for col in df.columns
        })
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        start_date = '2021-01-01'
        end_date = '2025-12-31'
        df = df[start_date:end_date]
        
        print(f"✓ Loaded {len(df)} days of BTC data ({df.index[0].date()} to {df.index[-1].date()})")
        print(f"  First close: ${df['Close'].iloc[0]:,.2f}")
        print(f"  Last close:  ${df['Close'].iloc[-1]:,.2f}")
        
        return df
    
    except Exception as e:
        print(f"✗ Error downloading data: {e}")
        print("Using fallback: yfinance...")
        return load_btc_data_yfinance()


def load_btc_data_yfinance():
    """Fallback to yfinance"""
    import yfinance as yf
    
    print("Downloading BTC data from yfinance (fallback)...")
    df = yf.download('BTC-USD', start='2021-01-01', end='2025-12-31', interval='1d', progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Ensure proper capitalization for backtesting.py
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    
    print(f"✓ Loaded {len(df)} days of BTC data ({df.index[0].date()} to {df.index[-1].date()})")
    print(f"  First close: ${df['Close'].iloc[0]:,.2f}")
    print(f"  Last close:  ${df['Close'].iloc[-1]:,.2f}")
    
    return df


# ============================================================================
# 2. STRATEGY
# ============================================================================

class BTC20_50_SMA(Strategy):
    """20/50 SMA Golden Cross - Long only"""
    
    def init(self):
        # Calculate SMAs
        self.ma20 = self.I(lambda x: pd.Series(x).rolling(20).mean(), self.data.Close)
        self.ma50 = self.I(lambda x: pd.Series(x).rolling(50).mean(), self.data.Close)
    
    def next(self):
        # Golden Cross: 20 > 50
        if crossover(self.ma20, self.ma50):
            if not self.position:
                self.buy()
        
        # Death Cross: 20 < 50
        elif crossover(self.ma50, self.ma20):
            if self.position:
                self.position.close()


# ============================================================================
# 3. BACKTEST EXECUTION
# ============================================================================

def run_backtest(df):
    """Run the backtest"""
    
    print("\n" + "=" * 80)
    print("BACKTEST CONFIGURATION - TEST A: BTC 20/50 SMA")
    print("=" * 80)
    print(f"Initial Cash:       $100,000")
    print(f"Commission:         0.1% (0.001)")
    print(f"Strategy:           BTC 20/50 SMA Golden Cross (Long-only)")
    print(f"Data Range:         {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Total Bars:         {len(df)} days")
    print()
    
    bt = Backtest(
        df,
        BTC20_50_SMA,
        cash=100_000,
        commission=0.001,
        exclusive_orders=True,
    )
    
    print("Running backtest...")
    stats = bt.run()
    
    return stats, bt


def print_stats(stats, df):
    """Print backtest statistics"""
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS: BTC 20/50 SMA Golden Cross (2021-2025)")
    print("=" * 80)
    
    print("\nCAPITAL & RETURNS:")
    print(f"  Initial Cash:               ${100_000:>12,.2f}")
    print(f"  Final Value:                ${stats['Equity Final [$]']:>12,.2f}")
    print(f"  Total Return:               {stats['Return [%]']:>12.2f}%")
    if 'CAGR [%]' in stats.index:
        print(f"  CAGR:                       {stats['CAGR [%]']:>12.2f}%")
    
    print("\nTRADE STATISTICS:")
    print(f"  Total Trades:               {int(stats['# Trades']):>12}")
    if stats.get('# Trades', 0) > 0:
        print(f"  Win Rate:                   {stats['Win Rate [%]']:>12.2f}%")
        print(f"  Best Trade:                 {stats['Best Trade [%]']:>12.2f}%")
        print(f"  Worst Trade:                {stats['Worst Trade [%]']:>12.2f}%")
        if 'Avg. Trade [%]' in stats.index:
            print(f"  Avg Trade:                  {stats['Avg. Trade [%]']:>12.2f}%")
        if 'Profit Factor' in stats.index:
            print(f"  Profit Factor:              {stats['Profit Factor']:>12.2f}x")
    
    print("\nRISK METRICS:")
    print(f"  Max Drawdown:               {stats['Max. Drawdown [%]']:>12.2f}%")
    if 'Sharpe Ratio' in stats.index:
        print(f"  Sharpe Ratio:               {stats['Sharpe Ratio']:>12.2f}")
    
    print("\nCOMPARISON:")
    bh_return = ((df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1) * 100
    print(f"  Buy & Hold Return:          {bh_return:>12.2f}%")
    print(f"  Strategy Return:            {stats['Return [%]']:>12.2f}%")
    print(f"  Underperformance:           {(stats['Return [%]'] - bh_return):>12.2f}pp")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("BTC 20/50 SMA GOLDEN CROSS BACKTEST (2021-2025)")
    print("=" * 80 + "\n")
    
    # Load data
    df = load_btc_data()
    
    # Run backtest
    stats, bt = run_backtest(df)
    
    # Print results
    print_stats(stats, df)
    
    # Full stats
    print("DETAILED STATISTICS:")
    print(stats)
