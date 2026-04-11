"""
CONFIG.PY
Configuration file for RSI Hybrid Bot
Uses environment variables for sensitive credentials
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (local) or Railway environment
load_dotenv()

# ============================================================================
# DELTA EXCHANGE DEMO API CREDENTIALS
# ============================================================================
DEMO_API_KEY = os.getenv('DEMO_API_KEY', 'aMpcVoWFDJNpGGb2QYJKp2ZrljalU4')
DEMO_API_SECRET = os.getenv('DEMO_API_SECRET', 'ypj0WNDEOaQ4WNyx4fLidxde0Ba0Uo4iKI5HYes7Q46XtkPSDs1Wami1zDIH')
DEMO_BASE_URL = "https://cdn-ind.testnet.deltaex.org"  # Demo API base URL - DO NOT CHANGE

# ============================================================================
# TELEGRAM NOTIFICATIONS
# ============================================================================
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8765740344:AAGXil8M89EMg5W1qCT5EQojspizltahkv4')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '757555299')

# ============================================================================
# TRADING PARAMETERS (DO NOT MODIFY - BACKTESTED VALUES)
# ============================================================================
SYMBOL = "BTCUSD"  # Trading pair (perpetual futures on Delta Exchange)
PRODUCT_ID = 84  # Delta Exchange product ID for BTCUSD (do NOT change)
TP_PERCENT = 0.04  # Take profit 4% (must match backtest: 0.04)
SL_PERCENT = 0.012  # Stop loss 1.2% (must match backtest: 0.012)
ENTRY_COST_RATE = 0.001  # Entry fee 0.1% (must match backtest: 0.001)
EXIT_COST_RATE = 0.001  # Exit fee 0.1% (must match backtest: 0.001)

# ============================================================================
# POSITION SIZING (CAPITAL RISK BASED)
# ============================================================================
CAPITAL = 200  # Total account capital in USD
RISK_PERCENT = 0.10  # Risk 10% of capital per trade ($20 per trade)
LEVERAGE = 10  # Use 10x leverage on Delta Exchange (buying power: $200 × 10 = $2000)

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
# JOURNAL PATHS
# ============================================================================
JOURNAL_FOLDER = os.path.expanduser("~/Desktop/RSI_Hybrid_Journal")  # Daily logs folder
MASTER_JOURNAL = os.path.join(JOURNAL_FOLDER, "Master_Journal.xlsx")  # Master journal file

# Create journal directories if they don't exist
os.makedirs(os.path.join(JOURNAL_FOLDER, "Daily_Logs"), exist_ok=True)
