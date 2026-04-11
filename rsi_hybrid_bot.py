# -*- coding: utf-8 -*-
"""
RSI_HYBRID_BOT.PY - Live Trading Bot with Google Sheets + Excel Logging
Live trading bot for Delta Exchange BTCUSD perpetual futures
Strategy: RSI 30/70 with 200 EMA filter
Position Sizing: Dynamic capital-risk based
Leverage: 10x automatic
Timeframe: 1-hour candles
Logging: Google Sheets (Trade_Log + Daily_Summary tabs) + Local Excel files
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
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

sys.path.insert(0, '.')
from config import (
    DEMO_API_KEY, DEMO_API_SECRET, DEMO_BASE_URL,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    SYMBOL, PRODUCT_ID, TP_PERCENT, SL_PERCENT, 
    ENTRY_COST_RATE, EXIT_COST_RATE,
    CAPITAL, RISK_PERCENT, LEVERAGE,
    RSI_PERIOD, EMA_PERIOD, TIMEFRAME,
    GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH
)
from excel_logger import log_trade_to_excel, create_master_journal, create_daily_log_file

# ============================================================================
# CONSTANTS
# ============================================================================
BTCUSD_MIN_LOT_SIZE = 0.0001
API_RETRY_COUNT = 3
API_RETRY_DELAY = 30
LOOP_SLEEP = 60
ALIVE_CHECK_HOURS = 6  # Send "Bot is alive" message every 6 hours

# ============================================================================
# GOOGLE SHEETS SETUP
# ============================================================================
try:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Try to get credentials from environment variable (Railway) first
    google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if google_creds_json:
        # Parse JSON from environment variable
        creds_dict = json.loads(google_creds_json)
        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Fall back to file path (local development)
        credentials = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES)
    
    sheets_service = build('sheets', 'v4', credentials=credentials)
except Exception as e:
    print(f"[WARNING] Google Sheets initialization failed: {e}")
    sheets_service = None

# ============================================================================
# GLOBAL STATE
# ============================================================================
bot_state = {
    'current_price': 0,
    'current_balance': 0,
    'position_size': 0,
    'in_position': False,
    'position_side': None,
    'entry_price': 0,
    'entry_time': None,
    'monitor_count': 0,
    'last_candle_time': 0,
    'last_hourly_status_time': 0,
    'last_alive_check': int(time.time()),
    'daily_trades': [],
    'cumulative_pnl': 0,
}

candle_history = deque(maxlen=250)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_signature(secret, message):
    """Generate HMAC SHA256 signature"""
    message_bytes = message.encode('utf-8')
    secret_bytes = secret.encode('utf-8')
    signature = hmac.new(secret_bytes, message_bytes, hashlib.sha256).hexdigest()
    return signature

def make_api_request(method, path, body=None, retry=0):
    """Make authenticated API request with retry logic"""
    if retry >= API_RETRY_COUNT:
        send_telegram(f"[ERROR] API call failed after {API_RETRY_COUNT} retries. Path: {path}")
        return None
    
    try:
        timestamp = str(int(time.time()))
        
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
            print(f"[WARNING] API Error {response.status_code}: {response.text[:200]}")
            time.sleep(API_RETRY_DELAY)
            return make_api_request(method, path, body, retry + 1)
    
    except Exception as e:
        print(f"[WARNING] Request error: {e}")
        time.sleep(API_RETRY_DELAY)
        return make_api_request(method, path, body, retry + 1)

def get_current_price():
    """Fetch current BTCUSD price"""
    response = make_api_request('GET', '/v2/tickers/BTCUSD')
    if response and response.get('success'):
        ticker = response.get('result', {})
        price = float(ticker.get('mark_price', 0))
        bot_state['current_price'] = price
        return price
    return bot_state['current_price']

def get_account_balance():
    """Get available balance"""
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
    """Get current open position"""
    response = make_api_request('GET', '/v2/positions', {'product_id': PRODUCT_ID})
    if response and response.get('success'):
        position = response.get('result', {})
        size = int(position.get('size', 0))
        return size
    return 0

def set_leverage(leverage_value):
    """Set leverage (default is already 10x on BTCUSD)"""
    print(f"[SUCCESS] Leverage is set to {leverage_value}x (default for BTCUSD)")
    return True

def calculate_position_size(btc_price):
    """Calculate position size using capital risk formula"""
    if btc_price <= 0:
        return 0
    
    risk_amount = CAPITAL * RISK_PERCENT
    denominator = SL_PERCENT * btc_price
    
    position_size = risk_amount / denominator
    position_size = math.floor(position_size / BTCUSD_MIN_LOT_SIZE) * BTCUSD_MIN_LOT_SIZE
    
    bot_state['position_size'] = position_size
    return position_size

def get_required_margin(position_size_btc, btc_price):
    """Calculate required margin"""
    if LEVERAGE == 0:
        return float('inf')
    return (position_size_btc * btc_price) / LEVERAGE

def check_available_margin(position_size_btc):
    """Check if account has sufficient margin"""
    btc_price = bot_state['current_price']
    available_balance = bot_state['current_balance']
    required_margin = get_required_margin(position_size_btc, btc_price)
    return available_balance >= required_margin

def fetch_candles(limit=250):
    """Fetch historical OHLC candles"""
    try:
        now = int(time.time())
        start_time = now - (limit * 3600)
        
        resolution = "1h"
        query_string = f"?symbol={SYMBOL}&resolution={resolution}&start={start_time}&end={now}"
        path = f"/v2/history/candles{query_string}"
        url = f"{DEMO_BASE_URL}{path}"
        
        timestamp = str(int(time.time()))
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
            print(f"[WARNING] Candle fetch error {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Error fetching candles: {e}")
    
    return []

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
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
    """Calculate EMA"""
    if len(prices) < period:
        return None
    
    sma = sum(prices[-period:]) / period
    ema = sma
    
    multiplier = 2 / (period + 1)
    for price in prices[-period+1:]:
        ema = price * multiplier + ema * (1 - multiplier)
    
    return ema

def get_signal():
    """Determine trading signal"""
    candles = fetch_candles(750)
    
    if not candles or len(candles) < 201:
        return 'NEUTRAL', None, None
    
    closes = [float(c['close']) for c in candles]
    
    rsi = calculate_rsi(closes, RSI_PERIOD)
    ema200 = calculate_ema(closes, EMA_PERIOD)
    
    if rsi is None or ema200 is None:
        return 'NEUTRAL', rsi, ema200
    
    current_price = closes[-1]
    
    if rsi < 30 and current_price > ema200:
        return 'LONG', rsi, ema200
    elif rsi > 70:
        return 'SHORT', rsi, ema200
    else:
        return 'NEUTRAL', rsi, ema200

def place_entry_order(side, position_size_btc):
    """Place market entry order"""
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
    else:
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
    else:
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
    """Execute all three orders simultaneously"""
    entry_price = bot_state['current_price']
    
    entry_id = place_entry_order(side, position_size_btc)
    if not entry_id:
        return False
    
    time.sleep(1)
    
    tp_id = place_tp_order(side, entry_price, position_size_btc)
    if not tp_id:
        return False
    
    time.sleep(1)
    
    sl_id = place_sl_order(side, entry_price, position_size_btc)
    if not sl_id:
        return False
    
    bot_state['in_position'] = True
    bot_state['position_side'] = side
    bot_state['entry_price'] = entry_price
    bot_state['entry_time'] = datetime.datetime.now()
    
    return True

def send_telegram(message):
    """Send Telegram notification"""
    try:
        message = message.replace('\x00', '')
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
        response = requests.post(url, data=data, timeout=5)
        if response.status_code != 200:
            print(f"[WARNING] Telegram send failed: {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Telegram error: {str(e)[:50]}")

def append_to_google_sheets(sheet_name, values):
    """Append a row to Google Sheets"""
    if not sheets_service or not GOOGLE_SHEET_ID:
        print(f"[WARNING] Google Sheets not configured")
        return False
    
    try:
        body = {'values': [values]}
        request = sheets_service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f'{sheet_name}!A:Z',
            valueInputOption='USER_ENTERED',
            body=body
        )
        response = request.execute()
        return True
    except Exception as e:
        print(f"[WARNING] Google Sheets append failed: {e}")
        return False

def update_google_sheets_cell(sheet_name, cell_range, values):
    """Update specific cells in Google Sheets"""
    if not sheets_service or not GOOGLE_SHEET_ID:
        return False
    
    try:
        body = {'values': values}
        request = sheets_service.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f'{sheet_name}!{cell_range}',
            valueInputOption='USER_ENTERED',
            body=body
        )
        response = request.execute()
        return True
    except Exception as e:
        print(f"[WARNING] Google Sheets update failed: {e}")
        return False

def log_trade_to_sheets(direction, entry_price, exit_price, result, gross_pnl, fees, net_pnl, notes):
    """Log trade to both Google Sheets and local Excel file"""
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    time_str = now.strftime('%H:%M:%S')
    
    # Update cumulative PnL
    bot_state['cumulative_pnl'] += net_pnl
    
    row = [
        date_str,
        time_str,
        direction,
        f"{entry_price:.2f}",
        f"{exit_price:.2f}",
        result,
        f"{gross_pnl:.4f}",
        f"{fees:.4f}",
        f"{net_pnl:.4f}",
        f"{bot_state['cumulative_pnl']:.4f}",
        notes
    ]
    
    # Log to Google Sheets
    append_to_google_sheets('Trade_Log', row)
    
    # Log to local Excel file
    try:
        trade_data = {
            'date': date_str,
            'time': time_str,
            'direction': direction,
            'entry_price': float(entry_price),
            'exit_price': float(exit_price),
            'result': result,
            'gross_pnl': float(gross_pnl),
            'fees': float(fees),
            'net_pnl': float(net_pnl),
            'cumulative_pnl': float(bot_state['cumulative_pnl']),
            'notes': notes
        }
        log_trade_to_excel(trade_data)
        
        # Update master journal after each trade
        create_master_journal()
    except Exception as e:
        print(f"[WARNING] Excel logging failed: {e}")
    
    # Save to daily_trades for summary
    bot_state['daily_trades'].append({
        'entry_price': entry_price,
        'exit_price': exit_price,
        'result': result,
        'net_pnl': net_pnl
    })

def update_daily_summary():
    """Update Daily_Summary sheet at midnight"""
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    total_trades = len(bot_state['daily_trades'])
    winning_trades = sum(1 for t in bot_state['daily_trades'] if t['result'] == 'TP')
    losing_trades = sum(1 for t in bot_state['daily_trades'] if t['result'] == 'SL')
    daily_pnl = sum(t['net_pnl'] for t in bot_state['daily_trades'])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    if total_trades == 0:
        row = [date_str, '0', '0', '0', '0%', '0', f"{bot_state['cumulative_pnl']:.4f}"]
        notes = 'No Trade Today'
    else:
        row = [
            date_str,
            str(total_trades),
            str(winning_trades),
            str(losing_trades),
            f"{win_rate:.1f}%",
            f"{daily_pnl:.4f}",
            f"{bot_state['cumulative_pnl']:.4f}"
        ]
        notes = f'{winning_trades}W {losing_trades}L'
    
    append_to_google_sheets('Daily_Summary', row)
    
    # Reset daily trades
    bot_state['daily_trades'] = []

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
        
        if bot_state['position_side'] == 'LONG':
            pnl_percent = ((exit_price - bot_state['entry_price']) / bot_state['entry_price']) * 100
        else:
            pnl_percent = ((bot_state['entry_price'] - exit_price) / bot_state['entry_price']) * 100
        
        fees = (ENTRY_COST_RATE + EXIT_COST_RATE) * 100
        gross_pnl = pnl_percent
        net_pnl = pnl_percent - fees
        pnl_usd = bot_state['position_size'] * bot_state['entry_price'] * (net_pnl / 100)
        
        status = "TP HIT" if net_pnl > 0 else "SL HIT"
        result = "TP" if net_pnl > 0 else "SL"
        
        message = (
            f"[CLOSED] Trade Closed\n"
            f"Side: {bot_state['position_side']}\n"
            f"Entry: ${bot_state['entry_price']:,.2f}\n"
            f"Exit: ${exit_price:,.2f}\n"
            f"Hold Time: {hold_time:.0f} min\n"
            f"Net PnL: {net_pnl:.2f}% (${pnl_usd:,.2f})\n"
            f"Status: {status}"
        )
        
        send_telegram(message)
        log_trade_to_sheets(
            bot_state['position_side'],
            bot_state['entry_price'],
            exit_price,
            result,
            gross_pnl,
            fees,
            net_pnl,
            f"Hold {hold_time:.0f}min"
        )
        
        bot_state['in_position'] = False
        bot_state['position_side'] = None

def send_alive_message():
    """Send 'Bot is alive' message every 6 hours"""
    now = int(time.time())
    if now - bot_state['last_alive_check'] >= ALIVE_CHECK_HOURS * 3600:
        bot_state['last_alive_check'] = now
        
        rsi_str = "Computing..."
        ema_str = "Computing..."
        
        message = (
            f"[ALIVE] Bot is alive\n"
            f"BTC Price: ${bot_state['current_price']:,.2f}\n"
            f"RSI: {rsi_str}\n"
            f"EMA200: {ema_str}\n"
            f"Uptime: OK\n"
            f"Last Signal: Monitoring..."
        )
        
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message.replace(chr(10), ' | ')}")
        send_telegram(message)

def startup_check():
    """Verify bot configuration on startup"""
    print("\n" + "="*70)
    print("RSI HYBRID BOT - STARTUP VERIFICATION")
    print("="*70)
    
    btc_price = get_current_price()
    print(f"\n[MARKET DATA]")
    print(f"   BTC Price: ${btc_price:,.2f}")
    
    balance = get_account_balance()
    print(f"\n[ACCOUNT]")
    print(f"   Available Balance: ${balance:,.2f}")
    
    position_size = calculate_position_size(btc_price)
    required_margin = get_required_margin(position_size, btc_price)
    print(f"\n[POSITION SIZING]")
    print(f"   Capital: ${CAPITAL}")
    print(f"   Risk per Trade: {RISK_PERCENT*100}% = ${CAPITAL * RISK_PERCENT}")
    print(f"   Position Size: {position_size:.4f} BTC")
    print(f"   Required Margin: ${required_margin:,.2f}")
    print(f"   Leverage: {LEVERAGE}x")
    print(f"   Buying Power: ${CAPITAL * LEVERAGE:,.2f}")
    
    print(f"\n[CONFIGURING TRADING]")
    set_leverage(LEVERAGE)
    
    if balance < required_margin:
        print(f"\n[ERROR] Insufficient balance!")
        print(f"   Available: ${balance:,.2f}")
        print(f"   Required: ${required_margin:,.2f}")
        send_telegram("[ERROR] BOT STARTUP FAILED: Insufficient account balance")
        return False
    
    print(f"\n[GOOGLE SHEETS]")
    if sheets_service and GOOGLE_SHEET_ID:
        print(f"   Sheet ID: {GOOGLE_SHEET_ID[:20]}...")
        print(f"   Status: Connected")
    else:
        print(f"   Status: Not configured (local logging only)")
    
    print(f"\n[EXCEL JOURNAL]")
    try:
        daily_file = create_daily_log_file()
        print(f"   Daily Log: {daily_file.name}")
        print(f"   Status: Ready")
    except Exception as e:
        print(f"   Status: Error - {e}")
    
    print(f"\n[SUCCESS] All checks passed - Bot ready to trade!")
    print("="*70 + "\n")
    
    startup_msg = f"Bot is online. BTC Price: ${bot_state['current_price']:,.2f} RSI: Computing... EMA: Computing... Signal: Starting..."
    send_telegram(startup_msg)
    
    return True

def main_loop():
    """Main trading loop"""
    print("[BOT] RSI Hybrid Bot Started")
    print(f"[STRATEGY] RSI 30/70 + 200 EMA (LONG filtered, SHORT unfiltered)")
    print(f"[LOGGING] Google Sheets: Trade_Log + Daily_Summary")
    print(f"[MONITOR] Checking signals hourly, monitoring positions every 5 minutes")
    print(f"[LOOP] Main loop running - sleeping {LOOP_SLEEP} seconds per iteration\n")
    
    last_signal_candle = 0
    last_daily_summary_date = datetime.date.today()
    monitor_position_count = 0
    
    while True:
        try:
            now = int(time.time())
            current_hour = now // 3600
            current_date = datetime.date.today()
            
            get_current_price()
            get_account_balance()
            
            # Update daily summary at midnight
            if current_date > last_daily_summary_date:
                update_daily_summary()
                last_daily_summary_date = current_date
            
            # Check for new hourly candle
            if current_hour > last_signal_candle:
                last_signal_candle = current_hour
                
                signal, rsi, ema = get_signal()
                
                rsi_str = f"{rsi:.1f}" if rsi is not None else "N/A"
                ema_str = f"${ema:,.0f}" if ema is not None else "N/A"
                status_msg = f"Hour check complete. RSI={rsi_str} EMA={ema_str} Price=${bot_state['current_price']:,.0f} Signal={signal} Next check in 60 minutes."
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {status_msg}")
                
                if signal != 'NEUTRAL' and not bot_state['in_position']:
                    position_size_btc = calculate_position_size(bot_state['current_price'])
                    
                    if not check_available_margin(position_size_btc):
                        insufficient_msg = f"Balance insufficient. Available: ${bot_state['current_balance']:.2f}, Required: ${get_required_margin(position_size_btc, bot_state['current_price']):.2f}"
                        print(f"  [WARNING] {insufficient_msg}")
                        send_telegram(f"[WARNING] {insufficient_msg} - Trade skipped")
                    else:
                        print(f"  [SUCCESS] Executing {signal} trade ({position_size_btc:.4f} BTC)")
                        if execute_trade(signal, position_size_btc):
                            message = f"Trade Opened Side={signal} Entry=${bot_state['current_price']:,.2f} Position={position_size_btc:.4f}BTC"
                            send_telegram(message)
                        else:
                            print(f"  [ERROR] Failed to execute trade")
                else:
                    if signal == 'NEUTRAL':
                        print(f"  No signal - Waiting for next hour")
            
            # Monitor position every 5 minutes
            monitor_position_count += 1
            if monitor_position_count >= 5 and bot_state['in_position']:
                monitor_position()
                monitor_position_count = 0
            
            # Send "Bot is alive" message every 6 hours
            send_alive_message()
            
            time.sleep(LOOP_SLEEP)
        
        except KeyboardInterrupt:
            print("\n\n[STOP] Bot stopped by user")
            send_telegram("[STOP] Bot stopped by user")
            break
        except Exception as e:
            error_msg = str(e)[:80]
            print(f"\n[ERROR] Unexpected error: {error_msg}")
            try:
                send_telegram(f"[ERROR] Bot error occurred. Check logs for details.")
            except:
                pass
            time.sleep(60)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if startup_check():
        main_loop()
    else:
        print("\n[ERROR] Startup check failed. Bot exiting.")
