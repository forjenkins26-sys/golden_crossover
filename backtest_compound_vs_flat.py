"""
BTC 1-Hour RSI + Bollinger Band Strategy
Compound Lot Sizing vs Flat Lot Sizing
With TP1/TP2, Trailing SL, Session Filtering, Trade Journal
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from enum import Enum

# ============================================================================
# CONFIGURATION & ENUMS
# ============================================================================

class Session(Enum):
    """Trading sessions - can be toggled on/off"""
    LONDON = "London (08:00-16:00 UTC)"
    NEWYORK = "New York (13:00-21:00 UTC)"
    TOKYO = "Tokyo (00:00-08:00 UTC)"
    SYDNEY = "Sydney (22:00-06:00 UTC)"  # Previous day 22:00 to next day 06:00 UTC

class TradeStatus(Enum):
    CLOSED_TP1_TRAIL = "Closed TP1 (Trailed)"
    CLOSED_TP2 = "Closed TP2 (Booked)"
    CLOSED_SL = "Closed SL (Loss)"
    CLOSED_TIMEOUT = "Closed Timeout"
    OPEN = "Open"

# ============================================================================
# SESSION FILTERING
# ============================================================================

class SessionFilter:
    """Check if current time is in a specific session"""
    
    # Sessions can be enabled/disabled
    ACTIVE_SESSIONS = {
        'london': True,
        'newyork': True,
        'tokyo': True,
        'sydney': True,
    }
    
    @staticmethod
    def get_hour_utc(timestamp):
        """Get hour in UTC from timestamp"""
        return timestamp.hour
    
    @staticmethod
    def is_london(hour_utc):
        """08:00-16:00 UTC"""
        return 8 <= hour_utc < 16
    
    @staticmethod
    def is_newyork(hour_utc):
        """13:00-21:00 UTC"""
        return 13 <= hour_utc < 21
    
    @staticmethod
    def is_tokyo(hour_utc):
        """00:00-08:00 UTC"""
        return 0 <= hour_utc < 8
    
    @staticmethod
    def is_sydney(hour_utc):
        """22:00-06:00 UTC (wraps around midnight)"""
        return hour_utc >= 22 or hour_utc < 6
    
    @staticmethod
    def is_allowed(timestamp):
        """Check if timestamp is in allowed sessions"""
        hour = SessionFilter.get_hour_utc(timestamp)
        
        if SessionFilter.ACTIVE_SESSIONS['london'] and SessionFilter.is_london(hour):
            return True, "London"
        if SessionFilter.ACTIVE_SESSIONS['newyork'] and SessionFilter.is_newyork(hour):
            return True, "New York"
        if SessionFilter.ACTIVE_SESSIONS['tokyo'] and SessionFilter.is_tokyo(hour):
            return True, "Tokyo"
        if SessionFilter.ACTIVE_SESSIONS['sydney'] and SessionFilter.is_sydney(hour):
            return True, "Sydney"
        
        return False, "Off-Session"

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(series, period=14):
    """Calculate RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger_bands(series, period=20, num_std=2.0):
    """Calculate Bollinger Bands"""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower

# ============================================================================
# TRADE CLASS
# ============================================================================

