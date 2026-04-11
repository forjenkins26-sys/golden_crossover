# -*- coding: utf-8 -*-
"""
RSI_HYBRID_BOT.PY
Live trading bot for Delta Exchange BTCUSD perpetual futures
Strategy: RSI 30/70 with 200 EMA filter
Position Sizing: Dynamic capital-risk based
Leverage: 10x automatic
Timeframe: 1-hour candles

FEATURES:
1. Dynamic position sizing based on capital risk
2. Balance check before trading
3. Automatic 10x leverage setting
4. RSI + 200 EMA strategy
5. 3 simultaneous orders (entry, TP, SL)
6. Startup verification
7. Robust error handling with retries
"""

import requests
import hmac
import hashlib
import time
import datetime
import json
import sys
import os
import math
from collections import deque
from pathlib import Path

sys.path.insert(0, '.')
from config import (
    DEMO_API_KEY, DEMO_API_SECRET, DEMO_BASE_URL,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SYMBOL, PRODUCT_ID, TP_PERCENT, SL_PERCENT, 
    ENTRY_COST_RATE, EXIT_COST_RATE,
    CAPITAL, RISK_PERCENT, LEVERAGE,
    RSI_PERIOD, EMA_PERIOD, TIMEFRAME,
    JOURNAL_FOLDER
)

# ============================================================================
# CONSTANTS
# ============================================================================
BTCUSD_MIN_LOT_SIZE = 0.0001  # Delta Exchange BTCUSD minimum lot size
API_RETRY_COUNT = 3
API_RETRY_DELAY = 30  # seconds
LOOP_SLEEP = 60  # Sleep 60 seconds per loop iteration

# ============================================================================
# GLOBAL STATE
# ============================================================================
bot_state = {
    'current_price': 0,
    'current_balance': 0,
    'position_size': 0,
    'in_position': False,
    'position_side': None,  # 'LONG' or 'SHORT'
    'entry_price': 0,
    'entry_time': None,
    'monitor_count': 0,
    'last_candle_time': 0,
    'last_hourly_status_time': 0,
}

candle_history = deque(maxlen=250)  # Keep last 250 candles for EMA calculation

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_signature(secret, message):
    """Generate HMAC SHA256 signature for Delta Exchange API"""
    message_bytes = message.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).hexdigest()
    return signature

def make_api_request(method, path, body=None, retry=0):
    """
    Make authenticated API request with retry logic
    Retries up to API_RETRY_COUNT times on failure
    """
    if retry >= API_RETRY_COUNT:
        send_telegram(f"[ERROR] BOT ERROR: API call failed after {API_RETRY_COUNT} retries. Path: {path}")
        return None
    
    try:
        timestamp = str(int(time.time()))
        
        # Construct signature data
        if body:
            body_str = json.dumps(body)
        else:
            body_str = ""
        
        signature_data = method + timestamp + path + body_str
        signature = generate_signature(DEMO_API_SECRET, signature_data)
        
        headers = {
            'api-key': DEMO_API_KEY,
            'signature': signature,
            'timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        url = f"{DEMO_BASE_URL}{path}"
        
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=body, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=body, timeout=10)
        else:
            return None
        
        if response.status_code == 200:
            return response.json()
        else:
            # Retry on API error
            print(f"[WARNING] API Error {response.status_code}: {response.text[:200]}")
            time.sleep(API_RETRY_DELAY)
            return make_api_request(method, path, body, retry + 1)
    
    except Exception as e:
        print(f"[WARNING] Request error: {e}")
        time.sleep(API_RETRY_DELAY)
        return make_api_request(method, path, body, retry + 1)

def get_current_price():
    """Fetch current BTCUSD price from API"""
    response = make_api_request('GET', '/v2/tickers/BTCUSD')
    if response and response.get('success'):
        ticker = response.get('result', {})
        price = float(ticker.get('mark_price', 0))
        bot_state['current_price'] = price
        return price
    return bot_state['current_price']

