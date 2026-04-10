# Golden Crossover Trading System - Setup Instructions

## Project Overview
A cryptocurrency trading system implementing a Golden Crossover (EMA crossover) strategy on BTCUSDT 15m timeframe.

## Development Checklist

- [ ] **Setup Complete** - Project directories and files created
- [ ] **Strategy Implementation** - Create GoldenCrossoverStrategy class
- [ ] **Data Handler** - Implement data loading from yfinance
- [ ] **Backtesting Engine** - Implement backtest runner with metrics
- [ ] **Metrics Calculator** - CAGR, Sharpe, Sortino, Calmar, win rate, profit factor
- [ ] **Initial Backtests** - Run 2022-2025 yearly tests
- [ ] **Documentation** - Update README with results

## Key Files to Create

1. `src/strategies/base_strategy.py` - Base strategy class
2. `src/strategies/golden_crossover.py` - Golden Crossover implementation
3. `src/data/data_handler.py` - Historical data fetching
4. `src/backtesting/backtest_engine.py` - Backtesting framework
5. `src/backtesting/metrics_calculator.py` - Performance metrics
6. `src/backtesting/backtest_runner.py` - CLI interface
7. `src/execution/paper_trading_engine.py` - Paper trading
8. `src/logging_journal/logger.py` - Logging system

## Strategy Specification

**Name:** Golden Crossover
**Timeframe:** 15m (BTCUSDT)
**Entry:** EMA12 crosses EMA26 (Golden Cross = BUY, Death Cross = SELL)
**Exit:** Opposite cross OR stop loss / take profit
**Risk Management:** 1% risk per trade, 2:1 RR ratio, ATR-based stops

## Progress Tracking

Update this file as you complete each section.