class Trade:
    """Track individual trade with compound vs flat P&L"""
    
    def __init__(self, entry_idx, entry_price, entry_time, direction, 
                 tp1, tp2, sl, flat_lot, compound_lot, session):
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction  # "LONG"
        self.tp1 = tp1
        self.tp2 = tp2
        self.sl = sl
        self.flat_lot = flat_lot
        self.compound_lot = compound_lot
        self.session = session
        
        # Exit info
        self.exit_idx = None
        self.exit_price = None
        self.exit_time = None
        self.exit_type = None
        self.highest_price = entry_price  # For trailing
        self.trail_sb = None  # Trailing stop break
        
        # P&L
        self.flat_pnl = 0
        self.compound_pnl = 0
        self.flat_pnl_pct = 0
        self.compound_pnl_pct = 0
    
    def update_high(self, price):
        """Update highest price for trailing"""
        if price > self.highest_price:
            self.highest_price = price
    
    def close(self, exit_idx, exit_price, exit_time, exit_type):
        """Close the trade"""
        self.exit_idx = exit_idx
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_type = exit_type
        
        # Calculate P&L
        if self.direction == "LONG":
            price_move = exit_price - self.entry_price
        else:
            price_move = self.entry_price - exit_price
        
        # Flat lot P&L
        self.flat_pnl = price_move * self.flat_lot
        self.flat_pnl_pct = (price_move / self.entry_price) * 100
        
        # Compound lot P&L
        self.compound_pnl = price_move * self.compound_lot
        self.compound_pnl_pct = (price_move / self.entry_price) * 100

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class TradingBacktest:
    """Main backtest engine with compound vs flat lot sizing"""
    
    def __init__(self, df, initial_capital=500, flat_lot_size=0.10):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.flat_lot_size = flat_lot_size
        self.current_compound_lot = flat_lot_size
        
        # Precompute indicators
        close = self.df['Close']
        self.rsi = calculate_rsi(close, 14)
        upper, sma, lower = calculate_bollinger_bands(close, 20, 2.0)
        self.bb_upper = upper
        self.bb_sma = sma
        self.bb_lower = lower
        
        # Trade tracking
        self.trades = []
        self.position = None
        self.equity_flat = initial_capital
        self.equity_compound = initial_capital
        
        # Trade counters
        self.wins = 0
        self.losses = 0
    
    def get_entry_signal(self, idx):
        """
        Entry signal: RSI < 25 AND Price < Lower BB
        (High-conviction oversold)
        """
        if idx < 50:  # Need enough data for indicators
            return False
        
        rsi = self.rsi.iloc[idx]
        price = self.df['Close'].iloc[idx]
        bb_lower = self.bb_lower.iloc[idx]
        
        # Entry condition
        if rsi < 25 and price < bb_lower:
            return True
        
        return False
    
    def calculate_levels(self, entry_price):
        """Calculate TP1, TP2, SL"""
        tp1 = entry_price * 1.015  # +1.5%
        tp2 = entry_price * 1.035  # +3.5%
        sl = entry_price * 0.99    # -1.0%
        return tp1, tp2, sl
    
    def run(self):
        """Run the backtest"""
        print("Running backtest...")
        
        for idx in range(50, len(self.df)):
            current_price = self.df['Close'].iloc[idx]
            current_time = self.df.index[idx]
            
            # Check if allowed session
            is_allowed, session_name = SessionFilter.is_allowed(current_time)
            
            # Exit existing position
            if self.position:
                self._check_exit(idx, current_price, current_time)
            
            # Enter new position (only in allowed sessions)
            if not self.position and is_allowed:
                if self.get_entry_signal(idx):
                    self._enter_trade(idx, current_price, current_time, session_name)
        
        # Close any open position at end
        if self.position:
            self.position.close(
                len(self.df) - 1,
                self.df['Close'].iloc[-1],
                self.df.index[-1],
                TradeStatus.CLOSED_TIMEOUT.value
            )
            self.trades.append(self.position)
            self.position = None
        
        return self._generate_report()
    
    def _enter_trade(self, idx, entry_price, entry_time, session):
        """Enter a new trade"""
        tp1, tp2, sl = self.calculate_levels(entry_price)
        
        self.position = Trade(
            entry_idx=idx,
            entry_price=entry_price,
            entry_time=entry_time,
            direction="LONG",
            tp1=tp1,
            tp2=tp2,
            sl=sl,
            flat_lot=self.flat_lot_size,
            compound_lot=self.current_compound_lot,
            session=session
        )
    
    def _check_exit(self, idx, current_price, current_time):
        """Check exit conditions"""
        high = self.df['High'].iloc[idx]
        low = self.df['Low'].iloc[idx]
        
        # Update highest price for trailing
        self.position.update_high(high)
        
        # TP2: Book profit immediately
        if high >= self.position.tp2:
            self.position.close(idx, self.position.tp2, current_time, 
                              TradeStatus.CLOSED_TP2.value)
            self._process_closed_trade(win=True)
            return
        
        # TP1: Start trailing
        if high >= self.position.tp1:
            # Trail by 1% from highest
            trail_sb = self.position.highest_price * 0.99
            
            # Check if trailing SL hit
            if low <= trail_sb:
                self.position.close(idx, trail_sb, current_time, 
                                  TradeStatus.CLOSED_TP1_TRAIL.value)
                self._process_closed_trade(win=True)  # TP1 trail is still a win
                return
            
            # Update trail SB for next check
            self.position.trail_sb = trail_sb
        
        # SL: Stop loss
        if low <= self.position.sl:
            self.position.close(idx, self.position.sl, current_time, 
                              TradeStatus.CLOSED_SL.value)
            self._process_closed_trade(win=False)
            return
    
    def _process_closed_trade(self, win):
        """Process closed trade and update lot sizing"""
        self.trades.append(self.position)
        
        # Update equity
        self.equity_flat += self.position.flat_pnl
        self.equity_compound += self.position.compound_pnl
        
        # Update lot sizing (compound only)
        if win:
            self.wins += 1
            # Increase lot on win
            self.current_compound_lot += self.flat_lot_size
        else:
            self.losses += 1
            # Reset to base lot on loss
            self.current_compound_lot = self.flat_lot_size
        
        self.position = None
    
    def _generate_report(self):
        """Generate backtest report"""
        return {
            'trades': self.trades,
            'initial_capital': self.initial_capital,
            'final_equity_flat': self.equity_flat,
            'final_equity_compound': self.equity_compound,
            'wins': self.wins,
            'losses': self.losses,
        }

# ============================================================================
# DATA LOADING
# ============================================================================