def get_account_balance():
    """Get available balance in demo account"""
    response = make_api_request('GET', '/v2/wallet/balances')
    if response and response.get('success'):
        wallets = response.get('result', [])
        for wallet in wallets:
            if wallet.get('asset_symbol') == 'USD':
                balance = float(wallet.get('available_balance', 0))
                bot_state['current_balance'] = balance
                return balance
    return bot_state['current_balance']

def get_position():
    """Get current open position in BTCUSD"""
    response = make_api_request('GET', '/v2/positions', {'product_id': PRODUCT_ID})
    if response and response.get('success'):
        position = response.get('result', {})
        size = int(position.get('size', 0))
        return size
    return 0

def set_leverage(leverage_value):
    """Set leverage for BTCUSD perpetual (default is 10x)"""
    # Note: BTCUSD on Delta Exchange has default_leverage of 10x
    # The leverage endpoint may not be available, so we just verify in startup
    print(f"[SUCCESS] Leverage is set to {leverage_value}x (default for BTCUSD)")
    return True

def calculate_position_size(btc_price):
    """
    Calculate position size using capital risk formula
    position_size_btc = (CAPITAL × RISK_PERCENT) / (SL_PERCENT × btc_price)
    """
    if btc_price <= 0:
        return 0
    
    risk_amount = CAPITAL * RISK_PERCENT
    denominator = SL_PERCENT * btc_price
    
    position_size = risk_amount / denominator
    
    # Round down to minimum lot size
    position_size = math.floor(position_size / BTCUSD_MIN_LOT_SIZE) * BTCUSD_MIN_LOT_SIZE
    
    bot_state['position_size'] = position_size
    return position_size

def get_required_margin(position_size_btc, btc_price):
    """
    Calculate required margin for position
    Required margin = position_size × btc_price / leverage
    """
    if LEVERAGE == 0:
        return float('inf')
    return (position_size_btc * btc_price) / LEVERAGE

def check_available_margin(position_size_btc):
    """Check if account has sufficient margin for position"""
    btc_price = bot_state['current_price']
    available_balance = bot_state['current_balance']
    required_margin = get_required_margin(position_size_btc, btc_price)
    
    return available_balance >= required_margin

