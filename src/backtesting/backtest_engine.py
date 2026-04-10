"""Backtesting Engine - Core backtesting logic"""

import pandas as pd
from typing import Optional
from dataclasses import dataclass
from src.strategies.base_strategy import BaseStrategy, SignalType
from src.backtesting.metrics_calculator import MetricsCalculator
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_bar: int
    entry_price: float
    exit_bar: int
    exit_price: float
    signal_type: SignalType
    pnl: float
    return_pct: float
    reason: str = ''


class BacktestEngine:
    """Core backtesting engine"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.trades = []
        self.cash = initial_capital
        self.position = None
        self.equity_curve = []
    
    def run(self, df: pd.DataFrame) -> dict:
        """
        Run backtest on historical data
        
        Args:
            df: DataFrame with OHLCV data and 'signal' column
        
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info(f"Starting backtest: {self.strategy.name}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"Data points: {len(df)}")
        
        # Process each bar
        for bar_idx, (idx, bar) in enumerate(df.iterrows()):
            signal = int(bar.get('signal', 0))
            close = bar['close']
            
            # Check exit conditions for open position
            if self.position is not None:
                exit_result = self.strategy.evaluate_position(bar, close, bar_idx)
                if exit_result.get('exit', False):
                    self._close_position(bar_idx, bar, exit_result)
            
            # Check entry conditions
            if self.position is None and signal != SignalType.HOLD.value:
                if signal == SignalType.BUY.value:
                    self._open_position(bar_idx, bar, close, SignalType.BUY)
                elif signal == SignalType.SELL.value:
                    self._open_position(bar_idx, bar, close, SignalType.SELL)
            
            # Track equity
            self.equity_curve.append(self.cash)
        
        # Calculate metrics
        metrics = MetricsCalculator.calculate_metrics(
            [vars(t) for t in self.trades],
            self.initial_capital
        )
        
        logger.info(f"Backtest complete: {len(self.trades)} trades closed")
        logger.info(f"Final balance: ${self.cash:,.2f}")
        logger.info(f"Win rate: {metrics['win_rate']:.2f}% | Profit Factor: {metrics['profit_factor']:.2f}")
        
        return {
            'trades': self.trades,
            'metrics': metrics,
            'final_capital': self.cash,
            'equity_curve': self.equity_curve,
        }
    
    def _open_position(self, bar_idx: int, bar: pd.Series, price: float, signal: SignalType):
        """Open a new position"""
        self.position = Trade(
            entry_bar=bar_idx,
            entry_price=price,
            exit_bar=0,
            exit_price=0,
            signal_type=signal,
            pnl=0,
            return_pct=0,
        )
        
        self.strategy.on_trade_open(price, signal)
        logger.info(f"Position opened: {signal.name} @ ${price:.2f} (bar {bar_idx})")
    
    def _close_position(self, bar_idx: int, bar: pd.Series, exit_result: dict):
        """Close the current position"""
        exit_price = exit_result.get('exit_price', bar['close'])
        reason = exit_result.get('reason', 'Strategy signal')
        
        self.position.exit_bar = bar_idx
        self.position.exit_price = exit_price
        self.position.reason = reason
        
        # Calculate P&L
        if self.position.signal_type == SignalType.BUY:
            pnl = (exit_price - self.position.entry_price) * 1  # Simple 1-unit position
        else:  # SELL
            pnl = (self.position.entry_price - exit_price) * 1
        
        # Apply commission and slippage
        comm = exit_price * 0.01 * (self.commission + self.slippage)  # Simplified
        pnl -= comm
        
        self.position.pnl = pnl
        self.position.return_pct = (pnl / self.position.entry_price * 100) if self.position.entry_price > 0 else 0
        
        # Update cash
        self.cash += pnl
        
        # Finalize trade
        self.trades.append(self.position)
        self.strategy.on_trade_close(exit_price, reason)
        
        logger.info(f"Position closed: {reason} @ ${exit_price:.2f} | PnL: ${pnl:.2f} | Return: {self.position.return_pct:.2f}%")
        
        self.position = None
