"""Metrics Calculator - Performance metrics for backtesting"""

import pandas as pd
import numpy as np
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


class MetricsCalculator:
    """Calculates trading performance metrics"""
    
    @staticmethod
    def calculate_metrics(trades: list, initial_capital: float = 100000) -> dict:
        """
        Calculate comprehensive trading metrics
        
        Args:
            trades: List of completed trade dicts
            initial_capital: Starting capital
        
        Returns:
            Dictionary with performance metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'largest_win': 0,
                'largest_loss': 0,
            }
        
        # Extract P&L data
        pnls = [t.get('pnl', 0) for t in trades]
        returns = [t.get('return_pct', 0) for t in trades]
        
        # Count winners/losers
        winning_trades = sum(1 for p in pnls if p > 0)
        losing_trades = sum(1 for p in pnls if p < 0)
        total_trades = len(trades)
        
        # Win metrics
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p < 0]
        
        total_wins = sum(wins) if wins else 0
        total_losses = sum(losses) if losses else 0
        
        avg_win = (total_wins / len(wins)) if wins else 0
        avg_loss = -(total_losses / len(losses)) if losses else 0
        
        # Profit Factor
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Return calculations
        total_return = sum(pnls)
        return_pct = (total_return / initial_capital) * 100 if initial_capital > 0 else 0
        
        # Sharpe Ratio (simplified, assuming daily returns)
        if len(returns) > 1:
            daily_returns = np.array(returns) / 100
            excess_returns = daily_returns - 0.0  # Risk-free rate = 0
            sharpe = np.mean(excess_returns) / (np.std(excess_returns) + 1e-6) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Sortino Ratio (only downside volatility)
        if len(returns) > 1:
            daily_returns = np.array(returns) / 100
            downside = np.where(daily_returns < 0, daily_returns, 0)
            downside_std = np.sqrt(np.mean(downside ** 2))
            sortino = np.mean(daily_returns) / (downside_std + 1e-6) * np.sqrt(252)
        else:
            sortino = 0
        
        # Drawdown
        max_drawdown = MetricsCalculator._calculate_max_drawdown(pnls, initial_capital)
        
        metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'return_pct': return_pct,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max(wins) if wins else 0,
            'largest_loss': -max(losses) if losses else 0,
        }
        
        return metrics
    
    @staticmethod
    def _calculate_max_drawdown(pnls: list, initial_capital: float) -> float:
        """Calculate maximum drawdown percentage"""
        if not pnls:
            return 0
        
        running_balance = initial_capital
        peak = initial_capital
        max_dd = 0
        
        for pnl in pnls:
            running_balance += pnl
            if running_balance > peak:
                peak = running_balance
            
            dd = (peak - running_balance) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100
