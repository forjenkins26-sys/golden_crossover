"""
CONFIG.PY - RSI Hybrid Bot Configuration
Reads all sensitive values from environment variables (for Railway deployment)
Local development: Create .env file with values
Railway: Set environment variables in Dashboard
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists locally)
load_dotenv()

# ============================================================================
# DELTA EXCHANGE API CREDENTIALS
# ============================================================================
DEMO_API_KEY = os.getenv('DEMO_API_KEY', 'aMpcVoWFDJNpGGb2QYJKp2ZrljalU4')
DEMO_API_SECRET = os.getenv('DEMO_API_SECRET', 'ypj0WNDEOaQ4WNyx4fLidxde0Ba0Uo4iKI5HYes7Q46XtkPSDs1Wami1zDIH')
DEMO_BASE_URL = "https://cdn-ind.testnet.deltaex.org"  # Demo API base URL - DO NOT CHANGE

# ============================================================================
# GOOGLE SHEETS CONFIGURATION
# ============================================================================
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')  # Your Google Sheet ID
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'google_credentials.json')  # Path to credentials JSON

# ============================================================================
# TELEGRAM NOTIFICATIONS
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8765740344:AAGXil8M89EMg5W1qCT5EQojspizltahkv4')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '757555299')

# ============================================================================
# TRADING PARAMETERS (DO NOT MODIFY - BACKTESTED VALUES)
# ============================================================================
SYMBOL = "BTCUSD"  # Trading pair (perpetual futures on Delta Exchange)
PRODUCT_ID = 84  # Delta Exchange product ID for BTCUSD
TP_PERCENT = 0.04  # Take profit 4% (must match backtest: 0.04)
SL_PERCENT = 0.012  # Stop loss 1.2% (must match backtest: 0.012)
ENTRY_COST_RATE = 0.001  # Entry fee 0.1% (must match backtest: 0.001)
EXIT_COST_RATE = 0.001  # Exit fee 0.1% (must match backtest: 0.001)

# ============================================================================
# POSITION SIZING (CAPITAL RISK BASED)
# ============================================================================
CAPITAL = float(os.getenv('CAPITAL', '200'))  # Total account capital in USD
RISK_PERCENT = float(os.getenv('RISK_PERCENT', '0.10'))  # Risk 10% of capital per trade
LEVERAGE = int(os.getenv('LEVERAGE', '10'))  # Use 10x leverage on Delta Exchange

# Position size formula (calculated dynamically in bot):
# position_size_btc = (CAPITAL × RISK_PERCENT) / (SL_PERCENT × current_btc_price)
# Example with BTC at $72,827: (200 × 0.10) / (0.012 × 72,827) ≈ 0.0023 BTC

# ============================================================================
# INDICATOR PARAMETERS (DO NOT MODIFY - BACKTESTED VALUES)
# ============================================================================
RSI_PERIOD = 14  # RSI calculation period (must match backtest: 14)
EMA_PERIOD = 200  # EMA calculation period (must match backtest: 200)
TIMEFRAME = "1h"  # Candle timeframe (must match backtest: 1h)

# ============================================================================
# LOGGING AND JOURNAL PATHS (Local use - not needed on Railway)
# ============================================================================
JOURNAL_FOLDER = os.path.expanduser("~/Desktop/RSI_Hybrid_Journal")  # Daily logs folder (local only)
MASTER_JOURNAL = os.path.join(JOURNAL_FOLDER, "Master_Journal.xlsx")  # Master journal file (local only)

# Create journal directories if they don't exist (local only)
try:
    os.makedirs(os.path.join(JOURNAL_FOLDER, "Daily_Logs"), exist_ok=True)
except:
    pass  # Ignore errors on Railway where /root/Desktop doesn't exist


