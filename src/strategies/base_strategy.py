"""Base Strategy Class - Abstract framework for all strategies"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional
import pandas as pd
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


class SignalType(Enum):
    """Trading signal types"""
    BUY = 1
    SELL = -1
    HOLD = 0


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Every strategy must implement:
    1. generate_signals() - Entry signal generation
    2. get_entry_rules() - Entry parameters
    3. get_exit_rules() - Exit parameters
    """
    
    def __init__(self, symbol: str, timeframe: str = '15m', name: Optional[str] = None):
        """Initialize strategy"""
        self.symbol = symbol
        self.timeframe = timeframe
        self.name = name or self.__class__.__name__
        
        # Position tracking
        self.current_position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
        
        logger.info(f"Strategy {self.name} initialized for {symbol} ({timeframe})")
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals
        
        Args:
            df: OHLCV dataframe
        
        Returns:
            DataFrame with 'signal' column (1=BUY, -1=SELL, 0=HOLD)
        """
        pass
    
    def get_entry_rules(self) -> Dict:
        """Define entry parameters"""
        return {
            'condition': 'Strategy signal',
            'quantity': 1,
            'order_type': 'market'
        }
    
    def get_exit_rules(self) -> Dict:
        """Define exit parameters"""
        return {
            'stop_loss_pct': 2.0,
            'take_profit_pct': 4.0,
            'trailing_stop': None,
        }
    
    def on_trade_open(self, entry_price: float, signal: SignalType) -> None:
        """Initialize position state on trade entry"""
        self.current_position = signal
        self.entry_price = entry_price
        logger.info(f"Position opened: {signal.name} @ ${entry_price:.2f}")
    
    def on_trade_close(self, exit_price: float, reason: str = 'Unknown') -> None:
        """Reset position state on trade exit"""
        pnl = exit_price - self.entry_price if self.entry_price else 0
        logger.info(f"Position closed: {reason} @ ${exit_price:.2f} | PnL: ${pnl:.2f}")
        
        self.current_position = None
        self.entry_price = None
        self.stop_loss = None
        self.take_profit = None
    
    def evaluate_position(self, bar: pd.Series, current_price: float, bar_idx: int) -> Dict:
        """Check if position should exit (override in subclass)"""
        return {'exit': False}