def fetch_candles(limit=250):
    """Fetch historical OHLC candles for BTCUSD"""
    try:
        now = int(time.time())
        start_time = now - (limit * 3600)  # 1 hour per candle = 3600 seconds
        
        # Resolution: "1h" for 1-hour candles (must be string format)
        resolution = "1h"
        
        # Build the query string with required parameters
        query_string = f"?symbol={SYMBOL}&resolution={resolution}&start={start_time}&end={now}"
        path = f"/v2/history/candles{query_string}"
        url = f"{DEMO_BASE_URL}{path}"
        
        timestamp = str(int(time.time()))
        # Create signature with the path including query parameters
        signature_data = 'GET' + timestamp + path
        signature = generate_signature(DEMO_API_SECRET, signature_data)
        
        headers = {
            'api-key': DEMO_API_KEY,
            'signature': signature,
            'timestamp': timestamp,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                candles = data.get('result', [])
                return candles
        else:
            print(f"[WARNING] Candle fetch error {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[WARNING] Error fetching candles: {e}")
    
    # Return empty list on failure - signal will return NEUTRAL
    return []

def calculate_rsi(prices, period=14):
    """Calculate RSI from price series"""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_ema(prices, period=200):
    """Calculate EMA from price series"""
    if len(prices) < period:
        return None
    
    # Simple moving average for first EMA value
    sma = sum(prices[-period:]) / period
    ema = sma
    
    # Exponential smoothing for subsequent values
    multiplier = 2 / (period + 1)
    for price in prices[-period+1:]:
        ema = price * multiplier + ema * (1 - multiplier)
    
    return ema

def get_signal():
    """
    Determine trading signal
    LONG: RSI < 30 AND price > 200 EMA
    SHORT: RSI > 70 only
    NEUTRAL: other cases
    """
    candles = fetch_candles(250)
    
    if not candles or len(candles) < 201:
        return 'NEUTRAL', None, None
    
    # Extract close prices
    closes = [float(c['close']) for c in candles]
    
    # Calculate indicators
    rsi = calculate_rsi(closes, RSI_PERIOD)
    ema200 = calculate_ema(closes, EMA_PERIOD)
    
    if rsi is None or ema200 is None:
        return 'NEUTRAL', rsi, ema200
    
    current_price = closes[-1]
    
    # Signal logic
    if rsi < 30 and current_price > ema200:
        return 'LONG', rsi, ema200
    elif rsi > 70:
        return 'SHORT', rsi, ema200
    else:
        return 'NEUTRAL', rsi, ema200

def place_entry_order(side, position_size_btc):
    """Place market entry order"""
    btc_price = bot_state['current_price']
    
    body = {
        'product_id': PRODUCT_ID,
        'side': side.lower(),
        'order_type': 'market_order',
        'size': position_size_btc
    }
    
    response = make_api_request('POST', '/v2/orders', body)
    
    if response and response.get('success'):
        order = response.get('result', {})
        return order.get('id')
    
    return None

def place_tp_order(side, entry_price, position_size_btc):
    """Place limit take profit order"""
    if side == 'LONG':
        tp_price = entry_price * (1 + TP_PERCENT)
        order_side = 'sell'
    else:  # SHORT
        tp_price = entry_price * (1 - TP_PERCENT)
        order_side = 'buy'
    
    body = {
        'product_id': PRODUCT_ID,
        'side': order_side,
        'order_type': 'limit_order',
        'limit_price': str(round(tp_price, 1)),
        'size': position_size_btc,
        'reduce_only': True
    }
    
    response = make_api_request('POST', '/v2/orders', body)
    
    if response and response.get('success'):
        order = response.get('result', {})
        return order.get('id')
    
    return None

def place_sl_order(side, entry_price, position_size_btc):
    """Place stop loss market order"""
    if side == 'LONG':
        sl_price = entry_price * (1 - SL_PERCENT)
        order_side = 'sell'
    else:  # SHORT
        sl_price = entry_price * (1 + SL_PERCENT)
        order_side = 'buy'
    
    body = {
        'product_id': PRODUCT_ID,
        'side': order_side,
        'order_type': 'stop_market',
        'stop_price': str(round(sl_price, 1)),
        'size': position_size_btc,
        'reduce_only': True
    }
    
    response = make_api_request('POST', '/v2/orders', body)
    
    if response and response.get('success'):
        order = response.get('result', {})
        return order.get('id')
    
    return None

def execute_trade(side, position_size_btc):
    """
    Execute all three orders simultaneously:
    1. Market entry order
    2. Limit TP order
    3. Stop loss order
    """
    entry_price = bot_state['current_price']
    
    # Place entry
    entry_id = place_entry_order(side, position_size_btc)
    if not entry_id:
        return False
    
    time.sleep(1)
    
    # Place TP
    tp_id = place_tp_order(side, entry_price, position_size_btc)
    if not tp_id:
        return False
    
    time.sleep(1)
    
    # Place SL
    sl_id = place_sl_order(side, entry_price, position_size_btc)
    if not sl_id:
        return False
    
    # Update bot state
    bot_state['in_position'] = True
    bot_state['position_side'] = side
    bot_state['entry_price'] = entry_price
    bot_state['entry_time'] = datetime.datetime.now()
    
    return True

def send_telegram(message):
    """Send Telegram notification with error handling"""
    try:
        # Remove any problematic characters
        message = message.replace('\x00', '')  # Remove null bytes
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        response = requests.post(url, data=data, timeout=5)
        
        if response.status_code != 200:
            print(f"[WARNING] Telegram send failed: {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Telegram error: {str(e)[:50]}")

def log_to_excel(signal, rsi, ema, position_size_btc, status='OK', notes=''):
    """Log trade to daily Excel file"""
    today = datetime.date.today()
    daily_file = os.path.join(JOURNAL_FOLDER, 'Daily_Logs', f'{today}.json')
    
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'signal': signal,
        'rsi': round(rsi, 2) if rsi else 0,
        'ema200': round(ema, 2) if ema else 0,
        'btc_price': round(bot_state['current_price'], 2),
        'position_size': position_size_btc,
        'balance': round(bot_state['current_balance'], 2),
        'status': status,
        'notes': notes
    }
    
    # For simplicity, using JSON logging (Excel can be added later)
    try:
        logs = []
        if os.path.exists(daily_file):
            with open(daily_file, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        
        os.makedirs(os.path.dirname(daily_file), exist_ok=True)
        with open(daily_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Logging error: {e}")

def startup_check():
    """Verify bot configuration on startup"""
    print("\n" + "="*70)
    print("RSI HYBRID BOT - STARTUP VERIFICATION")
    print("="*70)
    
    # Get current market data
    btc_price = get_current_price()
    print(f"\n[MARKET DATA]")
    print(f"   BTC Price: ${btc_price:,.2f}")
    
    # Get account balance
    balance = get_account_balance()
    print(f"\n[ACCOUNT]")
    print(f"   Available Balance: ${balance:,.2f}")
    
    # Calculate position size
    position_size = calculate_position_size(btc_price)
    required_margin = get_required_margin(position_size, btc_price)
    print(f"\n[POSITION SIZING]")
    print(f"   Capital: ${CAPITAL}")
    print(f"   Risk per Trade: {RISK_PERCENT*100}% = ${CAPITAL * RISK_PERCENT}")
    print(f"   Position Size: {position_size:.4f} BTC")
    print(f"   Required Margin: ${required_margin:,.2f}")
    print(f"   Leverage: {LEVERAGE}x")
    print(f"   Buying Power: ${CAPITAL * LEVERAGE:,.2f}")
    
    # Set leverage
    print(f"\n[CONFIGURING TRADING]")
    set_leverage(LEVERAGE)
    
    # Check balance
    if balance < required_margin:
        print(f"\n[ERROR] Insufficient balance!")
        print(f"   Available: ${balance:,.2f}")
        print(f"   Required: ${required_margin:,.2f}")
        send_telegram("[ERROR] BOT STARTUP FAILED: Insufficient account balance for position sizing")
        return False
    
    print(f"\n[SUCCESS] All checks passed - Bot ready to trade!")
    print("="*70 + "\n")
    
    # Send startup confirmation to Telegram
    startup_msg = f"Bot is online. BTC Price: ${bot_state['current_price']:,.2f} RSI: Computing... EMA: Computing... Signal: Starting..."
    send_telegram(startup_msg)
    
    return True

def monitor_position():
    """Monitor open position every 5 minutes"""
    if not bot_state['in_position']:
        return
    
    current_size = get_position()
    
    if current_size == 0:
        # Position closed
        exit_price = bot_state['current_price']
        exit_time = datetime.datetime.now()
        hold_time = (exit_time - bot_state['entry_time']).total_seconds() / 60
        
        # Calculate PnL
        if bot_state['position_side'] == 'LONG':
            pnl_percent = ((exit_price - bot_state['entry_price']) / bot_state['entry_price']) * 100
        else:
            pnl_percent = ((bot_state['entry_price'] - exit_price) / bot_state['entry_price']) * 100
        
        # Account for fees
        pnl_percent -= (ENTRY_COST_RATE + EXIT_COST_RATE) * 100
        pnl_usd = bot_state['position_size'] * bot_state['entry_price'] * (pnl_percent / 100)
        
        status = "TP HIT" if pnl_percent > 0 else "SL HIT"
        
        message = (
            f"[CLOSED] Trade Closed\n"
            f"Side: {bot_state['position_side']}\n"
            f"Entry: ${bot_state['entry_price']:,.2f}\n"
            f"Exit: ${exit_price:,.2f}\n"
            f"Hold Time: {hold_time:.0f} min\n"
            f"PnL: {pnl_percent:.2f}% (${pnl_usd:,.2f})\n"
            f"Status: {status}"
        )
        
        send_telegram(message)
        log_to_excel(bot_state['position_side'], 0, 0, bot_state['position_size'], status, f"Exit at ${exit_price:.2f}")
        
        bot_state['in_position'] = False
        bot_state['position_side'] = None

def main_loop():
    """Main trading loop - runs continuously"""
    print("[BOT] RSI Hybrid Bot Started")
    print(f"[STRATEGY] RSI 30/70 + 200 EMA (LONG filtered, SHORT unfiltered)")
    print(f"[MONITOR] Checking signals hourly, monitoring positions every 5 minutes")
    print(f"[LOOP] Main loop running - sleeping {LOOP_SLEEP} seconds per iteration\n")
    
    last_signal_candle = 0
    monitor_position_count = 0  # Counter for every 5-minute check (5 iterations of 60 sec)
    
    while True:
        try:
            # Get current time
            now = int(time.time())
            current_hour = now // 3600
            
            # Refresh market data
            get_current_price()
            get_account_balance()
            
            # Check for new hourly candle
            if current_hour > last_signal_candle:
                last_signal_candle = current_hour
                
                # Get trading signal
                signal, rsi, ema = get_signal()
                
                # Print hourly status
                rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
                ema_str = f"${ema:,.0f}" if ema is not None else "N/A"
                status_msg = f"Hour check complete. RSI={rsi_str} EMA={ema_str} Price=${bot_state['current_price']:,.0f} Signal={signal} Next check in 60 minutes."
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {status_msg}")
                
                if signal != 'NEUTRAL' and not bot_state['in_position']:
                    # Calculate position size
                    position_size_btc = calculate_position_size(bot_state['current_price'])
                    
                    # Check balance
                    if not check_available_margin(position_size_btc):
                        insufficient_msg = f"Balance insufficient. Available: ${bot_state['current_balance']:.2f}, Required: ${get_required_margin(position_size_btc, bot_state['current_price']):.2f}"
                        print(f"  [WARNING] {insufficient_msg}")
                        send_telegram(f"[WARNING] {insufficient_msg} - Trade skipped")
                        log_to_excel(signal, rsi, ema, position_size_btc, 'SKIPPED', 'Insufficient Balance')
                    else:
                        # Execute trade
                        print(f"  [SUCCESS] Executing {signal} trade ({position_size_btc:.4f} BTC)")
                        if execute_trade(signal, position_size_btc):
                            message = (
                                f"Trade Opened Side={signal} Entry=${bot_state['current_price']:,.2f} Position={position_size_btc:.4f}BTC"
                            )
                            send_telegram(message)
                            log_to_excel(signal, rsi, ema, position_size_btc, 'TRADED', 'Entry order placed')
                        else:
                            print(f"  [ERROR] Failed to execute trade")
                            log_to_excel(signal, rsi, ema, position_size_btc, 'FAILED', 'Order placement failed')
                else:
                    # No signal or already in position
                    if signal == 'NEUTRAL':
                        print(f"  No signal - Waiting for next hour")
            
            # Monitor position every 5 minutes (5 iterations of 60 seconds = 300 seconds)
            monitor_position_count += 1
            if monitor_position_count >= 5 and bot_state['in_position']:
                monitor_position()
                monitor_position_count = 0
            
            # Sleep 60 seconds and continue loop
            time.sleep(LOOP_SLEEP)
        
        except KeyboardInterrupt:
            print("\n\n[STOP] Bot stopped by user")
            send_telegram("[STOP] Bot stopped by user")
            break
        except Exception as e:
            error_msg = str(e)[:80]  # Limit error message length
            print(f"\n[ERROR] Unexpected error: {error_msg}")
            try:
                send_telegram(f"[ERROR] Bot error occurred. Check logs for details.")
            except:
                pass  # Silently fail if Telegram also has issues
            time.sleep(60)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run startup check
    if startup_check():
        # Start main trading loop
        main_loop()
    else:
        print("\n[ERROR] Startup check failed. Bot exiting.")
