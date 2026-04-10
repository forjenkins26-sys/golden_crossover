"""
Bidirectional Strategy: LONG + SHORT with 200 EMA Trend Filter
March 1 - April 10, 2026 Backtest

Entry Logic:
- Price > 200 EMA → LONG only (RSI < 25 + Price < Lower BB)
- Price < 200 EMA → SHORT only (RSI > 75 + Price > Upper BB)
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# ============================================================================
# INDICATORS
# ============================================================================

def calculate_rsi(series, period=14):
    """Calculate RSI(14)"""
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

def calculate_ema(series, period=200):
    """Calculate EMA"""
    return series.ewm(span=period, adjust=False).mean()

# ============================================================================
# SESSION FILTERING
# ============================================================================

def get_session(timestamp):
    """Get current session based on IST time (UTC + 5:30)"""
    hour_utc = timestamp.hour
    
    if 0.5 <= hour_utc < 4.5:
        return "Asian"
    elif 5.5 <= hour_utc < 11.5:
        return "London"
    elif 12.5 <= hour_utc < 17.5:
        return "New York"
    else:
        return "Off-Session"

# ============================================================================
# TRADE CLASS
# ============================================================================

class Trade:
    """Track individual trade (LONG or SHORT)"""
    
    def __init__(self, entry_idx, entry_price, entry_time, direction, 
                 tp1, tp2, sl, flat_lot, compound_lot, session, trend):
        self.entry_idx = entry_idx
        self.entry_price = entry_price
        self.entry_time = entry_time
        self.direction = direction  # "LONG" or "SHORT"
        self.trend = trend  # "Bullish" or "Bearish"
        self.tp1 = tp1
        self.tp2 = tp2
        self.sl = sl
        self.flat_lot = flat_lot
        self.compound_lot = compound_lot
        self.session = session
        
        # Exit info
        self.exit_price = None
        self.exit_time = None
        self.exit_type = None
        self.extreme_price = entry_price  # Highest for LONG, Lowest for SHORT
        self.trail_sl = None
        
        # P&L
        self.flat_pnl = 0
        self.compound_pnl = 0
        self.points = 0
    
    def update_extreme(self, high, low):
        """Update extreme price for trailing"""
        if self.direction == "LONG":
            if high > self.extreme_price:
                self.extreme_price = high
        else:  # SHORT
            if low < self.extreme_price:
                self.extreme_price = low
    
    def close(self, exit_price, exit_time, exit_type):
        """Close the trade"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_type = exit_type
        
        # Calculate metrics
        if self.direction == "LONG":
            price_move = exit_price - self.entry_price
        else:  # SHORT
            price_move = self.entry_price - exit_price
        
        self.points = price_move
        self.flat_pnl = price_move * self.flat_lot
        self.compound_pnl = price_move * self.compound_lot

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

