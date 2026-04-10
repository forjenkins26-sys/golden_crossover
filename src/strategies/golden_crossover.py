"""
Golden Crossover Strategy
- Entry on EMA12 crossing EMA26
- Simple, systematic, and robust
"""

from typing import Dict
import pandas as pd
import numpy as np
from src.strategies.base_strategy import BaseStrategy, SignalType
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


class GoldenCrossoverStrategy(BaseStrategy):
    """
    Golden Crossover Strategy (EMA-based):
    
    Entry Rules:
    - BUY: EMA12 crosses above EMA26 (Golden Cross)
    - SELL: EMA12 crosses below EMA26 (Death Cross)
    
    Exit Rules:
    - Opposite cross OR Stop Loss / Take Profit
    
    Parameters:
    - fast_ema: 12 (fast moving average)
    - slow_ema: 26 (slow moving average)
    - atr_period: 14 (for volatility-based stops)
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '15m',
        fast_ema: int = 12,
        slow_ema: int = 26,
        atr_period: int = 14,
        atr_mult_sl: float = 2.0,
        risk_reward_ratio: float = 2.0,
    ):
        super().__init__(symbol, timeframe, name='GoldenCrossover')
        
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.atr_period = atr_period
        self.atr_mult_sl = atr_mult_sl
        self.risk_reward_ratio = risk_reward_ratio
        
        # Position tracking
        self.trailing_stop = None
        self.tp1_hit = False
    
    @staticmethod
    def _ema(series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate signals based on EMA crossovers
        
        Args:
            df: OHLCV dataframe
        
        Returns:
            DataFrame with 'signal' column
        """
        df = df.copy()
        df['signal'] = 0
        
        # Calculate EMAs
        df['ema_fast'] = self._ema(df['close'], self.fast_ema)
        df['ema_slow'] = self._ema(df['close'], self.slow_ema)
        
        # Calculate ATR for stop loss
        df['atr'] = self._atr(df, self.atr_period)
        
        # Detect crossovers
        df['fast_above_slow'] = df['ema_fast'] > df['ema_slow']
        df['prev_fast_above_slow'] = df['fast_above_slow'].shift(1)
        
        # Golden Cross (BUY): EMA12 crosses above EMA26
        golden_cross = (df['fast_above_slow']) & (~df['prev_fast_above_slow'].fillna(False))
        
        # Death Cross (SELL): EMA12 crosses below EMA26
        death_cross = (~df['fast_above_slow']) & (df['prev_fast_above_slow'].fillna(False))
        
        # Assign signals (only after enough bars for EMA calculation)
        calc_valid = df['ema_fast'].notna() & df['ema_slow'].notna()
        
        df.loc[golden_cross & calc_valid, 'signal'] = 1  # BUY
        df.loc[death_cross & calc_valid, 'signal'] = -1  # SELL
        
        # Precompute SL/TP for risk management
        df['sl_dist'] = 0.0
        df['tp2_price'] = 0.0
        
        # For LONG entries: SL below current price by ATR*multiplier
        long_mask = df['signal'] == 1
        df.loc[long_mask, 'sl_dist'] = df.loc[long_mask, 'atr'] * self.atr_mult_sl
        df.loc[long_mask, 'tp2_price'] = df.loc[long_mask, 'close'] + (self.risk_reward_ratio * df.loc[long_mask, 'sl_dist'])
        
        # For SHORT entries: SL above current price by ATR*multiplier
        short_mask = df['signal'] == -1
        df.loc[short_mask, 'sl_dist'] = df.loc[short_mask, 'atr'] * self.atr_mult_sl
        df.loc[short_mask, 'tp2_price'] = df.loc[short_mask, 'close'] - (self.risk_reward_ratio * df.loc[short_mask, 'sl_dist'])
        
        return df
    
    def get_entry_rules(self) -> Dict:
        """Define entry parameters"""
        return {
            'condition': 'EMA12 crosses EMA26',
            'quantity': 1,
            'order_type': 'market'
        }
    
    def get_exit_rules(self) -> Dict:
        """Define exit parameters"""
        return {
            'stop_loss_pct': None,  # ATR-based SL instead
            'take_profit_pct': None,  # RR-ratio based TP instead
            'atr_mult_sl': self.atr_mult_sl,
            'risk_reward_ratio': self.risk_reward_ratio,
        }
    
    def evaluate_position(self, bar: pd.Series, current_price: float, bar_idx: int) -> Dict:
        """
        Evaluate exit conditions (simple cross-close logic)
        """
        if self.current_position is None:
            return {'exit': False}
        
        # Exit on opposite crossover (simple implementation)
        # This will be overridden by the backtest engine's main logic
        return {'exit': False}
