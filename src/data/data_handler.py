"""Data Handler - Load historical OHLCV data"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


class DataHandler:
    """Handles historical data loading from yfinance"""
    
    def __init__(self, cache_dir: str = './data'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_historical_data(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = '15m'
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data
        
        Args:
            symbol: Ticker symbol (e.g., 'BTC-USD', 'BTCUSDT')
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Downloading {symbol} data from {start} to {end} ({interval})")
        
        try:
            # Download from yfinance
            df = yf.download(
                symbol,
                start=start,
                end=end,
                interval=interval,
                progress=False
            )
            
            # Standardize column names
            df.columns = df.columns.str.lower()
            
            # Ensure index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Sort by date
            df = df.sort_index()
            
            logger.info(f"Downloaded {len(df)} bars of data")
            return df
        
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            raise