class BidirectionalBacktest:
    """Backtest with LONG + SHORT and 200 EMA filter"""
    
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
        self.ema200 = calculate_ema(close, 200)
        
        # Trade tracking
        self.trades = []
        self.position = None
        self.equity_flat = initial_capital
        self.equity_compound = initial_capital
        
        # Trade counters
        self.wins = 0
        self.losses = 0
    
    def get_trend(self, idx):
        """Determine trend: Bullish (price > EMA200) or Bearish (price < EMA200)"""
        if idx < 200:
            return None
        
        price = self.df['Close'].iloc[idx]
        ema = self.ema200.iloc[idx]
        
        if pd.isna(ema):
            return None
        
        if price > ema:
            return "Bullish"
        else:
            return "Bearish"
    
    def get_entry_signal(self, idx):
        """Get entry signal: LONG or SHORT based on trend"""
        if idx < 200:
            return None
        
        rsi = self.rsi.iloc[idx]
        price = self.df['Close'].iloc[idx]
        bb_upper = self.bb_upper.iloc[idx]
        bb_lower = self.bb_lower.iloc[idx]
        
        if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_lower):
            return None
        
        trend = self.get_trend(idx)
        if trend is None:
            return None
        
        # LONG: RSI < 25 AND Price < Lower BB (in bullish trend)
        if trend == "Bullish" and rsi < 25 and price < bb_lower:
            return "LONG"
        
        # SHORT: RSI > 75 AND Price > Upper BB (in bearish trend)
        elif trend == "Bearish" and rsi > 75 and price > bb_upper:
            return "SHORT"
        
        return None
    
    def calculate_levels(self, entry_price, direction):
        """Calculate TP1, TP2, SL based on direction"""
        if direction == "LONG":
            tp1 = entry_price * 1.015  # +1.5%
            tp2 = entry_price * 1.035  # +3.5%
            sl = entry_price * 0.99    # -1.0%
        else:  # SHORT
            tp1 = entry_price * 0.985  # -1.5%
            tp2 = entry_price * 0.965  # -3.5%
            sl = entry_price * 1.01    # +1.0%
        
        return tp1, tp2, sl
    
    def run(self):
        """Run the backtest"""
        print("Running bidirectional backtest (March 1 - April 10, 2026)...\n")
        
        for idx in range(200, len(self.df)):
            current_price = self.df['Close'].iloc[idx]
            current_time = self.df.index[idx]
            
            # Get session
            session = get_session(current_time)
            
            # Exit existing position
            if self.position:
                self._check_exit(idx, current_price, current_time)
            
            # Enter new position (only in sessions)
            if not self.position and session != "Off-Session":
                signal = self.get_entry_signal(idx)
                if signal:
                    self._enter_trade(idx, current_price, current_time, signal, session)
        
        # Close any open position at end
        if self.position:
            self.position.close(
                self.df['Close'].iloc[-1],
                self.df.index[-1],
                "Timeout"
            )
            self.trades.append(self.position)
            self.position = None
        
        return self._generate_report()
    
    def _enter_trade(self, idx, entry_price, entry_time, direction, session):
        """Enter a new trade"""
        tp1, tp2, sl = self.calculate_levels(entry_price, direction)
        trend = self.get_trend(idx)
        
        self.position = Trade(
            entry_idx=idx,
            entry_price=entry_price,
            entry_time=entry_time,
            direction=direction,
            tp1=tp1,
            tp2=tp2,
            sl=sl,
            flat_lot=self.flat_lot_size,
            compound_lot=self.current_compound_lot,
            session=session,
            trend=trend
        )
    
    def _check_exit(self, idx, current_price, current_time):
        """Check exit conditions"""
        high = self.df['High'].iloc[idx]
        low = self.df['Low'].iloc[idx]
        
        # Update extreme price for trailing
        self.position.update_extreme(high, low)
        
        if self.position.direction == "LONG":
            self._check_exit_long(high, low, current_time)
        else:  # SHORT
            self._check_exit_short(high, low, current_time)
    
    def _check_exit_long(self, high, low, current_time):
        """Check exit for LONG"""
        # TP2: Book profit
        if high >= self.position.tp2:
            self.position.close(self.position.tp2, current_time, "TP2")
            self._process_closed_trade(win=True)
            return
        
        # TP1: Start trailing
        if high >= self.position.tp1:
            trail_sl = self.position.extreme_price * 0.99
            
            if low <= trail_sl:
                self.position.close(trail_sl, current_time, "TP1_Trail")
                self._process_closed_trade(win=True)
                return
            
            self.position.trail_sl = trail_sl
        
        # SL: Stop loss
        if low <= self.position.sl:
            self.position.close(self.position.sl, current_time, "SL")
            self._process_closed_trade(win=False)
            return
    
    def _check_exit_short(self, high, low, current_time):
        """Check exit for SHORT"""
        # TP2: Book profit
        if low <= self.position.tp2:
            self.position.close(self.position.tp2, current_time, "TP2")
            self._process_closed_trade(win=True)
            return
        
        # TP1: Start trailing
        if low <= self.position.tp1:
            trail_sl = self.position.extreme_price * 1.01
            
            if high >= trail_sl:
                self.position.close(trail_sl, current_time, "TP1_Trail")
                self._process_closed_trade(win=True)
                return
            
            self.position.trail_sl = trail_sl
        
        # SL: Stop loss
        if high >= self.position.sl:
            self.position.close(self.position.sl, current_time, "SL")
            self._process_closed_trade(win=False)
            return
    
    def _process_closed_trade(self, win):
        """Process closed trade"""
        self.trades.append(self.position)
        
        # Update equity
        self.equity_flat += self.position.flat_pnl
        self.equity_compound += self.position.compound_pnl
        
        # Update lot sizing
        if win:
            self.wins += 1
            self.current_compound_lot += self.flat_lot_size
        else:
            self.losses += 1
            self.current_compound_lot = self.flat_lot_size
        
        self.position = None
    
    def _generate_report(self):
        """Generate report"""
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

def load_data():
    """Load BTC 1-hour data"""
    print("📥 Downloading BTC 1-hour data (March 1 - April 10, 2026)...\n")
    
    df = yf.download(
        'BTC-USD',
        start="2026-03-01",
        end="2026-04-10",
        interval='1h',
        progress=False
    )
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    print(f"✓ Loaded {len(df)} 1-hour bars\n")
    return df

