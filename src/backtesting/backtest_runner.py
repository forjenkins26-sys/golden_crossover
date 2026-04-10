"""Backtest Runner - CLI interface for running backtests"""

import argparse
from src.strategies.golden_crossover import GoldenCrossoverStrategy
from src.data.data_handler import DataHandler
from src.backtesting.backtest_engine import BacktestEngine
from src.logging_journal.logger import get_logger

logger = get_logger(__name__)


def print_results(results: dict):
    """Pretty print backtest results"""
    metrics = results['metrics']
    
    print("\n" + "=" * 80)
    print(f"BACKTEST RESULTS: {metrics.get('strategy_name', 'Unknown')}")
    print("=" * 80)
    
    print("\nCAPITAL:")
    print(f"  Initial:                     {results.get('initial_capital', 0):,.2f}")
    print(f"  Final:                       {results['final_capital']:,.2f}")
    print(f"  Total Return:                {metrics['return_pct']:.2f}%")
    
    print("\nTRADE STATISTICS:")
    print(f"  Total Trades:                    {metrics['total_trades']}")
    print(f"  Winning Trades:                  {metrics['winning_trades']}")
    print(f"  Losing Trades:                   {metrics['losing_trades']}")
    print(f"  Win Rate:                    {metrics['win_rate']:.2f}%")
    print(f"  Profit Factor:                {metrics['profit_factor']:.2f}")
    print(f"  Avg Win:                     ${metrics['avg_win']:.2f}")
    print(f"  Avg Loss:                    ${metrics['avg_loss']:.2f}")
    print(f"  Largest Win:                 ${metrics['largest_win']:.2f}")
    print(f"  Largest Loss:                ${metrics['largest_loss']:.2f}")
    
    print("\nRISK METRICS:")
    print(f"  Max Drawdown:                {metrics['max_drawdown']:.2f}%")
    print(f"  Sharpe Ratio:                {metrics['sharpe_ratio']:.2f}")
    print(f"  Sortino Ratio:               {metrics['sortino_ratio']:.2f}")
    
    print("\n" + "=" * 80 + "\n")


def run_backtest(args):
    """Run a backtest"""
    logger.info(f"Running backtest: {args.strategy}")
    logger.info(f"Symbol: {args.symbol}, Timeframe: {args.timeframe}")
    logger.info(f"Period: {args.start} to {args.end}")
    
    # Create strategy
    if args.strategy.lower() == 'goldencrossover':
        strategy = GoldenCrossoverStrategy(
            symbol=args.symbol,
            timeframe=args.timeframe,
        )
    else:
        logger.error(f"Unknown strategy: {args.strategy}")
        return
    
    # Download data
    data_handler = DataHandler()
    df = data_handler.get_historical_data(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        interval=args.timeframe,
    )
    
    # Generate signals
    logger.info("Generating signals...")
    df = strategy.generate_signals(df)
    
    # Run backtest
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=args.initial_capital,
        commission=args.commission,
        slippage=args.slippage,
    )
    
    results = engine.run(df)
    results['initial_capital'] = args.initial_capital
    results['metrics']['strategy_name'] = strategy.name
    
    # Print results
    print_results(results)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Golden Crossover Backtesting System')
    
    parser.add_argument(
        '--strategy',
        default='GoldenCrossover',
        help='Strategy name (default: GoldenCrossover)'
    )
    parser.add_argument(
        '--symbol',
        default='BTC-USD',
        help='Trading symbol (default: BTC-USD)'
    )
    parser.add_argument(
        '--timeframe',
        default='15m',
        help='Timeframe (default: 15m)'
    )
    parser.add_argument(
        '--start',
        default='2022-01-01',
        help='Start date (YYYY-MM-DD, default: 2022-01-01)'
    )
    parser.add_argument(
        '--end',
        default='2025-12-31',
        help='End date (YYYY-MM-DD, default: 2025-12-31)'
    )
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=100000,
        help='Initial capital (default: 100000)'
    )
    parser.add_argument(
        '--commission',
        type=float,
        default=0.001,
        help='Commission rate (default: 0.001 = 0.1%%)'
    )
    parser.add_argument(
        '--slippage',
        type=float,
        default=0.0005,
        help='Slippage rate (default: 0.0005 = 0.05%%)'
    )
    
    args = parser.parse_args()
    run_backtest(args)


if __name__ == '__main__':
    main()