def load_btc_1h():
    """Load BTC 1-hour bars (1 year of data)"""
    print("Downloading BTC 1-hour data (1 year)...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    try:
        df = yf.download(
            'BTC-USD',
            start=start_date.date(),
            end=end_date.date(),
            interval='1h',
            progress=False
        )
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        print(f"✓ Loaded {len(df)} 1-hour bars ({df.index[0]} to {df.index[-1]})")
        
        return df
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

# ============================================================================
# TRADE JOURNAL & REPORTING
# ============================================================================

def create_trade_journal(trades):
    """Create detailed trade journal"""
    journal_data = []
    
    for trade in trades:
        entry_date = trade.entry_time.strftime("%Y-%m-%d %H:%M")
        exit_date = trade.exit_time.strftime("%Y-%m-%d %H:%M") if trade.exit_time else "Open"
        
        journal_data.append({
            'Direction': trade.direction,
            'Flat_Lots': f"{trade.flat_lot:.2f}",
            'Cmpd_Lots': f"{trade.compound_lot:.2f}",
            'Open_Date': entry_date,
            'Entry_Price': f"${trade.entry_price:.2f}",
            'Exit_Price': f"${trade.exit_price:.2f}" if trade.exit_price else "-",
            'Close_Date': exit_date,
            'Flat_PnL': f"${trade.flat_pnl:.2f}",
            'Cmpd_PnL': f"${trade.compound_pnl:.2f}",
            'Flat_Return': f"{trade.flat_pnl_pct:.2f}%",
            'Cmpd_Return': f"{trade.compound_pnl_pct:.2f}%",
            'Status': trade.exit_type,
            'Session': trade.session,
        })
    
    return pd.DataFrame(journal_data)

def print_results(report, df):
    """Print backtest results"""
    trades = report['trades']
    
    print("\n" + "=" * 100)
    print("BTC 1-HOUR TRADING SYSTEM: COMPOUND vs FLAT LOT SIZING")
    print("=" * 100)
    
    print("\nBACKTEST SUMMARY:")
    print(f"  Data Period:                {df.index[0]} to {df.index[-1]}")
    print(f"  Total Bars:                 {len(df)}")
    print(f"  Total Trades:               {len(trades)}")
    print(f"  Wins:                       {report['wins']}")
    print(f"  Losses:                     {report['losses']}")
    if len(trades) > 0:
        wr = (report['wins'] / len(trades)) * 100
        print(f"  Win Rate:                   {wr:.2f}%")
    
    print("\n" + "-" * 100)
    print("FLAT LOT SIZING (Constant 0.10 lot):")
    print("-" * 100)
    print(f"  Initial Capital:            ${report['initial_capital']:.2f}")
    print(f"  Final Equity:               ${report['final_equity_flat']:.2f}")
    flat_return = ((report['final_equity_flat'] - report['initial_capital']) / report['initial_capital']) * 100
    print(f"  Total Return:               {flat_return:.2f}%")
    print(f"  Net Profit:                 ${report['final_equity_flat'] - report['initial_capital']:.2f}")
    
    print("\n" + "-" * 100)
    print("COMPOUND LOT SIZING (Increase on wins, reset on losses):")
    print("-" * 100)
    print(f"  Initial Capital:            ${report['initial_capital']:.2f}")
    print(f"  Final Equity:               ${report['final_equity_compound']:.2f}")
    compound_return = ((report['final_equity_compound'] - report['initial_capital']) / report['initial_capital']) * 100
    print(f"  Total Return:               {compound_return:.2f}%")
    print(f"  Net Profit:                 ${report['final_equity_compound'] - report['initial_capital']:.2f}")
    
    print("\n" + "-" * 100)
    print("COMPARISON:")
    print("-" * 100)
    if report['final_equity_compound'] > report['final_equity_flat']:
        diff = report['final_equity_compound'] - report['final_equity_flat']
        print(f"  ✅ COMPOUND is better by ${diff:.2f}")
    else:
        diff = report['final_equity_flat'] - report['final_equity_compound']
        print(f"  ✅ FLAT is better by ${diff:.2f}")
    
    print("\n" + "=" * 100)
    print("TRADE JOURNAL")
    print("=" * 100)
    
    journal = create_trade_journal(trades)
    print(journal.to_string(index=False))
    
    print("\n" + "=" * 100)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 100)
    print("BTC 1-HOUR RSI + BOLLINGER BAND STRATEGY")
    print("Compound vs Flat Lot Sizing")
    print("=" * 100 + "\n")
    
    # Load data
    df = load_btc_1h()
    
    if df is not None and len(df) > 100:
        # Run backtest
        backtest = TradingBacktest(df, initial_capital=500, flat_lot_size=0.10)
        report = backtest.run()
        
        # Print results
        print_results(report, df)
        
        # Save journal to CSV
        journal = create_trade_journal(report['trades'])
        journal.to_csv('trade_journal.csv', index=False)
        print(f"\n✓ Trade journal saved to 'trade_journal.csv'")
    else:
        print("✗ Failed to load data")