# ============================================================================
# RESULTS
# ============================================================================

def create_journal(trades):
    """Create trade journal"""
    data = []
    
    for trade in trades:
        entry_date = trade.entry_time.strftime("%Y-%m-%d")
        entry_time = trade.entry_time.strftime("%H:%M")
        exit_date = trade.exit_time.strftime("%Y-%m-%d") if trade.exit_time else "-"
        exit_time = trade.exit_time.strftime("%H:%M") if trade.exit_time else "-"
        
        data.append({
            'Direction': trade.direction,
            'Flat_Lots': f"{trade.flat_lot:.2f}",
            'Cmpd_Lots': f"{trade.compound_lot:.2f}",
            'Date_In': entry_date,
            'Time_In': entry_time,
            'Price_In': f"${trade.entry_price:.2f}",
            'Date_Out': exit_date,
            'Time_Out': exit_time,
            'Price_Out': f"${trade.exit_price:.2f}" if trade.exit_price else "-",
            'PTS': f"{trade.points:+.2f}",
            'Flat_P&L': f"${trade.flat_pnl:+.2f}",
            'Cmpd_P&L': f"${trade.compound_pnl:+.2f}",
            'Status': trade.exit_type,
            'Session': trade.session,
            'Trend': trade.trend,
        })
    
    return pd.DataFrame(data)

def print_results(report, df):
    """Print results"""
    trades = report['trades']
    
    print("\n" + "=" * 180)
    print("BIDIRECTIONAL BACKTEST: March 1 - April 10, 2026")
    print("Strategy: LONG (>200 EMA) + SHORT (<200 EMA) with RSI + Bollinger Bands")
    print("=" * 180)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Trades:        {len(trades)}")
    print(f"   LONG Trades:         {sum(1 for t in trades if t.direction == 'LONG')}")
    print(f"   SHORT Trades:        {sum(1 for t in trades if t.direction == 'SHORT')}")
    print(f"   Wins:                {report['wins']}")
    print(f"   Losses:              {report['losses']}")
    if len(trades) > 0:
        wr = (report['wins'] / len(trades)) * 100
        print(f"   Win Rate:            {wr:.2f}%")
    
    print(f"\n💰 FLAT LOT SIZING (0.10 BTC constant):")
    print(f"   Initial Capital:     ${report['initial_capital']:.2f}")
    print(f"   Final Equity:        ${report['final_equity_flat']:.2f}")
    flat_return = ((report['final_equity_flat'] - report['initial_capital']) / report['initial_capital']) * 100
    print(f"   Total Return:        {flat_return:+.2f}%")
    print(f"   Net Profit:          ${report['final_equity_flat'] - report['initial_capital']:+.2f}")
    
    print(f"\n💰 COMPOUND LOT SIZING:")
    print(f"   Initial Capital:     ${report['initial_capital']:.2f}")
    print(f"   Final Equity:        ${report['final_equity_compound']:.2f}")
    compound_return = ((report['final_equity_compound'] - report['initial_capital']) / report['initial_capital']) * 100
    print(f"   Total Return:        {compound_return:+.2f}%")
    print(f"   Net Profit:          ${report['final_equity_compound'] - report['initial_capital']:+.2f}")
    
    if report['final_equity_compound'] > report['final_equity_flat']:
        diff = report['final_equity_compound'] - report['final_equity_flat']
        print(f"\n✅ COMPOUND is better by: ${diff:+.2f}")
    else:
        diff = report['final_equity_flat'] - report['final_equity_compound']
        print(f"\n✅ FLAT is better by: ${diff:+.2f}")
    
    print("\n" + "=" * 180)
    print("DETAILED TRADE JOURNAL")
    print("=" * 180 + "\n")
    
    journal = create_journal(trades)
    print(journal.to_string(index=False))
    
    print("\n" + "=" * 180 + "\n")
    
    journal.to_csv('backtest_bidirectional_march_april_2026.csv', index=False)
    print(f"✅ Journal saved to: backtest_bidirectional_march_april_2026.csv\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 180)
    print("BIDIRECTIONAL BACKTEST: March 1 - April 10, 2026")
    print("LONG + SHORT with 200 EMA Trend Filter")
    print("=" * 180 + "\n")
    
    df = load_data()
    
    if df is not None and len(df) > 200:
        backtest = BidirectionalBacktest(df, initial_capital=500, flat_lot_size=0.10)
        report = backtest.run()
        print_results(report, df)
    else:
        print("✗ Failed to load data")
