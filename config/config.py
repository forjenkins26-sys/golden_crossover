"""
Configuration for Golden Crossover Trading System
"""

# Strategy Parameters
STRATEGY_CONFIG = {
    'name': 'GoldenCrossover',
    'symbol': 'BTCUSDT',
    'timeframe': '15m',
    'fast_ema': 12,        # Fast EMA period
    'slow_ema': 26,        # Slow EMA period
    'atr_period': 14,      # ATR for stop loss calculation
    'atr_mult_sl': 2.0,    # ATR multiplier for stop loss
    'risk_per_trade': 0.01,  # Risk 1% per trade
    'risk_reward_ratio': 2.0,  # Take profit at 2R
}

# Backtesting Configuration
BACKTEST_CONFIG = {
    'initial_capital': 100000,  # $100K starting capital
    'commission': 0.001,        # 0.1% commission
    'slippage': 0.0005,         # 0.05% slippage
    'start_date': '2022-01-01',
    'end_date': '2025-12-31',
}

# Data Configuration
DATA_CONFIG = {
    'source': 'yfinance',  # Data source
    'cache_dir': './data',  # Cache directory for downloaded data
}

# Logging Configuration
LOG_CONFIG = {
    'log_dir': './logs',
    'log_level': 'INFO',
    'format': '[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
}
