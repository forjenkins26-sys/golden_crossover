# Golden Crossover Trading System

A systematic trading bot for cryptocurrency (BTCUSDT) using a Golden Crossover strategy on 15-minute timeframes.

## Project Structure

```
golden_crossover/
├── src/
│   ├── strategies/          # Trading strategy implementations
│   ├── backtesting/         # Backtesting engine & metrics
│   ├── execution/           # Paper trading & live execution
│   ├── data/               # Data handlers (OHLCV)
│   └── logging_journal/    # Logging system
├── config/                 # Configuration files
├── logs/                   # Log outputs
├── tests/                  # Unit tests
└── requirements.txt        # Python dependencies
```

## Quick Start

### 1. Setup Environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Backtest (Coming Soon)
```bash
python -m src.backtesting.backtest_runner --symbol BTCUSDT --timeframe 15m --strategy GoldenCrossover --start 2022-01-01 --end 2025-12-31
```

### 3. Paper Trade (Coming Soon)
```bash
python -m src.execution.paper_trading_engine --mode paper --strategy GoldenCrossover
```

## Strategy: Golden Crossover

**Entry Logic:**
- BUY: Fast EMA (12) crosses above Slow EMA (26)
- SELL: Fast EMA (12) crosses below Slow EMA (26)

**Risk Management:**
- Stop Loss: ATR-based (configurable multiplier)
- Take Profit: Fixed Risk-Reward ratio (default 2:1)
- Position Sizing: 1% risk per trade

**Filters:**
- Volume confirmation
- Trend direction confirmation
- Session-based trading (optional)

## Status

🔧 **In Development** - Framework setup complete, strategy implementation in progress.

### Completed
- ✅ Project structure
- ✅ Directory setup
- ✅ Requirements configuration

### Next Steps
- ⏳ Strategy implementation (GoldenCrossoverStrategy)
- ⏳ Data handler
- ⏳ Backtesting framework
- ⏳ Metrics calculator
- ⏳ Backtests (2022-2025)

## Requirements

- Python 3.8+
- pip
- Virtual environment (recommended)

## Dependencies

- **pandas** - Data manipulation
- **numpy** - Numerical computing
- **yfinance** - Historical data download
- **python-dotenv** - Configuration management

## License

MIT License
